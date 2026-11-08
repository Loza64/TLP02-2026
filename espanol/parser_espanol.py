"""Punto de entrada de la extensión al español (demo de la Sección 5).

Construye la tabla LL(1) con el motor compartido de ``parser.ll1``,
acepta oraciones que respetan concordancia, modificadores y subordinadas,
y rechaza las que las violan.

Uso (desde la raíz del proyecto):
    python -m espanol.parser_espanol
    python -m espanol.parser_espanol -c "el gato negro duerme." --tree
    python -m espanol.parser_espanol --demo
    python -m espanol.parser_espanol --conflicto
"""
from __future__ import annotations

import sys

from .grammar import GRAMMAR, PRODUCTIONS, TABLE
from .parser import main


def _banner() -> None:
    celdas = sum(len(row) for row in TABLE.values())
    print(
        f"Tabla LL(1) construida sin conflictos "
        f"({len(PRODUCTIONS)} producciones, {celdas} celdas activas, "
        f"símbolo inicial {GRAMMAR.start})."
    )
    print()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if not argv:
        _banner()
        raise SystemExit(main(["--demo"]))
    raise SystemExit(main(argv))
