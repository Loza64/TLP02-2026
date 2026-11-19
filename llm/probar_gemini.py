
import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

from llm.prompts import construir_prompt_zero_shot


# Cargar API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("No se encontró GEMINI_API_KEY.")

# Crear cliente
client = genai.Client(api_key=api_key)

# Oraciones de prueba
oraciones = [
    {
        "id": 1,
        "oracion": "El gato negro duerme."
    },
    {
        "id": 35,
        "oracion": "El elefante negro duerme."
    }
]

# Construir prompt
prompt = construir_prompt_zero_shot(oraciones)

print("Enviando oraciones a Gemini...")
print("Modelo: gemini-3.5-flash-lite")

try:
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json"
        )
    )

    # Obtener respuesta
    respuesta_texto = response.text

    # Convertir respuesta JSON a diccionario
    resultados = json.loads(respuesta_texto)

    print("\nRespuesta recibida correctamente:")
    print(json.dumps(resultados, ensure_ascii=False, indent=2))

except json.JSONDecodeError as error:
    print("Gemini no devolvió un JSON válido.")
    print(error)

except Exception as error:
    print("Ocurrió un error al consultar Gemini:")
    print(type(error).__name__)
    print(error)
