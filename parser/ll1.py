"""Motor LL(1) reutilizable: FIRST, FOLLOW y tabla predictiva.

Cualquier gramática del proyecto (el subconjunto de C++ o la extensión al
español) se describe como una lista de producciones y se entrega a
``LL1Grammar``. El parser no escribe reglas a mano: consulta la tabla que
se construye aquí.

Un lado derecho vacío ``[]`` representa ε.
"""
from __future__ import annotations

EPSILON = "ε"
END = "$"


class GrammarError(Exception):
    """La gramática no es LL(1) (conflicto en la tabla predictiva)."""


class LL1Grammar:
    """Gramática libre de contexto con conjuntos FIRST/FOLLOW y tabla LL(1)."""

    def __init__(
        self,
        productions: list[tuple[str, list[str]]],
        terminals: list[str],
        start: str,
    ) -> None:
        self.productions = productions
        self.terminals = list(terminals)
        self.start = start
        self.nonterminals = list(dict.fromkeys(lhs for lhs, _ in productions))
        self._nt = set(self.nonterminals)
        self._check_symbols()
        self.first = self.compute_first()
        self.follow = self.compute_follow()
        self.table = self.build_table()

    def _check_symbols(self) -> None:
        for lhs, rhs in self.productions:
            for sym in rhs:
                if sym not in self._nt and sym not in self.terminals:
                    raise GrammarError(f"Símbolo desconocido {sym!r} en {lhs}")

    def first_of_sequence(self, seq: list[str], first: dict[str, set[str]]) -> set[str]:
        """FIRST de una cadena de símbolos (contiene ε si toda la cadena es anulable)."""
        result: set[str] = set()
        for sym in seq:
            if sym in self._nt:
                result |= first[sym] - {EPSILON}
                if EPSILON not in first[sym]:
                    return result
            else:
                result.add(sym)
                return result
        result.add(EPSILON)
        return result

    def compute_first(self) -> dict[str, set[str]]:
        first: dict[str, set[str]] = {nt: set() for nt in self.nonterminals}
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.productions:
                new = self.first_of_sequence(rhs, first)
                if not new <= first[lhs]:
                    first[lhs] |= new
                    changed = True
        return first

    def compute_follow(self, first: dict[str, set[str]] | None = None) -> dict[str, set[str]]:
        first = self.first if first is None else first
        follow: dict[str, set[str]] = {nt: set() for nt in self.nonterminals}
        follow[self.start].add(END)
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.productions:
                for i, sym in enumerate(rhs):
                    if sym not in self._nt:
                        continue
                    rest = self.first_of_sequence(rhs[i + 1:], first)
                    new = rest - {EPSILON}
                    if EPSILON in rest:
                        new |= follow[lhs]
                    if not new <= follow[sym]:
                        follow[sym] |= new
                        changed = True
        return follow

    def build_table(
        self,
        first: dict[str, set[str]] | None = None,
        follow: dict[str, set[str]] | None = None,
    ) -> dict[str, dict[str, int]]:
        """Tabla predictiva M[No terminal][terminal] = índice de la producción.

        Lanza GrammarError si dos producciones compiten por la misma celda.
        """
        first = self.first if first is None else first
        follow = self.follow if follow is None else follow
        table: dict[str, dict[str, int]] = {nt: {} for nt in self.nonterminals}
        for idx, (lhs, rhs) in enumerate(self.productions):
            f = self.first_of_sequence(rhs, first)
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

    def format_production(self, idx: int) -> str:
        lhs, rhs = self.productions[idx]
        return f"{lhs} → {' '.join(rhs) if rhs else EPSILON}"

    def _ordered(self, symbols: set[str]) -> list[str]:
        order = self.terminals + [END, EPSILON]
        extra = [s for s in symbols if s not in order]
        return [s for s in order if s in symbols] + sorted(extra)

    def _fmt_set(self, symbols: set[str]) -> str:
        return "{ " + ", ".join(self._ordered(symbols)) + " }"

    def report(self, markdown: bool = False, compact: bool = False) -> str:
        out: list[str] = []
        cols = self.terminals + [END]
        wide = compact or len(self.terminals) > 16
        if markdown:
            out += ["### Producciones", ""]
            out += [f"{i + 1}. `{self.format_production(i)}`" for i in range(len(self.productions))]
            out += ["", "### Conjuntos FIRST y FOLLOW", "",
                    "| No terminal | FIRST | FOLLOW |", "|---|---|---|"]
            out += [
                f"| `{nt}` | `{self._fmt_set(self.first[nt])}` | `{self._fmt_set(self.follow[nt])}` |"
                for nt in self.nonterminals
            ]
            out += ["", "### Tabla predictiva LL(1)", ""]
            if wide:
                out += ["Cada fila es una celda activa `M[A, a] = producción`.", ""]
                out += ["| No terminal | Anticipación | Producción |", "|---|---|---|"]
                for nt in self.nonterminals:
                    for t in self._ordered(set(self.table[nt])):
                        out.append(
                            f"| `{nt}` | `{t}` | {self.table[nt][t] + 1}. `{self.format_production(self.table[nt][t])}` |"
                        )
            else:
                out += [
                    "Cada celda contiene el número de la producción a aplicar; vacío = error sintáctico.",
                    "",
                    "| | " + " | ".join(f"`{c}`" for c in cols) + " |",
                    "|---|" + "---|" * len(cols),
                ]
                for nt in self.nonterminals:
                    cells = [str(self.table[nt][c] + 1) if c in self.table[nt] else "" for c in cols]
                    out.append(f"| **{nt}** | " + " | ".join(cells) + " |")
        else:
            out += ["PRODUCCIONES"]
            width = max(2, len(str(len(self.productions))))
            out += [f"  {i + 1:>{width}}. {self.format_production(i)}" for i in range(len(self.productions))]
            nt_w = max((len(nt) for nt in self.nonterminals), default=8)
            out += ["", "FIRST / FOLLOW"]
            for nt in self.nonterminals:
                out.append(
                    f"  {nt:<{nt_w}}  FIRST={self._fmt_set(self.first[nt])}  "
                    f"FOLLOW={self._fmt_set(self.follow[nt])}"
                )
            if wide:
                out += ["", "TABLA PREDICTIVA (solo celdas activas)"]
                for nt in self.nonterminals:
                    for t in self._ordered(set(self.table[nt])):
                        out.append(
                            f"  M[{nt}, {t}] = {self.table[nt][t] + 1}. "
                            f"{self.format_production(self.table[nt][t])}"
                        )
            else:
                out += ["", "TABLA PREDICTIVA (número de producción; · = error)"]
                out.append("  " + f"{'':<{nt_w}}" + "".join(f"{c:>5}" for c in cols))
                for nt in self.nonterminals:
                    out.append("  " + f"{nt:<{nt_w}}" + "".join(
                        f"{(self.table[nt][c] + 1) if c in self.table[nt] else '·':>5}"
                        for c in cols
                    ))
        return "\n".join(out)
