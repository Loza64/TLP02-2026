"""Gramática LL(1) de un subconjunto controlado del español.

Reutiliza el motor de ``parser.ll1`` (los mismos algoritmos FIRST, FOLLOW y
tabla predictiva que el subconjunto de C++). La concordancia se codifica
multiplicando no terminales por género y número, porque una CFG no tiene
atributos (genero=M, numero=SG).

Uso:
    python -m espanol.grammar
    python -m espanol.grammar --markdown
    python -m espanol.grammar --conflicto
"""
from __future__ import annotations

import sys

from parser.ll1 import END, EPSILON, GrammarError, LL1Grammar

START = "Oracion"

# (lado izquierdo, lado derecho). Un lado derecho vacío [] representa ε.
PRODUCTIONS: list[tuple[str, list[str]]] = [
    # Oración: el número del sujeto decide el del verbo desde el primer determinante.
    ("Oracion", ["Sujeto_sg", "SV_sg", "."]),
    ("Oracion", ["Sujeto_pl", "SV_pl", "."]),

    ("Sujeto_sg", ["SN_m_sg", "SubOpt_sg"]),
    ("Sujeto_sg", ["SN_f_sg", "SubOpt_sg"]),
    ("Sujeto_pl", ["SN_m_pl", "SubOpt_pl"]),
    ("Sujeto_pl", ["SN_f_pl", "SubOpt_pl"]),

    # SN con concordancia estricta det–sustantivo–adjetivo.
    ("SN_m_sg", ["det_m_sg", "n_m_sg", "ModNom_m_sg"]),
    ("SN_f_sg", ["det_f_sg", "n_f_sg", "ModNom_f_sg"]),
    ("SN_m_pl", ["det_m_pl", "n_m_pl", "ModNom_m_pl"]),
    ("SN_f_pl", ["det_f_pl", "n_f_pl", "ModNom_f_pl"]),

    # Modificadores nominales. Adj_* agrupa el adjetivo flexionado y el invariable
    # (grande/grandes) para no crear un conflicto FIRST/FIRST tras "muy".
    ("ModNom_m_sg", ["Adj_m_sg"]),
    ("ModNom_m_sg", ["adv_intens", "Adj_m_sg"]),
    ("ModNom_m_sg", []),
    ("Adj_m_sg", ["adj_m_sg"]),
    ("Adj_m_sg", ["adj_inv_sg"]),

    ("ModNom_f_sg", ["Adj_f_sg"]),
    ("ModNom_f_sg", ["adv_intens", "Adj_f_sg"]),
    ("ModNom_f_sg", []),
    ("Adj_f_sg", ["adj_f_sg"]),
    ("Adj_f_sg", ["adj_inv_sg"]),

    ("ModNom_m_pl", ["Adj_m_pl"]),
    ("ModNom_m_pl", ["adv_intens", "Adj_m_pl"]),
    ("ModNom_m_pl", []),
    ("Adj_m_pl", ["adj_m_pl"]),
    ("Adj_m_pl", ["adj_inv_pl"]),

    ("ModNom_f_pl", ["Adj_f_pl"]),
    ("ModNom_f_pl", ["adv_intens", "Adj_f_pl"]),
    ("ModNom_f_pl", []),
    ("Adj_f_pl", ["adj_f_pl"]),
    ("Adj_f_pl", ["adj_inv_pl"]),

    # Relativa de sujeto: "el niño que corre". El verbo subordinado hereda el número.
    ("SubOpt_sg", ["que", "SV_sg"]),
    ("SubOpt_sg", []),
    ("SubOpt_pl", ["que", "SV_pl"]),
    ("SubOpt_pl", []),

    # Completiva ("observa que la gata duerme") o modificadores del verbo.
    ("SV_sg", ["v_sg", "RestoSV"]),
    ("SV_pl", ["v_pl", "RestoSV"]),
    ("RestoSV", ["que", "Clausula"]),
    ("RestoSV", ["AdvOpt", "SPOpt"]),

    ("Clausula", ["Sujeto_sg", "SV_sg"]),
    ("Clausula", ["Sujeto_pl", "SV_pl"]),

    ("AdvOpt", ["adv_modo"]),
    ("AdvOpt", []),
    ("SPOpt", ["prep", "SN_Prep"]),
    ("SPOpt", []),
    ("SN_Prep", ["SN_m_sg"]),
    ("SN_Prep", ["SN_f_sg"]),
    ("SN_Prep", ["SN_m_pl"]),
    ("SN_Prep", ["SN_f_pl"]),
]

TERMINALS: list[str] = [
    "det_m_sg", "det_f_sg", "det_m_pl", "det_f_pl",
    "n_m_sg", "n_f_sg", "n_m_pl", "n_f_pl",
    "adj_m_sg", "adj_f_sg", "adj_m_pl", "adj_f_pl",
    "adj_inv_sg", "adj_inv_pl",
    "v_sg", "v_pl",
    "adv_intens", "adv_modo",
    "prep", "que", "conj", ".",
]

GRAMMAR = LL1Grammar(PRODUCTIONS, TERMINALS, START)
NONTERMINALS = GRAMMAR.nonterminals
FIRST = GRAMMAR.first
FOLLOW = GRAMMAR.follow
TABLE = GRAMMAR.table


# Intento que rompe LL(1): un sujeto coordinado puede empezar por el mismo
# determinante que un sujeto singular ("el niño y la niña" vs. "el niño").
COORD_PRODUCTIONS: list[tuple[str, list[str]]] = PRODUCTIONS + [
    ("Sujeto_pl", ["SN_m_sg", "conj", "SN_Coord"]),
    ("Sujeto_pl", ["SN_f_sg", "conj", "SN_Coord"]),
    ("SN_Coord", ["SN_m_sg"]),
    ("SN_Coord", ["SN_f_sg"]),
    ("SN_Coord", ["SN_m_pl"]),
    ("SN_Coord", ["SN_f_pl"]),
]


def intento_coordinacion() -> LL1Grammar:
    """Construye la gramática con coordinación. Debe lanzar GrammarError."""
    return LL1Grammar(COORD_PRODUCTIONS, TERMINALS, START)


def format_production(idx: int) -> str:
    return GRAMMAR.format_production(idx)


def report(markdown: bool = False) -> str:
    return GRAMMAR.report(markdown=markdown, compact=True)


def explicar_conflicto() -> str:
    try:
        intento_coordinacion()
    except GrammarError as err:
        return (
            "Intento de extensión: sujeto coordinado\n"
            "  Sujeto_pl → SN_m_sg conj SN_Coord   (el niño y la niña)\n"
            "  Sujeto_pl → SN_f_sg conj SN_Coord   (la niña y el niño)\n\n"
            f"  Resultado: {err}\n\n"
            "  FIRST(Sujeto_sg) y FIRST(Sujeto_pl) pasan a compartir det_m_sg y det_f_sg.\n"
            "  Oracion debe decidir entre SV_sg y SV_pl con un solo token, y no puede.\n"
            "  Esto es un conflicto LL(1), no una imposibilidad de las CFG: una gramática\n"
            "  libre de contexto sí puede generar esa coordinación, pero no de forma\n"
            "  predictiva con un único símbolo de anticipación."
        )
    return "No se detectó el conflicto esperado."


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--conflicto" in sys.argv:
        print(explicar_conflicto())
        return
    print(report(markdown="--markdown" in sys.argv))
    if "--markdown" not in sys.argv:
        print(f"\nLa gramática es LL(1): {len(PRODUCTIONS)} producciones, "
              f"tabla sin conflictos ({sum(len(row) for row in TABLE.values())} celdas).")


if __name__ == "__main__":
    main()
