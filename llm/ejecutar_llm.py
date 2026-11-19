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
# Recuperacion de lotes incompletos
# --------------------------------------------------

def preparar_recuperacion(carpeta):
    """
    Analiza una ejecucion anterior y determina que lotes necesitan
    recuperarse. No realiza llamadas a Gemini.
    """
    carpeta = Path(carpeta).resolve()
    logs_resueltos = LOGS_PATH.resolve()

    if not carpeta.is_relative_to(logs_resueltos) or carpeta == logs_resueltos:
        raise ValueError("La carpeta de evidencia debe estar dentro de logs/.")

    ruta_meta = carpeta / "metadatos.json"
    ruta_resultados = carpeta / "resultados.json"
    ruta_llamadas = carpeta / "llamadas.json"

    for ruta in (ruta_meta, ruta_resultados, ruta_llamadas):
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el archivo requerido: {ruta}")

    with open(ruta_meta, "r", encoding="utf-8") as archivo:
        metadatos = json.load(archivo)

    modo = metadatos.get("modo")
    if modo not in ("zero-shot", "few-shot"):
        raise ValueError(f"Modo de ejecucion no valido: {modo!r}")

    # No mezclar resultados de otro corpus.
    if metadatos.get("corpus_sha256") != sha256(CORPUS_PATH):
        raise ValueError(
            "El corpus actual no coincide con el utilizado en la ejecucion "
            "original. No se puede recuperar con seguridad."
        )

    ruta_plantilla = RUTA_PLANTILLAS[modo]
    if metadatos.get("prompt_plantilla_sha256") != sha256(ruta_plantilla):
        raise ValueError(
            "La plantilla actual no coincide con la de la ejecucion original."
        )

    corpus = cargar_corpus()
    if not corpus:
        raise ValueError("El corpus esta vacio.")

    tamano_lote = metadatos.get("parametros", {}).get(
        "tamano_lote", TAMANO_LOTE
    )
    if not isinstance(tamano_lote, int) or tamano_lote <= 0:
        raise ValueError("El tamano de lote guardado no es valido.")

    lotes = dividir_en_lotes(corpus, tamano_lote)

    if metadatos.get("total_oraciones") != len(corpus):
        raise ValueError("La cantidad de oraciones del corpus ha cambiado.")

    if metadatos.get("total_lotes") != len(lotes):
        raise ValueError("La cantidad de lotes no coincide con la ejecucion original.")

    with open(ruta_resultados, "r", encoding="utf-8") as archivo:
        datos_resultados = json.load(archivo)

    resultados = datos_resultados.get("resultados")
    if not isinstance(resultados, list):
        raise ValueError("El archivo resultados.json no tiene una lista valida.")

    esperados = {e["id"]: e["oracion"] for e in corpus}
    resultados_por_id = {}

    for resultado in resultados:
        identificador = resultado.get("id")

        if identificador not in esperados:
            raise ValueError(f"ID desconocido en resultados.json: {identificador}")

        if identificador in resultados_por_id:
            raise ValueError(f"ID duplicado en resultados.json: {identificador}")

        if resultado.get("oracion") != esperados[identificador]:
            raise ValueError(
                f"La oracion del ID {identificador} no coincide con el corpus."
            )

        if resultado.get("decision") not in ("ACEPTADA", "RECHAZADA"):
            raise ValueError(
                f"Decision invalida para el ID {identificador}."
            )

        resultados_por_id[identificador] = resultado

    # Un lote se recupera si contiene al menos un ID faltante.
    lotes_por_recuperar = []

    for numero, lote in enumerate(lotes, start=1):
        ids_lote = [e["id"] for e in lote]
        faltantes = [
            identificador for identificador in ids_lote
            if identificador not in resultados_por_id
        ]

        if faltantes:
            ruta_prompt = carpeta / f"prompt_lote_{numero:02}.txt"

            if not ruta_prompt.is_file():
                raise FileNotFoundError(
                    f"No existe el prompt original del lote {numero}: "
                    f"{ruta_prompt}"
                )

            lotes_por_recuperar.append({
                "numero": numero,
                "lote": lote,
                "ids": ids_lote,
                "faltantes": faltantes,
                "ruta_prompt": ruta_prompt,
            })

    with open(ruta_llamadas, "r", encoding="utf-8") as archivo:
        llamadas = json.load(archivo)

    if not isinstance(llamadas, list):
        raise ValueError("El archivo llamadas.json no contiene una lista valida.")

    return {
        "carpeta": carpeta,
        "modo": modo,
        "metadatos": metadatos,
        "corpus": corpus,
        "lotes": lotes,
        "resultados": resultados_por_id,
        "lotes_por_recuperar": lotes_por_recuperar,
        "llamadas": llamadas,
    }


def simular_recuperacion(carpeta):
    """
    Muestra los lotes pendientes sin modificar archivos ni llamar a Gemini.
    """
    plan = preparar_recuperacion(carpeta)

    print(f"\n=== SIMULACION DE RECUPERACION: {plan['modo']} ===")
    print(f"Carpeta: {relativa(plan['carpeta'])}")
    print(f"Resultados existentes: "
          f"{len(plan['resultados'])}/{len(plan['corpus'])}")

    if not plan["lotes_por_recuperar"]:
        print("No hay lotes pendientes. La ejecucion esta completa.")
        return

    print("\nLotes que necesitan recuperacion:")

    for pendiente in plan["lotes_por_recuperar"]:
        print(
            f"  Lote {pendiente['numero']}: "
            f"IDs {pendiente['ids']} | "
            f"IDs faltantes: {pendiente['faltantes']}"
        )

    print(
        f"\nSe necesitan recuperar "
        f"{len(plan['lotes_por_recuperar'])} lote(s)."
    )
    print("Simulacion terminada. No se realizaron llamadas a Gemini.")


def recuperar_modo(client, types, carpeta):
    """
    Recupera los lotes incompletos de una ejecucion anterior.

    Conserva los resultados y las llamadas originales. Los nuevos intentos
    se guardan en una subcarpeta de recuperacion.
    """
    plan = preparar_recuperacion(carpeta)

    carpeta = plan["carpeta"]
    modo = plan["modo"]
    metadatos = plan["metadatos"]
    resultados = plan["resultados"]
    llamadas = plan["llamadas"]
    pendientes = plan["lotes_por_recuperar"]

    print(f"\n=== RECUPERACION LLM {modo} ===")
    print(f"Carpeta original: {relativa(carpeta)}")
    print(f"Resultados existentes: {len(resultados)}/{len(plan['corpus'])}")

    if not pendientes:
        print("No hay lotes pendientes. No se realizaron llamadas.")
        return True

    marca_tiempo = ahora()
    inicio_recuperacion = marca_tiempo

    carpeta_recuperacion = (
        carpeta / "recuperaciones" /
        f"recuperacion_{marca_tiempo:%Y%m%d_%H%M%S}"
    )
    carpeta_recuperacion.mkdir(parents=True, exist_ok=False)

    llamadas_recuperacion = []
    modelo = metadatos["modelo"]
    parametros = metadatos["parametros"]

    max_intentos = parametros.get("max_intentos_por_lote", MAX_INTENTOS)
    espera_base = parametros.get(
        "espera_base_segundos", ESPERA_BASE_SEGUNDOS
    )

    configuracion = types.GenerateContentConfig(
        temperature=parametros.get("temperature", TEMPERATURA),
        response_mime_type=parametros.get(
            "response_mime_type", FORMATO_RESPUESTA
        ),
    )

    print(f"Modelo original: {modelo}")
    print(f"Lotes pendientes: {len(pendientes)}")

    for pendiente in pendientes:
        numero = pendiente["numero"]
        lote = pendiente["lote"]
        ruta_prompt = pendiente["ruta_prompt"]

        # Se utiliza exactamente el prompt de la ejecucion original.
        prompt = ruta_prompt.read_text(encoding="utf-8")

        print(f"\nRecuperando lote {numero}: IDs {pendiente['ids']}")

        obtenido = False

        for intento in range(1, max_intentos + 1):
            registro = {
                "lote": numero,
                "ids": pendiente["ids"],
                "intento": intento,
                "tipo_ejecucion": "recuperacion",
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
                    config=configuracion,
                )

                fin = ahora()
                texto = response.text or ""

                ruta_respuesta = (
                    carpeta_recuperacion /
                    f"respuesta_bruta_lote_{numero:02}"
                    f"_intento_{intento:02}.txt"
                )
                ruta_respuesta.write_text(texto, encoding="utf-8")

                registro["respuesta_bruta"] = relativa(ruta_respuesta)
                registro["modelo_respondio"] = getattr(
                    response, "model_version", None
                )
                registro["tokens"] = uso_tokens(response)

                validados = validar_respuesta(texto, lote)
                registro["estado"] = "ok"

            except Exception as error:  # noqa: BLE001
                fin = ahora()
                registro["estado"] = "error"
                registro["error"] = f"{type(error).__name__}: {error}"
                validados = None

            registro["fin"] = fin.isoformat()
            registro["duracion_segundos"] = round(
                (fin - inicio).total_seconds(), 3
            )

            llamadas_recuperacion.append(registro)
            llamadas.append(registro)

            # Se conserva el historial incluso si el proceso se interrumpe.
            guardar_json(carpeta / "llamadas.json", llamadas)
            guardar_json(
                carpeta_recuperacion / "llamadas.json",
                llamadas_recuperacion,
            )

            if validados is not None:
                for resultado in validados:
                    resultados[resultado["id"]] = resultado

                # Guardar resultados después de cada lote recuperado.
                resultados_ordenados = sorted(
                    resultados.values(), key=lambda r: r["id"]
                )
                guardar_json(
                    carpeta / "resultados.json",
                    {"resultados": resultados_ordenados},
                )

                obtenido = True
                print(
                    f"  Lote {numero}: recuperado "
                    f"(intento {intento}, "
                    f"{registro['duracion_segundos']} s)"
                )
                break

            print(
                f"  Lote {numero}: intento {intento} fallo -> "
                f"{registro['error'][:160]}"
            )

            if intento < max_intentos:
                time.sleep(espera_base * 2 ** (intento - 1))

        if not obtenido:
            print(f"  Lote {numero}: continua pendiente.")

    fin_recuperacion = ahora()

    resultados_ordenados = sorted(
        resultados.values(), key=lambda r: r["id"]
    )

    ids_obtenidos = set(resultados)
    lotes_pendientes = [
        numero
        for numero, lote in enumerate(plan["lotes"], start=1)
        if any(e["id"] not in ids_obtenidos for e in lote)
    ]

    duracion = round(
        (fin_recuperacion - inicio_recuperacion).total_seconds(), 2
    )

    # Actualizar metadatos sin perder los datos de la ejecucion original.
    metadatos["total_llamadas"] = len(llamadas)
    metadatos["llamadas_fallidas"] = sum(
        llamada.get("estado") == "error" for llamada in llamadas
    )
    metadatos["resultados_obtenidos"] = len(resultados_ordenados)
    metadatos["lotes_pendientes"] = lotes_pendientes
    metadatos["ultima_recuperacion"] = {
        "inicio": inicio_recuperacion.isoformat(),
        "fin": fin_recuperacion.isoformat(),
        "duracion_segundos": duracion,
        "carpeta": relativa(carpeta_recuperacion),
        "lotes_intentados": [p["numero"] for p in pendientes],
        "lotes_pendientes": lotes_pendientes,
        "llamadas_realizadas": len(llamadas_recuperacion),
    }

    guardar_json(carpeta / "resultados.json", {
        "resultados": resultados_ordenados
    })
    guardar_json(carpeta / "metadatos.json", metadatos)

    # Actualizar el consolidado utilizado por evaluacion/evaluar.py.
    consolidado = LOGS_PATH / f"llm_{modo.replace('-', '_')}.json"
    guardar_json(consolidado, {
        "metadatos": metadatos,
        "llamadas": llamadas,
        "resultados": resultados_ordenados,
    })

    print("\n=== RESUMEN DE RECUPERACION ===")
    print(
        f"Resultados: {len(resultados_ordenados)}/"
        f"{len(plan['corpus'])}"
    )
    print(f"Llamadas nuevas: {len(llamadas_recuperacion)}")
    print(f"Lotes pendientes: {lotes_pendientes or 'ninguno'}")
    print(f"Log consolidado: {relativa(consolidado)}")

    return not lotes_pendientes


# --------------------------------------------------
# Punto de entrada
# --------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta o recupera experimentos LLM con Google Gemini."
        )
    )

    parser.add_argument(
        "modo",
        choices=["zero-shot", "few-shot", "ambos", "recuperar"],
        help="Modo de ejecucion o recuperacion.",
    )

    parser.add_argument(
        "--modelo",
        default=None,
        help=(
            "Modelo de Gemini para nuevas ejecuciones "
            "(por defecto GEMINI_MODEL del .env)."
        ),
    )

    parser.add_argument(
        "--carpeta",
        default=None,
        help="Carpeta de evidencia que se desea recuperar.",
    )

    parser.add_argument(
        "--simular",
        action="store_true",
        help="Analiza los lotes pendientes sin llamar a Gemini.",
    )

    args = parser.parse_args(argv)

    if args.modo == "recuperar" and not args.carpeta:
        parser.error("El modo recuperar requiere --carpeta.")

    if args.modo != "recuperar" and (args.carpeta or args.simular):
        parser.error("--carpeta y --simular solo se utilizan con recuperar.")

    if args.modo == "recuperar" and args.modelo:
        parser.error(
            "La recuperacion utiliza el modelo de la ejecucion original. "
            "No se permite cambiarlo."
        )

    # Garantiza que las plantillas versionadas estan actualizadas.
    desactualizadas = verificar_plantillas()
    if desactualizadas:
        sys.exit(
            "Las plantillas llm/prompt_*.txt no coinciden con llm/prompts.py "
            f"({', '.join(desactualizadas)}). Ejecuta: "
            "python -m llm.prompts"
        )

    # Simulacion: no requiere API key ni realiza llamadas.
    if args.modo == "recuperar" and args.simular:
        simular_recuperacion(args.carpeta)
        return

    from dotenv import load_dotenv
    from google import genai
    from google.genai import types

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        sys.exit(
            "Falta GEMINI_API_KEY. Copia .env.example a .env "
            "y coloca tu clave."
        )

    client = genai.Client(api_key=api_key)

    if args.modo == "recuperar":
        completo = recuperar_modo(client, types, args.carpeta)

        if not completo:
            sys.exit(1)

        return

    modelo = (
        args.modelo
        or os.getenv("GEMINI_MODEL")
        or MODELO_POR_DEFECTO
    )

    modos = (
        ["zero-shot", "few-shot"]
        if args.modo == "ambos"
        else [args.modo]
    )

    completos = [
        ejecutar_modo(client, types, modo, modelo)
        for modo in modos
    ]

    if not all(completos):
        sys.exit(1)


if __name__ == "__main__":
    main()
