# Resultados cuantitativos (generado por `evaluacion/evaluar.py`)

> Archivo generado automáticamente a partir de los logs. No editar a mano.

## Tabla comparativa

| Métrica | Parser propio | spaCy | HuggingFace | LLM zero-shot | LLM few-shot |
|---|---:|---:|---:|---:|---:|
| Precisión (%) | 100.00 | 88.46 | 80.00 | 100.00 | 100.00 |
| Recall (%) | 100.00 | 82.14 | 100.00 | 100.00 | 100.00 |
| Rechazo correcto (%) | 100.00 | 75.00 | 41.67 | 100.00 | 100.00 |
| VP | 28 | 23 | 28 | 28 | 28 |
| VN | 12 | 9 | 5 | 12 | 12 |
| FP | 0 | 3 | 7 | 0 | 0 |
| FN | 0 | 5 | 0 | 0 | 0 |
| Errores de etiquetado | 0 | 8 | 0 | 2 | 22 |
| Exactitud (%) | 100.00 | 80.00 | 82.50 | 100.00 | 100.00 |

## Errores de clasificación (FP + FN) por nivel

| Nivel | Parser propio | spaCy | HuggingFace | LLM zero-shot | LLM few-shot |
|---|---:|---:|---:|---:|---:|
| 1 | 0 (FP 0, FN 0) | 2 (FP 0, FN 2) | 0 (FP 0, FN 0) | 0 (FP 0, FN 0) | 0 (FP 0, FN 0) |
| 2 | 0 (FP 0, FN 0) | 3 (FP 0, FN 3) | 0 (FP 0, FN 0) | 0 (FP 0, FN 0) | 0 (FP 0, FN 0) |
| 3 | 0 (FP 0, FN 0) | 3 (FP 3, FN 0) | 7 (FP 7, FN 0) | 0 (FP 0, FN 0) | 0 (FP 0, FN 0) |

## Cumplimiento de la CFG por el LLM

| Indicador | LLM zero-shot | LLM few-shot |
|---|---:|---:|
| Reglas citadas | 346 | 322 |
| Reglas citadas que no existen en la CFG | 0 | 3 |
| Árboles idénticos al del parser propio | 24/28 | 23/28 |
| Errores de etiquetado | 2 | 22 |

## Fuentes

- **Parser propio**: parser propio LL(1) (CFG del español, Fase 1) — `logs/parser_propio.json`. Etiquetado: 0 por construccion: el parser asigna las categorias desde el lexico de la CFG, que es la referencia.
- **spaCy**: spaCy 3.8.18 (es_core_news_sm) — `logs/spacy.json`. Etiquetado: POS de la herramienta frente al lexico de la CFG (criterio de nlp/comun.py).
- **HuggingFace**: HuggingFace Transformers 5.23.0 (mrm8488/bert-spanish-cased-finetuned-pos, mrm8488/bert-spanish-cased-finetuned-pos-syntax) — `logs/segunda_herramienta.json`. Etiquetado: POS de la herramienta frente al lexico de la CFG (criterio de nlp/comun.py).
- **LLM zero-shot**: Google Gemini (gemini-3.5-flash-lite, temperatura 0) — `logs/llm_zero_shot_20261118_150630`. Etiquetado: Categoria de cada palabra en la estructura devuelta frente al lexico de la CFG.
- **LLM few-shot**: Google Gemini (gemini-3.5-flash-lite, temperatura 0) — `logs/llm_few_shot_20261118_153422`. Etiquetado: Categoria de cada palabra en la estructura devuelta frente al lexico de la CFG.

N/D: la métrica no se puede calcular porque su denominador es 0.
