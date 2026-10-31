"""Gramática del subconjunto de C++ y cálculo de FIRST, FOLLOW y tabla predictiva LL(1).

Las producciones son la fuente única de verdad: el parser no tiene reglas
"escritas a mano"; consulta la tabla que se construye aquí.

Uso:
    python -m parser.grammar               # imprime producciones, FIRST, FOLLOW y tabla
    python -m parser.grammar --markdown    # lo mismo en Markdown (para el informe)
"""
from __future__ import annotations

import sys

EPSILON = "ε"   # secuencia vacía
END = "$"       # fin de la entrada
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

NONTERMINALS: list[str] = list(dict.fromkeys(lhs for lhs, _ in PRODUCTIONS))
TERMINALS: list[str] = ["int", "id", "num", "cout", "<<", "=", ";", "+", "-", "*", "/", "(", ")"]
_NT = set(NONTERMINALS)


class GrammarError(Exception):
    """La gramática no es LL(1) (conflicto en la tabla predictiva)."""


def _check_symbols() -> None:
    for lhs, rhs in PRODUCTIONS:
        for sym in rhs:
            if sym not in _NT and sym not in TERMINALS:
                raise GrammarError(f"Símbolo desconocido {sym!r} en {lhs}")


def first_of_sequence(seq: list[str], first: dict[str, set[str]]) -> set[str]:
    """FIRST de una cadena de símbolos (contiene ε si toda la cadena es anulable)."""
    result: set[str] = set()
    for sym in seq:
        if sym in _NT:
            result |= first[sym] - {EPSILON}
            if EPSILON not in first[sym]:
                return result
        else:
            result.add(sym)
            return result
    result.add(EPSILON)
    return result


def compute_first() -> dict[str, set[str]]:
    first: dict[str, set[str]] = {nt: set() for nt in NONTERMINALS}
    changed = True
    while changed:
        changed = False
        for lhs, rhs in PRODUCTIONS:
            new = first_of_sequence(rhs, first)
            if not new <= first[lhs]:
                first[lhs] |= new
                changed = True
    return first


def compute_follow(first: dict[str, set[str]]) -> dict[str, set[str]]:
    follow: dict[str, set[str]] = {nt: set() for nt in NONTERMINALS}
    follow[START].add(END)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in PRODUCTIONS:
            for i, sym in enumerate(rhs):
                if sym not in _NT:
                    continue
                rest = first_of_sequence(rhs[i + 1:], first)
                new = rest - {EPSILON}
                if EPSILON in rest:
                    new |= follow[lhs]
                if not new <= follow[sym]:
                    follow[sym] |= new
                    changed = True
    return follow


def build_table(first: dict[str, set[str]], follow: dict[str, set[str]]) -> dict[str, dict[str, int]]:
    """Tabla predictiva M[No terminal][terminal] = índice de la producción en PRODUCTIONS.

    Lanza GrammarError si dos producciones compiten por la misma celda (no es LL(1)).
    """
    table: dict[str, dict[str, int]] = {nt: {} for nt in NONTERMINALS}
    for idx, (lhs, rhs) in enumerate(PRODUCTIONS):
        f = first_of_sequence(rhs, first)
        lookaheads = f - {EPSILON}
        if EPSILON in f:
            lookaheads |= follow[lhs]
        for t in lookaheads:
            if t in table[lhs]:
                raise GrammarError(
                    f"Conflicto LL(1) en M[{lhs}, {t}]: producciones "
                    f"{table[lhs][t] + 1} y {idx + 1}"
                )
            table[lhs][t] = idx
    return table


_check_symbols()
FIRST = compute_first()
FOLLOW = compute_follow(FIRST)
TABLE = build_table(FIRST, FOLLOW)


# --------------------------------------------------------------------------- #
# Presentación (para el informe y la demo)
# --------------------------------------------------------------------------- #
def format_production(idx: int) -> str:
    lhs, rhs = PRODUCTIONS[idx]
    return f"{lhs} → {' '.join(rhs) if rhs else EPSILON}"


def _ordered(symbols: set[str]) -> list[str]:
    order = TERMINALS + [END, EPSILON]
    return sorted(symbols, key=order.index)


def _fmt_set(symbols: set[str]) -> str:
    return "{ " + ", ".join(_ordered(symbols)) + " }"


def report(markdown: bool = False) -> str:
    out: list[str] = []
    cols = TERMINALS + [END]
    if markdown:
        out += ["### Producciones", ""]
        out += [f"{i + 1}. `{format_production(i)}`" for i in range(len(PRODUCTIONS))]
        out += ["", "### Conjuntos FIRST y FOLLOW", "",
                "| No terminal | FIRST | FOLLOW |", "|---|---|---|"]
        out += [f"| `{nt}` | `{_fmt_set(FIRST[nt])}` | `{_fmt_set(FOLLOW[nt])}` |"
                for nt in NONTERMINALS]
        out += ["", "### Tabla predictiva LL(1)", "",
                "Cada celda contiene el número de la producción a aplicar; vacío = error sintáctico.", "",
                "| | " + " | ".join(f"`{c}`" for c in cols) + " |",
                "|---|" + "---|" * len(cols)]
        for nt in NONTERMINALS:
            cells = [str(TABLE[nt][c] + 1) if c in TABLE[nt] else "" for c in cols]
            out.append(f"| **{nt}** | " + " | ".join(cells) + " |")
    else:
        out += ["PRODUCCIONES"]
        out += [f"  {i + 1:>2}. {format_production(i)}" for i in range(len(PRODUCTIONS))]
        out += ["", "FIRST / FOLLOW"]
        for nt in NONTERMINALS:
            out.append(f"  {nt:<9} FIRST={_fmt_set(FIRST[nt]):<22} FOLLOW={_fmt_set(FOLLOW[nt])}")
        out += ["", "TABLA PREDICTIVA (número de producción; · = error)"]
        out.append("  " + f"{'':<9}" + "".join(f"{c:>5}" for c in cols))
        for nt in NONTERMINALS:
            out.append("  " + f"{nt:<9}" + "".join(
                f"{(TABLE[nt][c] + 1) if c in TABLE[nt] else '·':>5}" for c in cols))
    return "\n".join(out)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    md = "--markdown" in sys.argv
    print(report(markdown=md))
    if not md:
        print("\nLa gramática es LL(1): la tabla se construyó sin conflictos.")


if __name__ == "__main__":
    main()
