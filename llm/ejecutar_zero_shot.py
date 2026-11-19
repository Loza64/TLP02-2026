import os
import csv
import json
import hashlib
import platform
import subprocess
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types

from llm.prompts import construir_prompt_zero_shot


# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "corpus" / "corpus_pruebas.csv"
LOGS_PATH = ROOT / "logs"

MODELO = "gemini-3.5-flash-lite"
TAMANO_LOTE = 5

load_dotenv(ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("No se encontro GEMINI_API_KEY en el archivo .env")

client = genai.Client(api_key=api_key)


# --------------------------------------------------
# FUNCIONES AUXILIARES
# --------------------------------------------------

def obtener_commit():
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        return resultado.stdout.strip()
    except Exception:
        return None


def guardar_json(ruta, contenido):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)


def cargar_corpus():
    with open(CORPUS_PATH, "r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)

        return [
            {
                "id": int(fila["id"]),
                "oracion": fila["oracion"],
                "esperado": fila["esperado"]
            }
            for fila in lector
        ]


# --------------------------------------------------
# EJECUCION
# --------------------------------------------------

def ejecutar():
    corpus = cargar_corpus()
    if not corpus:
        raise ValueError("El corpus está vacío.")
    
    contenido_csv = CORPUS_PATH.read_bytes()
    hash_corpus = hashlib.sha256(contenido_csv).hexdigest()

    marca_tiempo = datetime.now().astimezone()
    nombre_ejecucion = marca_tiempo.strftime("%Y%m%d_%H%M%S")

    carpeta_salida = LOGS_PATH / f"llm_zero_shot_{nombre_ejecucion}"
    carpeta_salida.mkdir(parents=True, exist_ok=False)

    resultados_totales = []
    errores = []
    lotes = [
        corpus[i:i + TAMANO_LOTE]
        for i in range(0, len(corpus), TAMANO_LOTE)
    ]

    inicio_total = datetime.now().astimezone()

    print(f"Modelo: {MODELO}")
    print(f"Oraciones: {len(corpus)}")
    print(f"Lotes: {len(lotes)}")
    print("Iniciando evaluacion zero-shot...\n")

    for numero, lote in enumerate(lotes, start=1):
        print(f"Procesando lote {numero}/{len(lotes)}...")

        prompt = construir_prompt_zero_shot([
            {
                "id": elemento["id"],
                "oracion": elemento["oracion"]
            }
            for elemento in lote
        ])

        (carpeta_salida / f"prompt_lote_{numero:02}.txt").write_text(
            prompt,
            encoding="utf-8"
        )

        inicio_lote = datetime.now().astimezone()

        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )

            respuesta_bruta = response.text or ""

            (carpeta_salida / f"respuesta_bruta_lote_{numero:02}.txt").write_text(
                respuesta_bruta,
                encoding="utf-8"
            )

            datos = json.loads(respuesta_bruta)
            resultados = datos["resultados"]

            # Validar estructura y correspondencia de IDs
            ids_esperados = {elemento["id"] for elemento in lote}
            ids_recibidos = [r.get("id") for r in resultados]

            if (
                set(ids_recibidos) != ids_esperados
                or len(ids_recibidos) != len(ids_esperados)
            ):
                raise ValueError("Los IDs recibidos no coinciden con los del lote.")

            oraciones_por_id = {
                elemento["id"]: elemento["oracion"]
                for elemento in lote
            }

            for resultado in resultados:
                if resultado.get("decision") not in ("ACEPTADA", "RECHAZADA"):
                    raise ValueError(
                        f"Decision invalida para ID {resultado.get('id')}"
                    )

                if resultado.get("oracion") != oraciones_por_id[resultado["id"]]:
                    raise ValueError(
                        f"La oracion del ID {resultado['id']} fue modificada."
                    )

            guardar_json(
                carpeta_salida / f"resultados_lote_{numero:02}.json",
                datos
            )

            resultados_totales.extend(resultados)

            print(f"  Lote {numero} completado correctamente.")

        except Exception as error:
            errores.append({
                "lote": numero,
                "ids": [elemento["id"] for elemento in lote],
                "tipo": type(error).__name__,
                "mensaje": str(error)
            })

            print(f"  Error en lote {numero}: {error}")

        fin_lote = datetime.now().astimezone()

        print(f"  Duracion: {(fin_lote - inicio_lote).total_seconds():.2f} segundos\n")

    fin_total = datetime.now().astimezone()

    # Guardar resultados combinados
    guardar_json(
        carpeta_salida / "resultados.json",
        {"resultados": resultados_totales}
    )

    # Guardar metadatos de la ejecucion
    metadatos = {
        "tipo_prompt": "zero-shot",
        "modelo": MODELO,
        "temperatura": 0,
        "formato_respuesta": "application/json",
        "total_oraciones": len(corpus),
        "total_lotes": len(lotes),
        "tamano_lote": TAMANO_LOTE,
        "resultados_obtenidos": len(resultados_totales),
        "errores": errores,
        "inicio": inicio_total.isoformat(),
        "fin": fin_total.isoformat(),
        "duracion_segundos": round(
            (fin_total - inicio_total).total_seconds(), 2
        ),
        "hash_sha256_corpus": hash_corpus,
        "commit_git": obtener_commit(),
        "sistema_operativo": platform.platform(),
        "version_python": platform.python_version()
    }

    guardar_json(carpeta_salida / "metadatos.json", metadatos)

    print("------------------------------------")
    print("EVALUACION FINALIZADA")
    print("------------------------------------")
    print(f"Resultados obtenidos: {len(resultados_totales)}/{len(corpus)}")
    print(f"Errores: {len(errores)}")
    print(f"Archivos guardados en: {carpeta_salida}")


if __name__ == "__main__":
    ejecutar()
