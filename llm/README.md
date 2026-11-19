# LLM mediante API (Fase 2, enfoque D)

Se evalúa si un LLM respeta una gramática formal cuando se le entregan explícitamente sus
reglas. El modelo recibe la CFG del español de la Fase 1 y decide, para cada oración de
`corpus/corpus_pruebas.csv`, si **pertenece al lenguaje generado por la gramática** (no si es
correcta en el español general).

| Modalidad | Qué recibe |
|---|---|
| **Zero-shot** | Instrucciones + todas las producciones + símbolo inicial + terminales + léxico. Sin ejemplos. |
| **Few-shot** | Exactamente lo mismo, más 4 ejemplos resueltos (2 ACEPTADA, 2 RECHAZADA) con la justificación de por qué cumplen o no la gramática. Ninguno pertenece al corpus. |

Las dos modalidades salen de la misma función (`llm/prompts.py`), así que las instrucciones
son idénticas; la única diferencia es el bloque `EJEMPLOS RESUELTOS`
(`tests/test_llm_evaluacion.py` lo comprueba).

## Prompts exactos

- `llm/prompt_zero_shot.txt`
- `llm/prompt_few_shot.txt`

Son el texto completo enviado a la API. El marcador `<<ORACIONES_A_EVALUAR>>` se sustituye
por el JSON con las 5 oraciones del lote (`[{"id": ..., "oracion": ...}]`). El prompt
efectivamente enviado en cada llamada se guarda además como `prompt_lote_XX.txt`.

Los `.txt` se generan desde `espanol/grammar.py` y `espanol/lexer.py`:

```bash
python -m llm.prompts              # regenerar
python -m llm.prompts --verificar  # comprobar que están al día
```

`ejecutar_llm.py` se niega a correr si los `.txt` no coinciden con lo que genera el código,
de modo que el archivo versionado siempre es el prompt real.

Para cada oración se pide: ID, decisión (ACEPTADA/RECHAZADA), producciones aplicadas,
justificación y estructura sintáctica.

## Configuración

```bash
python -m pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

En `.env` (ignorado por git):

```env
GEMINI_API_KEY=tu_clave
GEMINI_MODEL=gemini-3.5-flash-lite   # opcional
```

| Parámetro | Valor |
|---|---|
| Proveedor / SDK | Google Gemini / `google-genai` 3.5.0 |
| Modelo | `gemini-3.5-flash-lite` |
| `temperature` | 0 |
| `response_mime_type` | `application/json` |
| Tamaño de lote | 5 oraciones (8 llamadas por modalidad) |
| Reintentos | hasta 5 intentos por lote, espera exponencial de 10, 20, 40 y 80 s |

## Ejecución

```bash
python -m llm.ejecutar_llm ambos        # zero-shot y luego few-shot
python -m llm.ejecutar_llm zero-shot
python -m llm.ejecutar_llm few-shot
python -m evaluacion.evaluar            # métricas, tablas y gráficas
```

Cada respuesta se valida antes de aceptarla: JSON válido, exactamente los IDs del lote,
decisión ACEPTADA o RECHAZADA y la oración sin modificar. Si una validación o la API fallan,
el intento queda registrado y se reintenta. Las respuestas **nunca se reconstruyen**: si un
lote no se obtiene, queda en `lotes_pendientes` y el comando termina con código 1.

## Evidencia generada

`logs/llm_<modo>_<AAAAMMDD_HHMMSS>/`:

| Archivo | Contenido |
|---|---|
| `prompt_lote_XX.txt` | Prompt exacto enviado en el lote XX |
| `respuesta_bruta_lote_XX_intento_N.txt` | Respuesta completa de la API, sin tocar, de cada intento |
| `llamadas.json` | **Una entrada por llamada**: lote, IDs, intento, timestamp de inicio y fin, duración, estado, error, versión del modelo que respondió y tokens usados |
| `metadatos.json` | Modelo, parámetros, número de ejemplos, hash SHA-256 del prompt y del corpus, inicio/fin, versiones de Python y `google-genai`, sistema operativo y commit |
| `resultados.json` | Resultados validados de las 40 oraciones |

`logs/llm_zero_shot.json` y `logs/llm_few_shot.json` reúnen metadatos, llamadas y resultados
de la última ejecución, y son los que lee `evaluacion/evaluar.py`.

### Ejecuciones preliminares

`logs/llm_zero_shot_20261118_150630/` y `logs/llm_few_shot_20261118_153422/` se generaron con
los scripts anteriores (commit `1934c0e`). Se conservan como evidencia, pero **no cumplen el
protocolo final**: no registran el timestamp de cada llamada, el zero-shot no registró su
reintento y, sobre todo, **las dos modalidades no usaron las mismas instrucciones** (el
zero-shot se envió con una redacción distinta del texto). Mientras no existan
`logs/llm_*_shot.json`, la evaluación usa estas carpetas y lo avisa.

## Cómo se evalúa al LLM

`evaluacion/evaluar.py` aplica al LLM la misma metodología que a los demás enfoques:

- **VP/VN/FP/FN, precisión, recall y rechazo correcto**: comparando su decisión con la
  etiqueta esperada (positivo = ACEPTADA).
- **Errores de etiquetado**: mismo criterio que `nlp/` (categoría frente al léxico de la CFG).
  En cada oración aceptada, cada palabra debe aparecer en la `estructura` bajo su terminal
  (`det_m_sg`, `n_f_pl`, …). Se cuentan tres tipos: `categoria_incorrecta`, `sin_categoria`
  (la palabra cuelga directamente de un no terminal) y `palabra_omitida_o_alterada` (no
  aparece o aparece cambiada, p. ej. sin tilde). Se aceptan las dos notaciones que usa el
  modelo: `[det_m_sg El]` y `det_m_sg(El)`.
- **Cumplimiento de la CFG** (`evaluacion/cumplimiento_llm.csv`): reglas citadas en
  `producciones_aplicadas` que no existen en la gramática (las reglas léxicas válidas, como
  `det_m_sg -> el`, no cuentan como error) y si el árbol devuelto es idéntico al del parser
  propio (ignorando ε).

Los resultados están en `evaluacion/tabla_comparativa.md`. El análisis está en
`docs/informe/fase2_llm_resultados.md`.

## Limitaciones

- 40 oraciones: los resultados no se generalizan a otros corpus.
- El servicio externo puede devolver errores 503; quedan registrados en `llamadas.json`.
- Aun con temperatura 0, la salida del modelo no es determinista entre ejecuciones; por eso se
  guarda la evidencia de cada una y nunca se reconstruye.
