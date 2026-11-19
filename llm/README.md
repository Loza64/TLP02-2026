# Evaluación con modelos de lenguaje (Gemini)

## Descripción

Este módulo incorpora una evaluación complementaria del parser LL(1) del español mediante un modelo de lenguaje de Google Gemini.

El objetivo es comprobar si un modelo de lenguaje puede clasificar las oraciones del corpus según su pertenencia al lenguaje definido por nuestra gramática libre de contexto (CFG).

Se implementaron dos estrategias de prompting:

- **Zero-Shot:** el modelo recibe las instrucciones, las producciones de la gramática y el léxico, sin ejemplos resueltos.
- **Few-Shot:** utiliza las mismas instrucciones, gramática y léxico, pero incorpora cuatro ejemplos resueltos para orientar la clasificación.

Ambas estrategias se ejecutan sobre las mismas 40 oraciones de `corpus/corpus_pruebas.csv`.

**Importante:** la clasificación no busca determinar si una oración es gramaticalmente correcta en todo el español, sino si pertenece al lenguaje reconocido por la gramática implementada.

## Requisitos

- Python 3.10 o superior.
- Una clave de API de Google Gemini.
- Dependencias:
  - `google-genai==3.5.0`
  - `python-dotenv==1.2.4`

Estas dependencias están incluidas en `requirements.txt`.

## Configuración

Desde la raíz del proyecto, instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

Crear un archivo `.env` en la raíz del repositorio y agregar la clave de API:

```env
GEMINI_API_KEY=TU_CLAVE_DE_API
```

El archivo `.env` está incluido en `.gitignore` para evitar publicar información sensible.

## Modelo y configuración experimental

| Parámetro | Valor |
|---|---|
| Proveedor | Google Gemini |
| Modelo | `gemini-3.5-flash-lite` |
| Temperatura | `0` |
| Formato de respuesta | `application/json` |
| Corpus | 40 oraciones |
| Tamaño de lote | 5 oraciones |
| Total de lotes | 8 |
| Estrategias | Zero-Shot y Few-Shot |
| Ejemplos Few-Shot | 4 |

La temperatura 0 se utiliza para reducir la variabilidad de las respuestas. Cada lote se envía mediante la API y se valida que los resultados contengan los identificadores esperados, decisiones válidas y las oraciones originales sin modificaciones.


## Ejecución

Los experimentos y su evaluación se ejecutan de forma independiente.

### 1. Zero-Shot

Ejecutar el experimento:

```bash
python -m llm.ejecutar_zero_shot
```

Si algún lote falla por problemas temporales de conexión, recuperar los resultados:

```bash
python -m llm.recuperar_lote
```

Evaluar los resultados:

```bash
python -m llm.evaluar_llm zero-shot
```

### 2. Few-Shot

Ejecutar el experimento:

```bash
python -m llm.ejecutar_few_shot
```

Si algún lote falla por problemas temporales de conexión, recuperar los resultados:

```bash
python -m llm.recuperar_few_shot
```

Evaluar los resultados:

```bash
python -m llm.evaluar_llm few-shot
```

### Archivos generados

Cada ejecución almacena sus resultados en una carpeta independiente dentro de `logs/`.

Entre los archivos generados se encuentran:

- `resultados.json`: clasificación obtenida para las 40 oraciones.
- Archivos de prompts y respuestas originales de cada lote.
- `metadatos.json`: información del experimento y su ejecución.
- `metricas.json`: métricas generales y resultados por nivel.
- `detalle_evaluacion.csv`: clasificación individual de cada oración.

El evaluador utiliza el experimento más reciente de la modalidad indicada. Al ejecutarlo nuevamente, actualiza `metricas.json` y `detalle_evaluacion.csv` de esa carpeta, sin modificar los resultados originales.


## Prompts

Los prompts se construyen dinámicamente a partir de las producciones de `espanol/grammar.py` y las categorías léxicas de `espanol/lexer.py`.

El archivo `prompts.py` contiene:

- Las instrucciones para determinar si una oración pertenece al lenguaje.
- La gramática y el léxico utilizados por el parser.
- Cuatro ejemplos para la estrategia Few-Shot.

Los ejemplos Few-Shot son independientes de las 40 oraciones del corpus, evitando utilizar casos de evaluación como ejemplos de referencia.

## Resultados experimentales

Ambas estrategias obtuvieron los mismos resultados sobre el corpus de 40 oraciones.

| Métrica | Zero-Shot | Few-Shot |
|---|---:|---:|
| Verdaderos positivos (VP) | 28 | 28 |
| Verdaderos negativos (VN) | 12 | 12 |
| Falsos positivos (FP) | 0 | 0 |
| Falsos negativos (FN) | 0 | 0 |
| Exactitud | 100 % | 100 % |
| Precisión | 100 % | 100 % |
| Recall | 100 % | 100 % |
| Especificidad | 100 % | 100 % |
| F1-score | 100 % | 100 % |

### Resultados por nivel

| Nivel | Total | Zero-Shot | Few-Shot |
|---|---:|---:|---:|
| Nivel 1 | 12 | 12/12 | 12/12 |
| Nivel 2 | 16 | 16/16 | 16/16 |
| Nivel 3 | 12 | 12/12 | 12/12 |

Los resultados muestran que ambas estrategias clasificaron correctamente las 40 oraciones. En este corpus no se observó una mejora medible al incorporar ejemplos mediante Few-Shot.

## Registros y evidencia experimental

Cada ejecución genera una carpeta independiente dentro de `logs/`.

Las carpetas correspondientes a los experimentos realizados son:

- `logs/llm_zero_shot_20261118_150630/`
- `logs/llm_few_shot_20261118_153422/`

Cada carpeta contiene, según la estrategia y el proceso de recuperación:

| Archivo | Descripción |
|---|---|
| `prompt_lote_XX.txt` | Prompt enviado al modelo para cada lote. |
| `respuesta_bruta_lote_XX.txt` | Respuesta original recibida de la API. |
| `resultados_lote_XX.json` | Resultados validados de cada lote. |
| `resultados.json` | Resultados consolidados de las 40 oraciones. |
| `metadatos.json` | Información de la ejecución, modelo, parámetros, tiempos, errores y hash del corpus. |
| `recuperacion.json` | Registro de intentos de recuperación, cuando está disponible. |
| `metricas.json` | Métricas calculadas por el evaluador, cuando se genera. |
| `detalle_evaluacion.csv` | Comparación entre la clasificación esperada y la obtenida, cuando se genera. |

Los metadatos incluyen información como el modelo utilizado, la temperatura, el tamaño del corpus, la cantidad de lotes, las marcas de tiempo, la duración, la versión de Python, el sistema operativo y el hash SHA-256 del corpus.

### Recuperación de solicitudes

Durante las ejecuciones se presentaron errores temporales de disponibilidad del servicio Gemini (HTTP 503). Los lotes afectados se recuperaron mediante los scripts correspondientes.

Las dos ejecuciones finalizaron con:

- 40 de 40 resultados obtenidos.
- Ningún lote pendiente.
- Resultados consolidados y disponibles para evaluación.

Los errores iniciales se conservaron en los metadatos como evidencia de las incidencias durante la ejecución.

## Limitaciones

- La evaluación utiliza un corpus de 40 oraciones, por lo que los resultados no garantizan el mismo rendimiento en otros conjuntos de datos.
- El modelo clasifica según la gramática y el léxico proporcionados; no realiza una evaluación general de la corrección gramatical del español.
- Los resultados pueden depender del modelo, sus instrucciones y la disponibilidad del servicio externo.
- La igualdad de resultados entre Zero-Shot y Few-Shot no demuestra que ambas estrategias tengan el mismo rendimiento en otros corpus.

## Estructura del módulo

```text

llm/
├── prompts.py
├── probar_gemini.py
├── probar_prompt.py
├── probar_few_shot.py
├── ejecutar_zero_shot.py
├── ejecutar_few_shot.py
├── evaluar_llm.py
├── recuperar_lote.py
├── recuperar_few_shot.py
└── README.md
```

Los registros experimentales se almacenan en `logs/`, fuera de esta carpeta.

