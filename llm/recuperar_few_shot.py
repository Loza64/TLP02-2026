
import os
import csv
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
CORPUS = ROOT / "corpus" / "corpus_pruebas.csv"

load_dotenv(ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("No se encontro GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)

LOTES_PENDIENTES = [1, 2, 4, 6]
MAX_INTENTOS = 5


# --------------------------------------------------
# BUSCAR EJECUCION
# --------------------------------------------------

carpetas = sorted(
    LOGS.glob("llm_few_shot_*"),
    key=lambda ruta: ruta.stat().st_mtime,
    reverse=True
)

if not carpetas:
    raise FileNotFoundError("No se encontro una ejecucion few-shot.")

carpeta = carpetas[0]

print(f"Carpeta de ejecucion: {carpeta}")


# --------------------------------------------------
# CARGAR CORPUS
# --------------------------------------------------

with open(CORPUS, "r", encoding="utf-8-sig", newline="") as archivo:
    lector = csv.DictReader(archivo)

    oraciones = {
        int(fila["id"]): fila["oracion"]
        for fila in lector
    }


# --------------------------------------------------
# RECUPERAR LOTES
# --------------------------------------------------

intentos_registrados = []

for numero in LOTES_PENDIENTES:

    resultado_path = carpeta / f"resultados_lote_{numero:02}.json"
    prompt_path = carpeta / f"prompt_lote_{numero:02}.txt"
    respuesta_path = carpeta / f"respuesta_bruta_lote_{numero:02}.txt"

    if resultado_path.exists():
        print(f"Lote {numero}: ya existe, se omite.")
        continue

    if not prompt_path.exists():
        raise FileNotFoundError(f"No existe {prompt_path.name}")

    prompt = prompt_path.read_text(encoding="utf-8")

    ids_esperados = list(
        range((numero - 1) * 5 + 1, (numero - 1) * 5 + 6)
    )

    print(f"\nRecuperando lote {numero}: IDs {ids_esperados}")

    recuperado = False

    for intento in range(1, MAX_INTENTOS + 1):

        try:
            print(f"Intento {intento}/{MAX_INTENTOS}...")

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )

            respuesta = response.text or ""
            datos = json.loads(respuesta)
            resultados = datos["resultados"]

            ids_recibidos = [r.get("id") for r in resultados]

            if (
                set(ids_recibidos) != set(ids_esperados)
                or len(ids_recibidos) != len(ids_esperados)
            ):
                raise ValueError("Los IDs recibidos no coinciden.")

            for resultado in resultados:

                identificador = resultado["id"]

                if resultado.get("decision") not in (
                    "ACEPTADA", "RECHAZADA"
                ):
                    raise ValueError(
                        f"Decision invalida en ID {identificador}"
                    )

                if resultado.get("oracion") != oraciones[identificador]:
                    raise ValueError(
                        f"Oracion modificada en ID {identificador}"
                    )

            respuesta_path.write_text(
                respuesta,
                encoding="utf-8"
            )

            with open(resultado_path, "w", encoding="utf-8") as archivo:
                json.dump(
                    datos,
                    archivo,
                    ensure_ascii=False,
                    indent=2
                )

            print(f"Lote {numero} recuperado correctamente.")
            recuperado = True

            intentos_registrados.append({
                "lote": numero,
                "estado": "recuperado",
                "intento_exitoso": intento
            })

            break

        except Exception as error:

            print(f"Error: {type(error).__name__}: {error}")

            intentos_registrados.append({
                "lote": numero,
                "intento": intento,
                "error": f"{type(error).__name__}: {error}"
            })

            if intento < MAX_INTENTOS:
                espera = 15 * intento
                print(f"Esperando {espera} segundos...")
                time.sleep(espera)

    if not recuperado:
        print(f"No fue posible recuperar el lote {numero}.")

    # Pausa entre lotes para reducir solicitudes consecutivas
    if numero != LOTES_PENDIENTES[-1]:
        time.sleep(10)


# --------------------------------------------------
# RECONSTRUIR RESULTADOS
# --------------------------------------------------

resultados_totales = []

for numero in range(1, 9):

    ruta = carpeta / f"resultados_lote_{numero:02}.json"

    if not ruta.exists():
        print(f"\nTodavia falta el lote {numero}.")
        continue

    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    resultados_totales.extend(datos["resultados"])


ids = [r["id"] for r in resultados_totales]

if len(ids) != len(set(ids)):
    raise ValueError("Se encontraron IDs duplicados.")

with open(carpeta / "resultados.json", "w", encoding="utf-8") as archivo:
    json.dump(
        {"resultados": sorted(resultados_totales, key=lambda r: r["id"])},
        archivo,
        ensure_ascii=False,
        indent=2
    )


# Guardar evidencia de recuperacion
with open(
    carpeta / "recuperacion.json",
    "w",
    encoding="utf-8"
) as archivo:
    json.dump(
        intentos_registrados,
        archivo,
        ensure_ascii=False,
        indent=2
    )


# Actualizar metadatos sin borrar los errores iniciales
metadatos_path = carpeta / "metadatos.json"

if metadatos_path.exists():
    with open(metadatos_path, "r", encoding="utf-8") as archivo:
        metadatos = json.load(archivo)

    metadatos["resultados_obtenidos"] = len(resultados_totales)
    metadatos["recuperacion_realizada"] = True
    metadatos["errores_pendientes"] = [
        numero
        for numero in range(1, 9)
        if not (carpeta / f"resultados_lote_{numero:02}.json").exists()
    ]

    metadatos["recuperacion"] = "recuperacion.json"

    with open(metadatos_path, "w", encoding="utf-8") as archivo:
        json.dump(
            metadatos,
            archivo,
            ensure_ascii=False,
            indent=2
        )


print("\n------------------------------------")
print("RECUPERACION FEW-SHOT FINALIZADA")
print("------------------------------------")
print(f"Resultados obtenidos: {len(resultados_totales)}/40")

if len(resultados_totales) == 40:
    print("Evaluacion completa: 40/40.")
else:
    print("Evaluacion incompleta. Todavia hay lotes pendientes.")

print(f"Archivos guardados en: {carpeta}")
