
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"

load_dotenv(ROOT / ".env")

import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Buscar la ejecucion mas reciente
carpetas = sorted(
    LOGS.glob("llm_zero_shot_*"),
    key=lambda ruta: ruta.stat().st_mtime,
    reverse=True
)

if not carpetas:
    raise RuntimeError("No se encontraron ejecuciones.")

carpeta = carpetas[0]

prompt_path = carpeta / "prompt_lote_01.txt"
respuesta_path = carpeta / "respuesta_bruta_lote_01.txt"
resultado_path = carpeta / "resultados_lote_01.json"

if not prompt_path.exists():
    raise FileNotFoundError("No se encontro el prompt del lote 1.")

prompt = prompt_path.read_text(encoding="utf-8")

# Reintentar hasta 4 veces
for intento in range(1, 5):
    try:
        print(f"Intento {intento}/4 para recuperar el lote 1...")

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

        if len(datos["resultados"]) != 5:
            raise ValueError("El lote no contiene exactamente 5 resultados.")

        ids = {r["id"] for r in datos["resultados"]}

        if ids != {1, 2, 3, 4, 5}:
            raise ValueError("Los IDs del lote no son los esperados.")

        for r in datos["resultados"]:
            if r["decision"] not in ("ACEPTADA", "RECHAZADA"):
                raise ValueError("Se encontro una decision invalida.")

        respuesta_path.write_text(respuesta, encoding="utf-8")

        with open(resultado_path, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)

        print("Lote 1 recuperado correctamente.")
        break

    except Exception as error:
        print(f"Error: {type(error).__name__}: {error}")

        if intento == 4:
            raise

        espera = intento * 5
        print(f"Esperando {espera} segundos...")
        time.sleep(espera)


# Reconstruir los resultados de los 8 lotes
resultados_totales = []

for numero in range(1, 9):
    ruta = carpeta / f"resultados_lote_{numero:02}.json"

    if not ruta.exists():
        raise FileNotFoundError(f"Falta el archivo: {ruta.name}")

    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    resultados_totales.extend(datos["resultados"])

# Comprobar que no falte ni se repita ningun ID
ids = [r["id"] for r in resultados_totales]

if len(ids) != 40 or set(ids) != set(range(1, 41)):
    raise ValueError("Los resultados no contienen los 40 IDs unicos.")

with open(carpeta / "resultados.json", "w", encoding="utf-8") as archivo:
    json.dump(
        {"resultados": resultados_totales},
        archivo,
        ensure_ascii=False,
        indent=2
    )

print("\nRecuperación zero-shot finalizada: 40/40 resultados.")
print(f"Resultados guardados en: {carpeta}")
