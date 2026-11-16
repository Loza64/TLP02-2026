# Criterios de diseño del corpus de prueba (Fase 2)

**Integrante 1 — Corpus de prueba y etiquetas esperadas**  
Archivo: `corpus/corpus_pruebas.csv` (40 oraciones)

## Objetivo

Definir un conjunto fijo de oraciones con etiquetas `ACEPTADA` / `RECHAZADA` **antes** de ejecutar spaCy, NLTK/Transformers o el LLM. La referencia no es la intuición sobre el español general, sino la CFG LL(1) de la Fase 1 (`espanol/grammar.py` + léxico de `espanol/lexer.py`).

## Distribución

| Nivel | Cantidad | Esperado | Criterio |
|------:|---------:|----------|----------|
| 1 | 12 | ACEPTADA | Oraciones simples (determinante + sustantivo ± adjetivo + verbo + `.`) |
| 2 | 16 | ACEPTADA | Modificadores contemplados: `muy`, adverbios de modo, SP (`en`/`con`/`bajo`), relativa `que` + SV, completiva `observa que` + cláusula |
| 3 | 12 | RECHAZADA | Discordancia de género/número, coordinación con `y` (conflicto LL(1)), léxico ajeno o estructuras incompletas |

## Vocabulario admitido

Solo se usan formas presentes en `LEXICON` (p. ej. `el/la/los/las`, `gato/gata/...`, `negro/negra/...`, `grande/grandes`, `duerme/corre/juega/observa` y plurales, `muy`, `rápidamente`/`tranquilamente`, `en`/`con`/`bajo`, `que`, `y`). Cualquier palabra fuera del léxico se etiqueta `RECHAZADA` (error léxico), aunque sea español correcto.

## Casos canónicos incluidos

| Oración | Nivel | Esperado | Fenómeno |
|---------|------:|----------|----------|
| El gato negro duerme. | 1 | ACEPTADA | Concordancia básica |
| La gata muy rápida corre rápidamente en el jardín. | 2 | ACEPTADA | Intensificador + adv. de modo + SP |
| El gato negra duerme. | 3 | RECHAZADA | Discordancia de género |
| El niño y la niña duermen. | 3 | RECHAZADA | Coordinación (conflicto LL(1)) |

## Criterio de etiquetado

1. **ACEPTADA** solo si el parser LL(1) del proyecto acepta la oración con el léxico actual.
2. **RECHAZADA** si falla el lexer o el análisis predictivo (discordancia, coordinación, SP/completiva incompleta, palabra desconocida).
3. Una oración puede ser gramatical en español y aun así marcarse `RECHAZADA`: está fuera del alcance de la CFG, no “mal escrita” en sentido absoluto.

## Columnas del CSV

`id`, `oracion`, `nivel`, `esperado`, `fenomeno`

La columna `fenomeno` resume el fenómeno sintáctico o el motivo de rechazo para el análisis de errores (Integrantes 2–4).

## Verificación

Tras construir el CSV, las 40 filas se contrastaron con `espanol.parser.accepts` para confirmar que `esperado` coincide con el comportamiento real del parser propio.
