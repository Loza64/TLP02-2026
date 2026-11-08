"""Parser LL(1) del subconjunto de español, dirigido por la misma tabla predictiva.

El algoritmo es el del parser de C++: pila [$, Oracion], un token de
anticipación y consulta de TABLE[A][a]. Mientras expande, construye el
árbol de análisis sintáctico.

Uso:
    python -m espanol.parser -c "el gato negro duerme." --tree --trace
    python -m espanol.parser --demo
    python -m espanol.parser --conflicto
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from parser.lexer import LanguageError, LexError, Token
from parser.ll1 import END, EPSILON
from parser.parser import ParseError
from parser.tree import Node

from .grammar import PRODUCTIONS, START, TABLE, TERMINALS, format_production
from .lexer import tokenize

__all__ = ["parse", "accepts", "ParseError", "LexError", "LanguageError"]

ROOT = Path(__file__).resolve().parent.parent


def _describe(tok: Token) -> str:
    if tok.type == END:
        return "el fin de la entrada"
    if tok.value:
        return f"{tok.value!r} ({tok.type})"
    return repr(tok.type)


def _fmt_expected(symbols) -> str:
    order = TERMINALS + [END]
    extra = [s for s in symbols if s not in order]

    def name(s: str) -> str:
        return "fin de la entrada" if s == END else repr(s)

    names = [name(s) for s in order if s in symbols] + [name(s) for s in sorted(extra)]
    return names[0] if len(names) == 1 else "uno de: " + ", ".join(names)


def parse(source: str, trace: list | None = None) -> Node:
    """Analiza una oración y devuelve la raíz del árbol de derivación."""
    tokens = tokenize(source)
    pos = 0
    root = Node(START)
    stack: list[Node] = [Node(END), root]
    step = 0

    def log(action: str, lookahead: Token) -> None:
        nonlocal step
        if trace is not None:
            step += 1
            snapshot = " ".join(n.symbol for n in reversed(stack)) or "(vacía)"
            look = lookahead.value or lookahead.type
            trace.append((step, snapshot, look, action))

    while stack:
        look = tokens[pos]
        top = stack[-1]
        sym = top.symbol

        if sym == END:
            if look.type == END:
                log("Aceptar", look)
                stack.pop()
                break
            raise ParseError(
                f"se encontró {_describe(look)} después de terminar la oración",
                look.line, look.col,
            )

        if sym not in TABLE:
            if look.type != sym:
                raise ParseError(
                    f"se encontró {_describe(look)}, se esperaba {_fmt_expected([sym])}",
                    look.line, look.col,
                )
            log(f"Emparejar {sym}", look)
            stack.pop()
            top.token = look
            pos += 1
            continue

        idx = TABLE[sym].get(look.type)
        if idx is None:
            raise ParseError(
                f"se encontró {_describe(look)}, se esperaba {_fmt_expected(TABLE[sym])}",
                look.line, look.col,
            )
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
    try:
        parse(source)
    except LanguageError:
        return False
    return True


def pretty_tree(root: Node) -> str:
    """Árbol de derivación; en los terminales se muestra también la palabra."""

    def label(node: Node) -> str:
        if node.token is not None and node.token.value:
            return f"{node.symbol}({node.token.value})"
        return node.symbol

    lines = [label(root)]

    def walk(node: Node, prefix: str) -> None:
        for i, child in enumerate(node.children):
            last = i == len(node.children) - 1
            lines.append(prefix + ("└── " if last else "├── ") + label(child))
            walk(child, prefix + ("    " if last else "│   "))

    walk(root, "")
    return "\n".join(lines)


def _print_trace(rows: list) -> None:
    w = max((len(r[1]) for r in rows), default=5)
    print(f"{'Paso':>4}  {'Pila (tope a la izquierda)':<{w}}  {'Lookahead':<14}  Acción")
    for step, stack, look, action in rows:
        print(f"{step:>4}  {stack:<{w}}  {look:<14}  {action}")


def _casos(nombre: str) -> list[str]:
    texto = (ROOT / "examples" / nombre).read_text(encoding="utf-8")
    return [l.strip() for l in texto.splitlines() if l.strip() and not l.startswith("#")]


def _evaluar(src: str) -> tuple[bool, str]:
    try:
        parse(src)
        return True, ""
    except LanguageError as err:
        return False, str(err)


def run_demo() -> int:
    fallos = 0
    for archivo, esperado in (("espanol_valid.txt", True), ("espanol_invalid.txt", False)):
        print(f"\n== {archivo} (se espera: {'ACEPTAR' if esperado else 'RECHAZAR'}) ==")
        for src in _casos(archivo):
            aceptado, motivo = _evaluar(src)
            ok = aceptado == esperado
            fallos += not ok
            marca = "✓ acepta " if aceptado else "✗ rechaza"
            detalle = f"   -> {motivo}" if motivo else ""
            print(f"  {marca} | {src}{'' if ok else '  ¡RESULTADO INESPERADO!'}{detalle}")
    print(f"\n{'Todos los casos se comportan como se esperaba.' if not fallos else f'{fallos} caso(s) inesperados.'}")
    return 1 if fallos else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        prog="python -m espanol.parser",
        description="Parser LL(1) para un subconjunto controlado del español.",
    )
    ap.add_argument("archivo", nargs="?", help="archivo con la oración (si se omite, stdin)")
    ap.add_argument("-c", "--oracion", help="analizar este texto en lugar de un archivo")
    ap.add_argument("--tree", action="store_true", help="mostrar el árbol de análisis sintáctico")
    ap.add_argument("--trace", action="store_true", help="mostrar la traza pila/lookahead/acción")
    ap.add_argument("--demo", action="store_true", help="correr los ejemplos de examples/espanol_*.txt")
    ap.add_argument("--conflicto", action="store_true",
                    help="mostrar el conflicto LL(1) del intento de coordinación")
    args = ap.parse_args(argv)

    if args.conflicto:
        from .grammar import explicar_conflicto
        print(explicar_conflicto())
        return 0
    if args.demo:
        return run_demo()

    if args.oracion is not None:
        source = args.oracion
    elif args.archivo:
        source = Path(args.archivo).read_text(encoding="utf-8")
    else:
        source = sys.stdin.read()

    rows: list = []
    try:
        root = parse(source, trace=rows if args.trace else None)
    except LanguageError as err:
        print(f"✗ Parser rechaza: {err}")
        if args.trace and rows:
            print()
            _print_trace(rows)
        return 1

    print("✓ Parser acepta")
    if args.trace:
        print()
        _print_trace(rows)
    if args.tree:
        print()
        print(pretty_tree(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
