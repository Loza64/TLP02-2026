
from llm.prompts import (
    construir_prompt_zero_shot,
    construir_prompt_few_shot
)

oraciones = [
    {"id": 1, "oracion": "El gato negro duerme."},
    {"id": 35, "oracion": "El elefante negro duerme."}
]

prompt_zero = construir_prompt_zero_shot(oraciones)
prompt_few = construir_prompt_few_shot(oraciones)

print("ZERO-SHOT")
print(f"Caracteres: {len(prompt_zero)}")

print("\nFEW-SHOT")
print(f"Caracteres: {len(prompt_few)}")

print("\nEjemplos incluidos:")
print("Unos perros grandes corren en el parque.")
print("La perra corre tranquilamente bajo la casa.")
print("La gato negro duerme.")
print("La perra corren.")

print("\nPrueba de construccion completada.")
