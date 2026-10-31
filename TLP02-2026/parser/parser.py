"""Parser LL(1) dirigido por tabla.

Algoritmo (análisis predictivo no recursivo):
    1. La pila empieza con [$, Program].
    2. Se mira el tope de la pila y el token de anticipación (lookahead):
         - terminal  -> debe coincidir con el lookahead; se consume el token.
         - no terminal A -> se consulta TABLE[A][lookahead]; se reemplaza A por el lado
           derecho de esa producción (apilado de derecha a izquierda). Si no hay entrada
           en la tabla, hay un error sintáctico.
         - $ con lookahead $ -> la entrada se acepta.
    3. Mientras se expande, se va construyendo el árbol de análisis sintáctico.

Uso:
    python -m parser.parser archivo.cpp
    python -m parser.parser -c "int x = 3 + 4 * 2;" --tree --ast --trace
    echo "cout << 5;" | python -m parser.parser
"""
from __future__ import annotations

import argparse
import sys

from .grammar import END, EPSILON, PRODUCTIONS, START, TABLE, TERMINALS, format_production
from .lexer import LanguageError, LexError, Token, tokenize
from .tree import Node, build_ast, format_ast

__all__ = ["parse", "accepts", "ParseError", "LexError", "LanguageError"]


class ParseError(LanguageError):
    """La secuencia de tokens no cumple la gramática."""


def _describe(tok: Token) -> str:
    return "el fin de la entrada" if tok.type == END else repr(tok.value)


def _fmt_expected(symbols) -> str:
    order = TERMINALS + [END]
    names = [("fin de la entrada" if s == END else repr(s)) for s in sorted(symbols, key=order.index)]
    return names[0] if len(names) == 1 else "uno de: " + ", ".join(names)


def parse(source: str, trace: list | None = None) -> Node:
    """Analiza `source` y devuelve la raíz del árbol de análisis sintáctico.

    Lanza LexError / ParseError (ambas LanguageError) si la entrada no es válida.
    Si `trace` es una lista, se le agregan las filas (paso, pila, lookahead, acción).
    """
    tokens = tokenize(source)
    pos = 0
    root = Node(START)
    stack: list[Node] = [Node(END), root]   # el tope es el último elemento
    step = 0

    def log(action: str, lookahead: Token) -> None:
        nonlocal step
        if trace is not None:
            step += 1
            snapshot = " ".join(n.symbol for n in reversed(stack)) or "(vacía)"
            trace.append((step, snapshot, lookahead.type, action))

    while stack:
        look = tokens[pos]
        top = stack[-1]
        sym = top.symbol

        if sym == END:
            if look.type == END:
                log("Aceptar", look)
                stack.pop()
                break
            raise ParseError(f"se encontró {_describe(look)} después de terminar el programa",
                             look.line, look.col)

        if sym not in TABLE:                       # terminal
            if look.type != sym:
                raise ParseError(f"se encontró {_describe(look)}, se esperaba {_fmt_expected([sym])}",
                                 look.line, look.col)
            log(f"Emparejar {sym}", look)
            stack.pop()
            top.token = look
            pos += 1
            continue

        # no terminal
        idx = TABLE[sym].get(look.type)
        if idx is None:
            raise ParseError(f"se encontró {_describe(look)}, se esperaba {_fmt_expected(TABLE[sym])}",
                             look.line, look.col)
        log(f"Expandir {format_production(idx)}", look)
        stack.pop()
        rhs = PRODUCTIONS[idx][1]
        if rhs:
            top.children = [Node(s) for s in rhs]
            stack.extend(reversed(top.children))
        else:
            top.children = [Node(EPSILON)]
    return root


def accepts(source: str) -> bool:
    """True si la entrada pertenece al lenguaje; False si genera un error léxico o sintáctico."""
    try:
        parse(source)
    except LanguageError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Línea de comandos
# --------------------------------------------------------------------------- #
def _print_trace(rows: list) -> None:
    w = max((len(r[1]) for r in rows), default=5)
    print(f"{'Paso':>4}  {'Pila (tope a la izquierda)':<{w}}  {'Lookahead':<9}  Acción")
    for step, stack, look, action in rows:
        print(f"{step:>4}  {stack:<{w}}  {look:<9}  {action}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="python -m parser.parser",
                                 description="Parser LL(1) para un subconjunto de C++.")
    ap.add_argument("archivo", nargs="?", help="archivo con el código a analizar (si se omite, stdin)")
    ap.add_argument("-c", "--code", help="analizar este texto en lugar de un archivo")
    ap.add_argument("--tree", action="store_true", help="mostrar el árbol de análisis sintáctico")
    ap.add_argument("--ast", action="store_true", help="mostrar el AST (asociatividad izquierda)")
    ap.add_argument("--trace", action="store_true", help="mostrar la traza pila/lookahead/acción")
    args = ap.parse_args(argv)

    if args.code is not None:
        source = args.code
    elif args.archivo:
        with open(args.archivo, encoding="utf-8") as fh:
            source = fh.read()
    else:
        source = sys.stdin.read()

    rows: list = []
    try:
        root = parse(source, trace=rows if args.trace else None)
    except LanguageError as err:
        print(f"✗ Parser rechaza: {err}")
        if args.trace and rows:
            print(); _print_trace(rows)
        return 1

    print("✓ Parser acepta")
    if args.trace:
        print(); _print_trace(rows)
    if args.tree:
        print(); print(root.pretty())
    if args.ast:
        print(); print(format_ast(build_ast(root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
