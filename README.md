# Proyecto TLP02-2026 — Fases 1 y 2

## Descripción

Proyecto de Teoría de Lenguajes de Programación (UCA): *Gramáticas formales y lenguaje natural:
experimentando los límites de la jerarquía de Chomsky*.

Esta fase implementa un **parser LL(1) dirigido por tabla** en Python para un subconjunto de C++
(declaraciones `int`, asignaciones, expresiones aritméticas con paréntesis y `cout <<`), y después
intenta extender la gramática al español, documenta las limitaciones de las gramáticas libres de
contexto y compara los resultados con una herramienta de NLP.

El parser **solo comprueba sintaxis**: no verifica que las variables estén declaradas ni los tipos
(eso es análisis semántico).

## Requisitos

- Python **3.10 o superior**. En macOS con Homebrew, preferir `python3.12` (el `python3` del
  sistema suele ser 3.9 y choca con el nombre del paquete `parser/`).
- Las pruebas usan `unittest` (incluido en Python). El parser de C++ y la extensión al español
  no requieren dependencias externas.
- spaCy y Transformers solo hacen falta para la comparación NLP (`nlp/`); `google-genai` y
  `python-dotenv` para el LLM (`llm/`); `matplotlib` y `numpy` para la evaluación (`evaluacion/`).

## Instalación

```bash
git clone <url-del-repositorio>
cd TLP02-2026

# Entorno virtual (recomendado en Mac/Linux/Windows)
python3.12 -m venv .venv          # o: python3 -m venv .venv  /  py -3.12 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

python -m pip install -r requirements.txt
python -m spacy download es_core_news_sm   # solo para la parte NLP
```

Con el entorno activado, todos los comandos siguientes usan `python`.

## Ejecución

Todos los comandos se ejecutan **desde la raíz del proyecto** y con `-m`
(no ejecutar `python parser/parser.py` ni `python espanol/parser_espanol.py` directamente).

### Parser de C++

```bash
# Analizar un archivo
python -m parser.parser tests/valid/07_programa_completo.cpp

# Analizar texto, con árbol, AST y traza
python -m parser.parser -c "int total = 3 + 4 * 2;" --tree --ast --trace

# Entrada inválida
python -m parser.parser -c "total = 5"

# Producciones, FIRST, FOLLOW y tabla predictiva (--markdown para el informe)
python -m parser.grammar
```

Salida esperada:

```
$ python -m parser.parser -c "int edad = 20;"
✓ Parser acepta

$ python -m parser.parser -c "total = 5"
✗ Parser rechaza: Error (línea 1, columna 10): se encontró el fin de la entrada, se esperaba uno de: ';', '+', '-', '*', '/', ')'
```

El código de salida es `0` si el parser acepta y `1` si rechaza.

### Extensión al español

```bash
# Demo: oraciones válidas (✓) e inválidas (✗)
python -m espanol.parser_espanol
python -m espanol --demo

# Conflicto LL(1) al intentar coordinación ("el niño y la niña")
python -m espanol --conflicto

# Oración a mano, con árbol o rechazo
python -m espanol -c "el gato negro duerme." --tree
python -m espanol -c "el gato negra duerme."
python -m espanol -c "el niño y la niña duermen."

# Producciones, FIRST, FOLLOW y tabla
python -m espanol.grammar
```

### Demo conjunta (C++ + español)

```bash
python run_examples.py
```

### Comparación NLP (spaCy y Transformers)

```bash
python -m nlp.spacy_comparison       # -> logs/spacy.json
python -m nlp.segunda_herramienta    # -> logs/segunda_herramienta.json
```

Detalles de instalación, metodología y esquema de los logs en `nlp/README.md`.
La visualización de dependencias de la Fase 2 queda en `nlp/results/arboles_spacy.html`
(la de la Fase 1, en `nlp/results/arboles_dependencias_nlp.html`).
Para abrirla:

```bash
# macOS
open nlp/results/arboles_dependencias_nlp.html

# Linux
xdg-open nlp/results/arboles_dependencias_nlp.html

# Windows
start nlp/results/arboles_dependencias_nlp.html
```

# Fase 2: parser propio con el corpus de prueba

Ejecuta las 40 oraciones de `corpus/corpus_pruebas.csv` con el parser LL(1) del español y
guarda la evidencia en `logs/`. No requiere dependencias externas.

```bash
# 1. Ejecutar el corpus y guardar el log
python -m espanol.ejecutar_corpus

# 2. Dibujar los árboles de las oraciones aceptadas (lee logs/parser_propio.json)
python -m espanol.visualizacion_arboles
python -m espanol.visualizacion_arboles --con-epsilon        # árbol completo, con ε

# Un solo árbol, para una figura del informe
python -m espanol.visualizacion_arboles --oracion "el gato negro duerme." --salida figuras
```

Archivos generados:

| Archivo | Contenido |
|---|---|
| `logs/parser_propio.json` | Log completo: metadatos (fecha, versión de Python, commit, hash del corpus, tamaño de la gramática), resumen con VP/VN/FP/FN y, por oración: tokens, derivación, traza de la pila, árbol y motivo de rechazo. |
| `logs/parser_propio.txt` | El mismo log en formato legible. |
| `logs/parser_propio_resultados.csv` | Una fila por oración (`id, nivel, oracion, esperado, obtenido, coincide, motivo_categoria, regla, arbol`), para el script de evaluación. |
| `logs/arboles/arbol_XX.svg` | Un árbol por oración aceptada. |
| `logs/arboles/index.html` | Galería con todos los árboles. |
| `logs/arboles/arboles_forest.tex` | Los árboles para LaTeX (`\usepackage{forest}`). |

Criterio: **ACEPTADA** si el parser construye el árbol completo; **RECHAZADA** si falla el
lexer o el análisis predictivo. El motivo de cada rechazo se clasifica en
`palabra_fuera_del_lexico`, `discordancia_genero`, `discordancia_numero`,
`discordancia_genero_y_numero`, `coordinacion_no_contemplada`, `estructura_incompleta`,
`falta_determinante` o `estructura_no_contemplada`, junto con la regla de la gramática que lo
decide.

# Fase 2: LLM mediante API (Gemini)

El LLM recibe la gramática completa (`espanol/grammar.py`) y el léxico (`espanol/lexer.py`)
y decide si cada oración pertenece al lenguaje. Hay dos modalidades con **las mismas
instrucciones**; few-shot solo añade 4 ejemplos resueltos (2 aceptados, 2 rechazados, ninguno
del corpus).

**Configuración** (no subir claves al repositorio):

```bash
cp .env.example .env      # Windows: copy .env.example .env
# editar .env y colocar GEMINI_API_KEY
```

**Ejecución:**

```bash
python -m llm.ejecutar_llm ambos       # o: zero-shot / few-shot
```

| Elemento | Ubicación |
|---|---|
| Prompt zero-shot exacto | `llm/prompt_zero_shot.txt` |
| Prompt few-shot exacto | `llm/prompt_few_shot.txt` |
| Código | `llm/ejecutar_llm.py`, `llm/prompts.py` |
| Log consolidado (lo lee la evaluación) | `logs/llm_zero_shot.json`, `logs/llm_few_shot.json` |
| Evidencia original de cada ejecución | `logs/llm_<modo>_<AAAAMMDD_HHMMSS>/` |

En los `.txt`, el marcador `<<ORACIONES_A_EVALUAR>>` se sustituye por las 5 oraciones de
cada lote; el prompt exacto de cada llamada queda en `prompt_lote_XX.txt`. Si se modifica
la gramática, regenerar los `.txt` con `python -m llm.prompts` (el ejecutor se niega a
correr si no coinciden con el código).

Cada llamada a la API (incluidos los reintentos por errores 503) queda en `llamadas.json`
con timestamp de inicio y fin, estado, error, versión del modelo que respondió y tokens
usados. Modelo, parámetros (`temperature=0`, `response_mime_type=application/json`, lotes
de 5), versiones y hash del corpus quedan en `metadatos.json`. Detalles en
[`llm/README.md`](llm/README.md).

# Fase 2: evaluación, tablas y gráficas

```bash
python -m evaluacion.evaluar
```

Lee los cinco logs (`logs/parser_propio.json`, `logs/spacy.json`,
`logs/segunda_herramienta.json`, `logs/llm_zero_shot.json`, `logs/llm_few_shot.json`),
compara cada decisión con la etiqueta de `corpus/corpus_pruebas.csv` y **regenera** todas
las tablas y gráficas. No hay resultados escritos a mano: con los mismos logs produce
exactamente los mismos archivos.

| Archivo | Contenido |
|---|---|
| `evaluacion/resultados.csv` | Tabla comparativa: precisión, recall, rechazo correcto, VP, VN, FP, FN, errores de etiquetado y exactitud por enfoque |
| `evaluacion/tabla_comparativa.md` | Las mismas tablas en Markdown, para el informe |
| `evaluacion/resultados_por_nivel.csv` | VP/VN/FP/FN y errores por nivel de complejidad |
| `evaluacion/resultados_por_oracion.csv` | Decisión y clasificación de los 5 enfoques en cada oración |
| `evaluacion/cumplimiento_llm.csv` | Reglas citadas por el LLM que no existen en la CFG, errores de etiquetado y si su árbol coincide con el del parser |
| `evaluacion/resultados.json` | Todo lo anterior |
| `evaluacion/graficas/metricas_comparativas.png` | Barras agrupadas: precisión, recall y rechazo correcto |
| `evaluacion/graficas/errores_comparativos.png` | FP, FN y errores de etiquetado |
| `evaluacion/graficas/errores_por_nivel.png` | Errores de clasificación por nivel |

Fórmulas (positivo = ACEPTADA): Precisión = VP/(VP+FP), Recall = VP/(VP+FN),
Rechazo correcto = VN/(VN+FP).

## Versiones utilizadas

| Componente | Versión |
|---|---|
| Python | 3.15.2 (parser, NLP, evaluación) |
| spaCy / modelo | 3.8.18 / `es_core_news_sm` 3.8.0 |
| Transformers / torch | 5.23.0 / 2.15.0 (CPU) |
| google-genai / python-dotenv | 3.5.0 / 1.2.4 |
| Modelo LLM | `gemini-3.5-flash-lite`, temperatura 0 |
| matplotlib / numpy | 3.11.2 / 2.5.5 |

## Pruebas

```bash
# C++ + español + corpus + LLM y evaluación de la Fase 2 (57 pruebas)
python -m unittest discover -s tests -t . -v

# Solo la extensión al español
python -m unittest tests.test_espanol -v

# Solo el corpus, el log y los árboles de la Fase 2
python -m unittest tests.test_corpus -v
```

Importante: el `-t .` hace que Python use el paquete local `parser/` y no el módulo
homónimo de la biblioteca estándar (presente en Python 3.9).

Las pruebas comprueban: FIRST/FOLLOW y ausencia de conflictos LL(1); que cada archivo de
`tests/valid/` se acepte y cada archivo de `tests/invalid/` se rechace; posiciones de los errores;
comportamiento del lexer; precedencia/asociatividad en el AST; y la extensión al español
(`tests/test_espanol.py`: oraciones válidas, discordancias y el conflicto LL(1) de la
coordinación) y, en `tests/test_corpus.py`, que las 40 oraciones del corpus coincidan con su
etiqueta, que los motivos de rechazo se clasifiquen bien y que se generen el log y los
árboles; y, en `tests/test_llm_evaluacion.py`, las fórmulas de las métricas, que los
prompts `.txt` coincidan con el código y compartan instrucciones, la validación de las
respuestas del LLM y que la evaluación reproduzca los resúmenes de cada log.
Resultado esperado: `OK` (57 pruebas).

Para agregar un caso de C++, basta con crear un archivo `.cpp` en `tests/valid/` o
`tests/invalid/`. Para el español, se añade una línea en `examples/espanol_valid.txt` o
`examples/espanol_invalid.txt`.

## Estructura

```
TLP02-2026/
├── README.md
├── requirements.txt
├── run_examples.py        # demo: acepta ✓ / rechaza ✗ sobre examples/
├── parser/
│   ├── lexer.py           # texto -> tokens (con línea y columna)
│   ├── ll1.py             # motor reutilizable: FIRST, FOLLOW, tabla LL(1)
│   ├── grammar.py         # producciones del subconjunto de C++
│   ├── parser.py          # parser predictivo no recursivo + línea de comandos
│   └── tree.py            # árbol de análisis sintáctico y AST
├── espanol/               # extensión al español
│   ├── grammar.py         # producciones con concordancia y subordinadas
│   ├── lexer.py           # léxico cerrado del español
│   ├── parser.py          # mismo algoritmo LL(1), otro símbolo inicial
│   ├── parser_espanol.py  # demo de aceptación / rechazo
│   ├── ejecutar_corpus.py       # Fase 2: corpus -> logs/parser_propio.*
│   └── visualizacion_arboles.py # Fase 2: árboles SVG / HTML / LaTeX
├── corpus/
│   ├── corpus_pruebas.csv       # 40 oraciones con etiqueta esperada
│   └── criterios_diseno_corpus.md
├── .env.example           # plantilla sin credenciales (copiar a .env)
├── llm/                   # Fase 2: LLM mediante API (Gemini)
│   ├── prompt_zero_shot.txt    # prompt zero-shot exacto
│   ├── prompt_few_shot.txt     # prompt few-shot exacto
│   ├── prompts.py              # genera los prompts desde la gramática y el léxico
│   ├── ejecutar_llm.py         # ejecuta zero-shot / few-shot y guarda la evidencia
│   └── README.md
├── evaluacion/            # Fase 2: métricas, tablas y gráficas de los 5 enfoques
│   ├── evaluar.py
│   ├── resultados.csv, tabla_comparativa.md, resultados_*.csv, cumplimiento_llm.csv
│   └── graficas/
├── logs/
│   ├── parser_propio.json       # log completo del parser propio
│   ├── parser_propio.txt
│   ├── parser_propio_resultados.csv
│   ├── spacy.json               # log de spaCy (nlp/spacy_comparison.py)
│   ├── segunda_herramienta.json # log de Transformers (nlp/segunda_herramienta.py)
│   ├── llm_zero_shot.json       # log consolidado del LLM (llm/ejecutar_llm.py)
│   ├── llm_few_shot.json
│   ├── llm_<modo>_<fecha>/      # prompts, respuestas brutas y llamadas de cada ejecución
│   └── arboles/                 # árboles de las oraciones aceptadas
├── nlp/                   # Fase 2: herramientas modernas de NLP (ver nlp/README.md)
│   ├── spacy_comparison.py     # spaCy + es_core_news_sm -> logs/spacy.json
│   ├── segunda_herramienta.py  # Transformers (BETO) -> logs/segunda_herramienta.json
│   ├── criterios.py            # metodología común de aceptación/rechazo (C1–C4)
│   ├── comun.py                # corpus, métricas y escritura de logs
│   └── results/                # árboles de dependencias HTML (displaCy)
├── tests/
│   ├── test_parser.py
│   ├── test_espanol.py
│   ├── test_corpus.py
│   ├── test_llm_evaluacion.py  # prompts, validación de respuestas y evaluación
│   ├── valid/             # programas que deben aceptarse
│   └── invalid/           # programas que deben rechazarse
├── examples/              # un caso por línea, para la demo
└── docs/
    ├── informe/           # secciones del informe (seccion4, seccion5, tablas LL(1))
    └── presentacion/
```

## Gramática

```
Program  → Stmt StmtList
StmtList → Stmt StmtList | ε
Stmt     → int id DeclTail | id = Expr ; | cout << Expr ;
DeclTail → ; | = Expr ;
Expr     → Term ExprTail
ExprTail → + Term ExprTail | - Term ExprTail | ε
Term     → Factor TermTail
TermTail → * Factor TermTail | / Factor TermTail | ε
Factor   → id | num | ( Expr )
```

Fuera del subconjunto (se rechazan por diseño): operadores unarios (`x = -5;`), encadenado de
`cout << a << b;`, cadenas de texto, `endl`, declaraciones múltiples (`int a, b;`), condicionales,
ciclos, funciones.

## Integrantes

- González Rivas, Javier Alejandro — 00088022
- Hernández López, Jennifer Arlette — 00162622
- Hernández Martínez, Wilson David — 00135222
- Loza Castillo, Carlos Roberto — 00002522

Catedrático: Jaime Roberto Clímaco Navarrete
