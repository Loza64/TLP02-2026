
from llm.prompts import construir_prompt_zero_shot

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

prompt = construir_prompt_zero_shot(oraciones)

print(prompt)
print("\nLongitud del prompt:", len(prompt), "caracteres")
