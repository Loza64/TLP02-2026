# 4. Implementación y pruebas del parser

## 4.1. Diseño e implementación

El parser está escrito en Python (≥ 3.10, solo biblioteca estándar) y se organiza en cuatro módulos dentro de `parser/`:

- **`lexer.py`**: convierte el texto en tokens (`int`, `cout`, `id`, `num`, `<<`, `=`, `;`, `+`, `-`, `*`, `/`, `(`, `)` y `$`). Reconoce `<<` como un único token, distingue palabras reservadas de identificadores (`integer` es un `id`, no `int`), ignora espacios y comentarios `//`, y registra línea y columna de cada token. Los caracteres no reconocidos generan un error léxico.
- **`grammar.py`**: contiene las 19 producciones de la gramática y calcula automáticamente los conjuntos FIRST y FOLLOW y la tabla predictiva LL(1). Si dos producciones compitieran por una misma celda lanzaría un error, de modo que construir la tabla sin conflictos comprueba que la gramática es LL(1). Los conjuntos obtenidos coinciden con los del diseño de la gramática y se verifican en las pruebas.
- **`parser.py`**: parser predictivo no recursivo dirigido por tabla. Usa una pila que inicia con `$ Program`. En cada paso compara el tope con el token de anticipación: si es un terminal lo empareja y avanza; si es un no terminal consulta `TABLE[A][token]` y lo reemplaza por el lado derecho de la producción elegida; si la celda está vacía informa un error sintáctico. La entrada se acepta cuando `$` coincide con el fin de la entrada.
- **`tree.py`**: construye el árbol de análisis sintáctico mientras se expanden las producciones y ofrece una conversión a AST.

**Manejo de errores.** Se detiene en el primer error e informa línea, columna, el token encontrado y los tokens que se esperaban en ese punto (los que tienen entrada en la tabla para el no terminal actual). Ejemplo: `int edad = ;` → *se encontró ';', se esperaba uno de: 'id', 'num', '('*. El modo `--trace` muestra la pila, el token de anticipación y la acción de cada paso.

**Uso.** `python -m parser.parser -c "int x = 3 + 4 * 2;" --tree --ast --trace`; los pasos completos están en el `README.md`.

## 4.2. Árbol de análisis sintáctico

Árbol generado para `cout << 3 + 4;`:

```
Program
├── Stmt
│   ├── cout
│   ├── <<
│   ├── Expr
│   │   ├── Term
│   │   │   ├── Factor
│   │   │   │   └── num(3)
│   │   │   └── TermTail
│   │   │       └── ε
│   │   └── ExprTail
│   │       ├── +
│   │       ├── Term
│   │       │   ├── Factor
│   │       │   │   └── num(4)
│   │       │   └── TermTail
│   │       │       └── ε
│   │       └── ExprTail
│   │           └── ε
│   └── ;
└── StmtList
    └── ε
```

La suma queda en `ExprTail` (nivel de expresión) y cada operando cuelga de un `Term`, lo que refleja la separación entre `Expr` y `Term` que establece la precedencia. Las producciones vacías aparecen como `ε` cuando el token de anticipación pertenece al FOLLOW (`TermTail` ante `+` y `;`, `ExprTail` ante `;`, `StmtList` ante `$`).

Como las colas `ExprTail` y `TermTail` son recursivas por la derecha (necesario para evitar la recursión por la izquierda), el árbol de derivación inclina las operaciones hacia la derecha. Por eso `tree.py` también genera un AST que las pliega hacia la izquierda y conserva la asociatividad izquierda: `total - 1 - 2` se interpreta como `(total - 1) - 2`. AST de un programa de dos instrucciones:

```
decl   total = (+ 3 (* 4 2))
assign total = (- (- total 1) 2)
```

## 4.3. Pruebas del lenguaje formal

| Entrada | Resultado esperado | Resultado obtenido |
|---|---|---|
| `int edad;` | Aceptar | Aceptó ✓ |
| `int edad = 20;` | Aceptar | Aceptó ✓ |
| `int total = 3 + 4 * 2;` | Aceptar | Aceptó ✓ |
| `total = (3 + 4) * 2;` | Aceptar | Aceptó ✓ |
| `cout << total;` | Aceptar | Aceptó ✓ |
| `cout << 3 + 4;` | Aceptar | Aceptó ✓ |
| `int edad = ;` | Rechazar | Rechazó ✓<br>(línea 1, columna 12) se encontró ';', se esperaba uno de: 'id', 'num', '(' |
| `total = 5` | Rechazar | Rechazó ✓<br>(línea 1, columna 10) se encontró el fin de la entrada, se esperaba uno de: ';', '+', '-', '*', '/', ')' |
| `total = 3 + * 2;` | Rechazar | Rechazó ✓<br>(línea 1, columna 13) se encontró '*', se esperaba uno de: 'id', 'num', '(' |
| `cout << (3 + 4;` | Rechazar | Rechazó ✓<br>(línea 1, columna 15) se encontró ';', se esperaba ')' |

Las pruebas automáticas (`python -m unittest discover -s tests -t . -v`, 19 pruebas) comprueban que: (1) los FIRST/FOLLOW calculados coinciden con los del diseño y la tabla no tiene conflictos; (2) los 10 archivos de `tests/valid/` son aceptados y los 17 de `tests/invalid/` son rechazados; (3) los errores se reportan en la posición correcta; (4) el lexer trata bien `<<`, palabras reservadas y caracteres inválidos; y (5) el AST respeta precedencia y asociatividad izquierda. Los mismos ejemplos se pueden ver en pantalla con `python run_examples.py` (acepta ✓ / rechaza ✗). Las entradas fuera del subconjunto (por ejemplo `x = -5;` o `cout << a << b;`) se rechazan por diseño y están documentadas en `tests/invalid/`.
