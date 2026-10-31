"""Gramática del subconjunto de C++ y cálculo de FIRST, FOLLOW y tabla predictiva LL(1).

Las producciones son la fuente única de verdad: el parser no tiene reglas
"escritas a mano"; consulta la tabla que se construye aquí.

Uso:
    python -m parser.grammar               # imprime producciones, FIRST, FOLLOW y tabla
    python -m parser.grammar --markdown    # lo mismo en Markdown (para el informe)
"""
from __future__ import annotations

import sys

from .ll1 import END, EPSILON, GrammarError, LL1Grammar

START = "Program"

# (lado izquierdo, lado derecho). Un lado derecho vacío [] representa ε.
PRODUCTIONS: list[tuple[str, list[str]]] = [
    ("Program",  ["Stmt", "StmtList"]),
    ("StmtList", ["Stmt", "StmtList"]),
    ("StmtList", []),
    ("Stmt",     ["int", "id", "DeclTail"]),
    ("Stmt",     ["id", "=", "Expr", ";"]),
    ("Stmt",     ["cout", "<<", "Expr", ";"]),
    ("DeclTail", [";"]),
    ("DeclTail", ["=", "Expr", ";"]),
    ("Expr",     ["Term", "ExprTail"]),
    ("ExprTail", ["+", "Term", "ExprTail"]),
    ("ExprTail", ["-", "Term", "ExprTail"]),
    ("ExprTail", []),
    ("Term",     ["Factor", "TermTail"]),
    ("TermTail", ["*", "Factor", "TermTail"]),
    ("TermTail", ["/", "Factor", "TermTail"]),
    ("TermTail", []),
    ("Factor",   ["id"]),
    ("Factor",   ["num"]),
    ("Factor",   ["(", "Expr", ")"]),
]

TERMINALS: list[str] = ["int", "id", "num", "cout", "<<", "=", ";", "+", "-", "*", "/", "(", ")"]

GRAMMAR = LL1Grammar(PRODUCTIONS, TERMINALS, START)
NONTERMINALS: list[str] = GRAMMAR.nonterminals
_NT = set(NONTERMINALS)
FIRST = GRAMMAR.first
FOLLOW = GRAMMAR.follow
TABLE = GRAMMAR.table


def first_of_sequence(seq: list[str], first: dict[str, set[str]]) -> set[str]:
    """FIRST de una cadena de símbolos (contiene ε si toda la cadena es anulable)."""
    return GRAMMAR.first_of_sequence(seq, first)


def compute_first() -> dict[str, set[str]]:
    return GRAMMAR.compute_first()


def compute_follow(first: dict[str, set[str]]) -> dict[str, set[str]]:
    return GRAMMAR.compute_follow(first)


def build_table(first: dict[str, set[str]], follow: dict[str, set[str]]) -> dict[str, dict[str, int]]:
    """Tabla predictiva M[No terminal][terminal] = índice de la producción en PRODUCTIONS.

    Lanza GrammarError si dos producciones compiten por la misma celda (no es LL(1)).
    """
    return GRAMMAR.build_table(first, follow)


def format_production(idx: int) -> str:
    return GRAMMAR.format_production(idx)


def report(markdown: bool = False) -> str:
    return GRAMMAR.report(markdown=markdown)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    md = "--markdown" in sys.argv
    print(report(markdown=md))
    if not md:
        print("\nLa gramática es LL(1): la tabla se construyó sin conflictos.")


if __name__ == "__main__":
    main()
