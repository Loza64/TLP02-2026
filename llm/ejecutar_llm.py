"""
Ejecucion del experimento LLM (Fase 2, enfoque D) con Google Gemini.

Uso (desde la raiz del repositorio):

    python -m llm.ejecutar_llm zero-shot
    python -m llm.ejecutar_llm few-shot
    python -m llm.ejecutar_llm ambos

Por cada ejecucion se crea logs/llm_<modo>_<AAAAMMDD_HHMMSS>/ con la
evidencia original de cada llamada:

- prompt_lote_XX.txt                    prompt exacto enviado
- respuesta_bruta_lote_XX_intento_N.txt respuesta completa recibida
- llamadas.json                         timestamp de inicio/fin, estado,
                                        error y uso de tokens de CADA llamada
                                        (incluidos los reintentos)
- metadatos.json                        modelo, parametros, entorno, hash
- resultados.json                       decisiones validadas de las 40 oraciones

Ademas se escribe el log consolidado logs/llm_<modo>.json, que es el que
lee evaluacion/evaluar.py.

Las respuestas nunca se reconstruyen: si un lote no se obtiene tras los
reintentos, queda registrado como pendiente y la ejecucion termina con
codigo de salida 1.
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from importlib import metadata
from pathlib import Path

from llm.prompts import (
    EJEMPLOS_FEW_SHOT,
    RUTA_PLANTILLAS,
    construir_prompt,
    verificar_plantillas,
)

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "corpus" / "corpus_pruebas.csv"
LOGS_PATH = ROOT / "logs"

MODELO_POR_DEFECTO = "gemini-3.5-flash-lite"
TEMPERATURA = 0
FORMATO_RESPUESTA = "application/json"
TAMANO_LOTE = 5
MAX_INTENTOS = 5
ESPERA_BASE_SEGUNDOS = 10  # espera exponencial: 10, 20, 40, 80 s


# --------------------------------------------------
# Utilidades
# --------------------------------------------------

def ahora():
    return datetime.now().astimezone()


def guardar_json(ruta, contenido):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def relativa(ruta):
    return Path(ruta).resolve().relative_to(ROOT).as_posix()


def obtener_commit():
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        )
        return salida.stdout.strip()
    except Exception:
        return None


def version_paquete(nombre):
    try:
        return metadata.version(nombre)
    except metadata.PackageNotFoundError:
        return None


def cargar_corpus():
    with open(CORPUS_PATH, "r", encoding="utf-8-sig", newline="") as archivo:
        return [
            {"id": int(fila["id"]), "oracion": fila["oracion"]}
            for fila in csv.DictReader(archivo)
        ]


def dividir_en_lotes(corpus, tamano):
    return [corpus[i:i + tamano] for i in range(0, len(corpus), tamano)]


# --------------------------------------------------
# Validacion de la respuesta
# --------------------------------------------------

def validar_respuesta(texto, lote):
    """
    Comprueba que la respuesta sea JSON, que contenga exactamente los IDs
    del lote, que las decisiones sean validas y que las oraciones no hayan
    sido modificadas. Lanza ValueError si algo no cumple.
    """
    datos = json.loads(texto)
    resultados = datos["resultados"]

    esperados = {e["id"]: e["oracion"] for e in lote}
    recibidos = [r.get("id") for r in resultados]

    if sorted(recibidos) != sorted(esperados):
        raise ValueError(
            f"IDs recibidos {recibidos} no coinciden con {sorted(esperados)}"
        )

    for r in resultados:
        if r.get("decision") not in ("ACEPTADA", "RECHAZADA"):
            raise ValueError(f"Decision invalida para ID {r.get('id')}: "
                             f"{r.get('decision')!r}")
        if r.get("oracion") != esperados[r["id"]]:
            raise ValueError(f"La oracion del ID {r['id']} fue modificada")

    return sorted(resultados, key=lambda r: r["id"])


def uso_tokens(response):
    uso = getattr(response, "usage_metadata", None)
    if uso is None:
        return None
    return {
        "prompt": getattr(uso, "prompt_token_count", None),
        "respuesta": getattr(uso, "candidates_token_count", None),
        "razonamiento": getattr(uso, "thoughts_token_count", None),
        "total": getattr(uso, "total_token_count", None),
    }


# --------------------------------------------------
# Ejecucion de un modo
# --------------------------------------------------

def ejecutar_modo(client, types, modo, modelo):
    corpus = cargar_corpus()
    if not corpus:
        raise ValueError("El corpus esta vacio.")

    incluir_ejemplos = modo == "few-shot"
    lotes = dividir_en_lotes(corpus, TAMANO_LOTE)

    inicio_total = ahora()
    carpeta = LOGS_PATH / (
        f"llm_{modo.replace('-', '_')}_{inicio_total:%Y%m%d_%H%M%S}"
    )
    carpeta.mkdir(parents=True, exist_ok=False)

    configuracion = {
        "temperature": TEMPERATURA,
        "response_mime_type": FORMATO_RESPUESTA,
    }

    llamadas = []
    resultados = []
    lotes_pendientes = []

    print(f"\n=== LLM {modo} | modelo {modelo} | "
          f"{len(corpus)} oraciones en {len(lotes)} lotes ===")

    for numero, lote in enumerate(lotes, start=1):
        prompt = construir_prompt(lote, incluir_ejemplos=incluir_ejemplos)
        ruta_prompt = carpeta / f"prompt_lote_{numero:02}.txt"
        ruta_prompt.write_text(prompt, encoding="utf-8")

        obtenido = False
        for intento in range(1, MAX_INTENTOS + 1):
            registro = {
                "lote": numero,
                "ids": [e["id"] for e in lote],
                "intento": intento,
                "inicio": None,
                "fin": None,
                "duracion_segundos": None,
                "estado": None,
                "error": None,
                "modelo_respondio": None,
                "tokens": None,
                "prompt": relativa(ruta_prompt),
                "respuesta_bruta": None,
            }

            inicio = ahora()
            registro["inicio"] = inicio.isoformat()
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=TEMPERATURA,
                        response_mime_type=FORMATO_RESPUESTA,
                    ),
                )
                fin = ahora()
                texto = response.text or ""

                ruta_resp = (carpeta /
                             f"respuesta_bruta_lote_{numero:02}"
                             f"_intento_{intento}.txt")
                ruta_resp.write_text(texto, encoding="utf-8")
                registro["respuesta_bruta"] = relativa(ruta_resp)
                registro["modelo_respondio"] = getattr(
                    response, "model_version", None)
                registro["tokens"] = uso_tokens(response)

                validados = validar_respuesta(texto, lote)
                registro["estado"] = "ok"
            except Exception as error:  # noqa: BLE001 - se registra todo
                fin = ahora()
                registro["estado"] = "error"
                registro["error"] = f"{type(error).__name__}: {error}"
                validados = None

            registro["fin"] = fin.isoformat()
            registro["duracion_segundos"] = round(
                (fin - inicio).total_seconds(), 3)
            llamadas.append(registro)
            guardar_json(carpeta / "llamadas.json", llamadas)

            if validados is not None:
                resultados.extend(validados)
                obtenido = True
                print(f"  Lote {numero}: ok (intento {intento}, "
                      f"{registro['duracion_segundos']} s)")
                break

            print(f"  Lote {numero}: intento {intento} fallo -> "
                  f"{registro['error'][:120]}")
            if intento < MAX_INTENTOS:
                time.sleep(ESPERA_BASE_SEGUNDOS * 2 ** (intento - 1))

        if not obtenido:
            lotes_pendientes.append(numero)

    fin_total = ahora()
    resultados.sort(key=lambda r: r["id"])

    ruta_plantilla = RUTA_PLANTILLAS[modo]
    metadatos = {
        "enfoque": "LLM mediante API",
        "modo": modo,
        "proveedor": "Google Gemini",
        "modelo": modelo,
        "parametros": {
            **configuracion,
            "tamano_lote": TAMANO_LOTE,
            "max_intentos_por_lote": MAX_INTENTOS,
            "espera_base_segundos": ESPERA_BASE_SEGUNDOS,
        },
        "ejemplos_few_shot": len(EJEMPLOS_FEW_SHOT) if incluir_ejemplos else 0,
        "prompt_plantilla": relativa(ruta_plantilla),
        "prompt_plantilla_sha256": sha256(ruta_plantilla),
        "corpus": relativa(CORPUS_PATH),
        "corpus_sha256": sha256(CORPUS_PATH),
        "total_oraciones": len(corpus),
        "total_lotes": len(lotes),
        "total_llamadas": len(llamadas),
        "llamadas_fallidas": sum(ll["estado"] == "error" for ll in llamadas),
        "resultados_obtenidos": len(resultados),
        "lotes_pendientes": lotes_pendientes,
        "inicio": inicio_total.isoformat(),
        "fin": fin_total.isoformat(),
        "duracion_segundos": round((fin_total - inicio_total).total_seconds(), 2),
        "entorno": {
            "python": platform.python_version(),
            "sistema_operativo": platform.platform(),
            "google_genai": version_paquete("google-genai"),
            "commit_git": obtener_commit(),
        },
        "carpeta_evidencia": relativa(carpeta),
    }

    guardar_json(carpeta / "resultados.json", {"resultados": resultados})
    guardar_json(carpeta / "metadatos.json", metadatos)

    # Log consolidado que consume evaluacion/evaluar.py
    consolidado = LOGS_PATH / f"llm_{modo.replace('-', '_')}.json"
    guardar_json(consolidado, {
        "metadatos": metadatos,
        "llamadas": llamadas,
        "resultados": resultados,
    })

    print(f"  Resultados: {len(resultados)}/{len(corpus)} | "
          f"llamadas: {len(llamadas)} | pendientes: {lotes_pendientes or 'ninguno'}")
    print(f"  Evidencia: {relativa(carpeta)}/  |  Log: {relativa(consolidado)}")

    return not lotes_pendientes


# --------------------------------------------------
# Punto de entrada
# --------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Ejecuta el corpus con Gemini en modo zero-shot y/o few-shot."
    )
    parser.add_argument("modo", choices=["zero-shot", "few-shot", "ambos"])
    parser.add_argument("--modelo", default=None,
                        help="Modelo de Gemini (por defecto GEMINI_MODEL "
                             f"del .env o {MODELO_POR_DEFECTO}).")
    args = parser.parse_args(argv)

    # Garantiza que el .txt versionado es exactamente el prompt enviado.
    desactualizadas = verificar_plantillas()
    if desactualizadas:
        sys.exit(
            "Las plantillas llm/prompt_*.txt no coinciden con llm/prompts.py "
            f"({', '.join(desactualizadas)}). Ejecuta: python -m llm.prompts"
        )

    from dotenv import load_dotenv
    from google import genai
    from google.genai import types

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Falta GEMINI_API_KEY. Copia .env.example a .env y "
                 "coloca tu clave.")

    modelo = args.modelo or os.getenv("GEMINI_MODEL") or MODELO_POR_DEFECTO
    client = genai.Client(api_key=api_key)

    modos = ["zero-shot", "few-shot"] if args.modo == "ambos" else [args.modo]
    completos = [ejecutar_modo(client, types, m, modelo) for m in modos]

    if not all(completos):
        sys.exit(1)


if __name__ == "__main__":
    main()
