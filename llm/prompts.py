"""
Prompts para la evaluacion de oraciones mediante Gemini.

Experimentos:
- Zero-shot: instrucciones + gramatica + lexico, sin ejemplos.
- Few-shot: mismas instrucciones + gramatica + lexico,
  incorporando ejemplos resueltos.
"""

import json
import sys
from pathlib import Path

from espanol.grammar import START, PRODUCTIONS, TERMINALS
from espanol.lexer import LEXICON


# --------------------------------------------------
# 1. Formatear la gramatica
# --------------------------------------------------

def formatear_gramatica():
    lineas = []

    for no_terminal, simbolos in PRODUCTIONS:
        derecha = " ".join(simbolos) if simbolos else "ε"
        lineas.append(f"{no_terminal} -> {derecha}")

    return "\n".join(lineas)


# --------------------------------------------------
# 2. Formatear el lexico
# --------------------------------------------------

def formatear_lexico():
    lineas = []

    for palabra, categoria in sorted(LEXICON.items()):
        lineas.append(f"{palabra} -> {categoria}")

    return "\n".join(lineas)


# --------------------------------------------------
# 3. Ejemplos para few-shot
# --------------------------------------------------

EJEMPLOS_FEW_SHOT = [
    {
        "oracion": "Unos perros grandes corren en el parque.",
        "decision": "ACEPTADA",
        "justificacion": (
            "La oracion puede derivarse mediante las producciones "
            "para sujeto plural masculino, adjetivo invariable, "
            "verbo plural y frase preposicional."
        )
    },
    {
        "oracion": "La perra corre tranquilamente bajo la casa.",
        "decision": "ACEPTADA",
        "justificacion": (
            "La oracion presenta un sujeto femenino singular, "
            "un verbo singular, un adverbio de modo y una frase "
            "preposicional permitidos por la gramatica."
        )
    },
    {
        "oracion": "La gato negro duerme.",
        "decision": "RECHAZADA",
        "justificacion": (
            "El determinante femenino singular no concuerda "
            "con el sustantivo masculino singular. "
            "No existe una produccion que permita esa combinacion."
        )
    },
    {
        "oracion": "La perra corren.",
        "decision": "RECHAZADA",
        "justificacion": (
            "El sujeto es femenino singular, pero el verbo "
            "esta conjugado en plural. No se cumple la concordancia "
            "entre sujeto y verbo."
        )
    }
]


def formatear_ejemplos():
    """
    Convierte los ejemplos few-shot en texto legible.
    """

    lineas = []

    for numero, ejemplo in enumerate(EJEMPLOS_FEW_SHOT, start=1):
        lineas.append(
            f"""
Ejemplo {numero}:

Oracion: {ejemplo["oracion"]}
Decision: {ejemplo["decision"]}
Justificacion: {ejemplo["justificacion"]}
""".strip()
        )

    return "\n\n".join(lineas)


# --------------------------------------------------
# 4. Construir el prompt base
# --------------------------------------------------

MARCADOR_ORACIONES = "<<ORACIONES_A_EVALUAR>>"

RUTA_PLANTILLAS = {
    "zero-shot": Path(__file__).resolve().parent / "prompt_zero_shot.txt",
    "few-shot": Path(__file__).resolve().parent / "prompt_few_shot.txt",
}


def construir_plantilla(incluir_ejemplos=False):
    """
    Devuelve el prompt completo con un marcador en lugar de las oraciones.
    Es exactamente el texto que se envia a la API; solo cambia el bloque
    final de oraciones de cada lote.
    """

    gramatica = formatear_gramatica()
    lexico = formatear_lexico()
    terminales = ", ".join(str(t) for t in TERMINALS)

    seccion_ejemplos = ""

    if incluir_ejemplos:
        seccion_ejemplos = f"""
EJEMPLOS RESUELTOS:

Los siguientes ejemplos muestran como aplicar
las reglas de la gramatica.

Utilizalos como referencia para realizar el analisis,
pero evalua cada nueva oracion de manera independiente.

{formatear_ejemplos()}

IMPORTANTE:
Los ejemplos son demostraciones del procedimiento.
No debes asumir que las oraciones nuevas tienen
la misma estructura o decision que estos ejemplos.
"""

    instrucciones = f"""
Actua como un analizador sintactico formal
especializado en gramatica libre de contexto (CFG).

OBJETIVO:

Determinar si cada oracion pertenece al lenguaje
generado por la gramatica proporcionada.

IMPORTANTE:

No debes determinar si una oracion es correcta
en el espanol general.

Debes determinar exclusivamente si puede generarse
mediante las producciones de esta gramatica y
utilizando las palabras de su lexico.

REGLAS DE EVALUACION:

1. Utiliza exclusivamente las producciones indicadas.
2. Comienza siempre desde el simbolo inicial.
3. Respeta las categorias terminales del lexico.
4. Respeta la concordancia de genero y numero
   entre determinantes, sustantivos y adjetivos.
5. Respeta la concordancia de numero entre
   el sujeto y el verbo.
6. No aceptes palabras que no aparezcan en el lexico.
7. No inventes producciones ni estructuras.
8. No completes estructuras incompletas por intuicion.
9. No aceptes coordinaciones u otras construcciones
   que no esten contempladas en las producciones.
10. Una oracion gramatical en espanol puede ser
    rechazada si no pertenece al lenguaje de esta CFG.

DECISIONES:

- ACEPTADA: la oracion puede derivarse desde el
  simbolo inicial utilizando las producciones y
  terminales proporcionados.
- RECHAZADA: no existe una derivacion valida
  para la oracion o contiene palabras fuera del lexico.

GRAMATICA:

Simbolo inicial: {START}

Producciones:
{gramatica}

TERMINALES:
{terminales}

LEXICO:

Cada palabra debe corresponder a su categoria
terminal indicada:

{lexico}

{seccion_ejemplos}

FORMATO DE RESPUESTA:

Devuelve exclusivamente un objeto JSON valido
con esta estructura:

{{
  "resultados": [
    {{
      "id": 1,
      "oracion": "El gato negro duerme.",
      "decision": "ACEPTADA",
      "producciones_aplicadas": [
        "Oracion -> ..."
      ],
      "justificacion": "Explicacion breve.",
      "estructura": "Representacion sintactica."
    }}
  ]
}}

INDICACIONES PARA EL JSON:

- Incluye todos los IDs recibidos.
- Conserva exactamente el texto de cada oracion.
- La decision debe ser ACEPTADA o RECHAZADA.
- Si es RECHAZADA, explica el motivo concreto.
- No inventes producciones aplicadas.
- Si no existe una derivacion, deja
  producciones_aplicadas como lista vacia
  y estructura como null.
- Si no puedes determinar una estructura,
  utiliza null en estructura.
- No incluyas Markdown ni bloques de codigo.
- No agregues explicaciones fuera del JSON.

ORACIONES A EVALUAR:

{MARCADOR_ORACIONES}
"""

    return instrucciones.strip()


def construir_prompt(oraciones, incluir_ejemplos=False):
    plantilla = construir_plantilla(incluir_ejemplos)
    return plantilla.replace(
        MARCADOR_ORACIONES,
        json.dumps(oraciones, ensure_ascii=False, indent=2)
    )


# --------------------------------------------------
# 5. Construir prompts de cada experimento
# --------------------------------------------------

def construir_prompt_zero_shot(oraciones):
    return construir_prompt(oraciones, incluir_ejemplos=False)


def construir_prompt_few_shot(oraciones):
    return construir_prompt(oraciones, incluir_ejemplos=True)


def plantilla_por_modo(modo):
    return construir_plantilla(incluir_ejemplos=(modo == "few-shot"))


def exportar_plantillas():
    """Escribe llm/prompt_zero_shot.txt y llm/prompt_few_shot.txt."""
    for modo, ruta in RUTA_PLANTILLAS.items():
        ruta.write_text(plantilla_por_modo(modo) + "\n", encoding="utf-8")
        print(f"Plantilla {modo} escrita en {ruta.name}")


def verificar_plantillas():
    """
    Comprueba que los .txt versionados coinciden con el prompt que genera
    el codigo. Devuelve la lista de modos desactualizados.
    """
    desactualizados = []
    for modo, ruta in RUTA_PLANTILLAS.items():
        if not ruta.exists():
            desactualizados.append(modo)
            continue
        en_disco = ruta.read_text(encoding="utf-8").rstrip("\n")
        if en_disco != plantilla_por_modo(modo):
            desactualizados.append(modo)
    return desactualizados


if __name__ == "__main__":
    # python -m llm.prompts            -> regenera los .txt
    # python -m llm.prompts --verificar -> solo comprueba
    if "--verificar" in sys.argv:
        pendientes = verificar_plantillas()
        if pendientes:
            print("Plantillas desactualizadas:", ", ".join(pendientes))
            sys.exit(1)
        print("Plantillas al dia.")
    else:
        exportar_plantillas()
