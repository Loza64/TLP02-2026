# Proyecto TLP02-2026 — Fase 1

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
- spaCy solo hace falta para la comparación NLP (`nlp/`).

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

## Pruebas

```bash
# C++ + español + corpus de la Fase 2 (41 pruebas)
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
árboles. Resultado esperado: `OK` (41 pruebas).

Para agregar un caso de C++, basta con crear un archivo `.cpp` en `tests/valid/` o
`tests/invalid/`. Para el español, se añade una línea en `examples/espanol_valid.txt` o
`examples/espanol_invalid.txt`.

### Evaluación con modelos de lenguaje (Gemini)

Se incorporó una evaluación adicional utilizando Gemini 3.5 Flash-Lite mediante dos estrategias de prompting:

- **Zero-Shot:** clasificación utilizando las instrucciones, la gramática y el léxico, sin ejemplos resueltos.
- **Few-Shot:** clasificación utilizando las mismas instrucciones, gramática y léxico, incorporando cuatro ejemplos resueltos.

Ambas modalidades se evaluaron sobre las 40 oraciones del corpus y obtuvieron un **100 % de exactitud**, con 28 verdaderos positivos, 12 verdaderos negativos y ningún error de clasificación.

Los scripts, requisitos de configuración, metodología, instrucciones de ejecución y resultados detallados se encuentran en [`llm/README.md`](llm/README.md).

Los registros completos de ejecución se encuentran en:

- `logs/llm_zero_shot_20261118_150630/`
- `logs/llm_few_shot_20261118_153422/`

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
├── llm/                    # Fase 2: evaluación con Gemini (Zero-Shot y Few-Shot)
│   ├── ejecutar_zero_shot.py   # Ejecución del experimento Zero-Shot
│   ├── ejecutar_few_shot.py    # Ejecución del experimento Few-Shot
│   ├── evaluar_llm.py          # Evaluación de métricas para ambas modalidades
│   ├── recuperar_lote.py       # Recuperación de lotes Zero-Shot
│   ├── recuperar_few_shot.py   # Recuperación de lotes Few-Shot
│   ├── prompts.py              # Construcción de prompts y ejemplos Few-Shot
│   ├── probar_gemini.py        # Prueba de conexión con Gemini
│   └── README.md               # Documentación de la evaluación con LLM
├── logs/
│   ├── parser_propio.json       # log completo del parser propio
│   ├── parser_propio.txt
│   ├── parser_propio_resultados.csv
│   ├── spacy.json               # log de spaCy (nlp/spacy_comparison.py)
│   ├── segunda_herramienta.json # log de Transformers (nlp/segunda_herramienta.py)
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
