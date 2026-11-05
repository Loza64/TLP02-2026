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

- Python **3.10 o superior** (el parser solo usa la biblioteca estándar).
- Las pruebas usan `unittest`, incluido en Python. No hace falta instalar nada para el parser.

## Instalación

```bash
git clone <url-del-repositorio>
cd TLP02-2026
# (opcional) entorno virtual
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                         # no instala nada para el parser
```

## Ejecución

Todos los comandos se ejecutan **desde la raíz del proyecto** y con `-m`
(no ejecutar `python parser/parser.py` directamente):

```bash
# Analizar un archivo
python -m parser.parser tests/valid/07_programa_completo.cpp

# Analizar texto directamente, mostrando árbol, AST y traza paso a paso
python -m parser.parser -c "int total = 3 + 4 * 2;" --tree --ast --trace

# Desde la entrada estándar
echo "cout << (3 + 4) * 2;" | python -m parser.parser

# Ver producciones, FIRST, FOLLOW y tabla predictiva (añadir --markdown para el informe)
python -m parser.grammar

# Demo: ejecuta examples/valid_examples.txt y examples/invalid_examples.txt
python run_examples.py

# Extensión al español (misma tabla LL(1), otro léxico y otras producciones)
python -m espanol.parser_espanol
python -m espanol.parser -c "el gato negro duerme." --tree --trace
python -m espanol.parser -c "el gato negra duerme."
python -m espanol.parser --conflicto
python -m espanol.grammar
```

Salida esperada para una entrada válida y una inválida:

```
$ python -m parser.parser -c "int edad = 20;"
✓ Parser acepta

$ python -m parser.parser -c "total = 5"
✗ Parser rechaza: Error (línea 1, columna 10): se encontró el fin de la entrada, se esperaba uno de: ';', '+', '-', '*', '/', ')'
```

El código de salida es `0` si el parser acepta y `1` si rechaza.

## Pruebas

```bash
python -m unittest discover -s tests -t . -v
```

Las pruebas comprueban: FIRST/FOLLOW y ausencia de conflictos LL(1); que cada archivo de
`tests/valid/` se acepte y cada archivo de `tests/invalid/` se rechace; posiciones de los errores;
comportamiento del lexer; precedencia/asociatividad en el AST; y la extensión al español
(`tests/test_espanol.py`: oraciones válidas, discordancias y el conflicto LL(1) de la
coordinación). Resultado esperado: `OK` (31 pruebas).

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
├── espanol/               # extensión al español (Integrante 3)
│   ├── grammar.py         # producciones con concordancia y subordinadas
│   ├── lexer.py           # léxico cerrado del español
│   ├── parser.py          # mismo algoritmo LL(1), otro símbolo inicial
│   └── parser_espanol.py  # demo de aceptación / rechazo
├── nlp/                   # comparación con spaCy (Integrante 4)
│   ├── nlp_comparison.py  # script principal de procesamiento y análisis
│   └── results/           # visualizaciones HTML generadas por spaCy
├── tests/
│   ├── test_parser.py
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
