"""Árbol de análisis sintáctico (parse tree) y árbol de sintaxis abstracta (AST).

* Node / Node.pretty(): árbol de derivación completo, con ε, tal como lo produce el parser LL(1).
* build_ast(): lo reduce a un AST. La gramática LL(1) usa colas recursivas por la derecha
  (ExprTail, TermTail), así que el árbol de derivación "inclina" las operaciones hacia la
  derecha. build_ast() las pliega hacia la izquierda para respetar la asociatividad izquierda
  de + - * / (por ejemplo 10 - 3 - 2 = (10 - 3) - 2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .grammar import EPSILON
from .lexer import Token


@dataclass
class Node:
    symbol: str
    children: list["Node"] = field(default_factory=list)
    token: Optional[Token] = None   # solo en hojas terminales

    def label(self) -> str:
        if self.token is not None and self.symbol in ("id", "num"):
            return f"{self.symbol}({self.token.value})"
        return self.symbol

    def pretty(self) -> str:
        lines = [self.label()]

        def walk(node: "Node", prefix: str) -> None:
            for i, child in enumerate(node.children):
                last = i == len(node.children) - 1
                lines.append(prefix + ("└── " if last else "├── ") + child.label())
                walk(child, prefix + ("    " if last else "│   "))

        walk(self, "")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# AST
# --------------------------------------------------------------------------- #
# Expresiones: ("num", 20) | ("id", "x") | (op, izquierda, derecha)
# Sentencias:  ("decl", nombre, expr|None) | ("assign", nombre, expr) | ("print", expr)
# Programa:    ("program", [sentencias])
def _is_empty(node: Node) -> bool:
    return not node.children or node.children[0].symbol == EPSILON


def _expr(node: Node):
    if node.symbol in ("Expr", "Term"):
        left = _expr(node.children[0])
        tail = node.children[1]
        while not _is_empty(tail):
            op = tail.children[0].symbol
            right = _expr(tail.children[1])
            left = (op, left, right)
            tail = tail.children[2]
        return left
    if node.symbol == "Factor":
        first = node.children[0]
        if first.symbol == "id":
            return ("id", first.token.value)
        if first.symbol == "num":
            return ("num", int(first.token.value))
        return _expr(node.children[1])          # ( Expr )
    raise ValueError(f"Nodo inesperado: {node.symbol}")


def _stmt(node: Node):
    kind = node.children[0].symbol
    if kind == "int":
        name = node.children[1].token.value
        tail = node.children[2]
        init = _expr(tail.children[1]) if len(tail.children) == 3 else None
        return ("decl", name, init)
    if kind == "id":
        return ("assign", node.children[0].token.value, _expr(node.children[2]))
    return ("print", _expr(node.children[2]))   # cout << Expr ;


def build_ast(root: Node):
    stmts = [_stmt(root.children[0])]
    rest = root.children[1]
    while not _is_empty(rest):
        stmts.append(_stmt(rest.children[0]))
        rest = rest.children[1]
    return ("program", stmts)


def format_expr(e) -> str:
    if e[0] in ("num", "id"):
        return str(e[1])
    return f"({e[0]} {format_expr(e[1])} {format_expr(e[2])})"


def format_ast(ast) -> str:
    lines = []
    for s in ast[1]:
        if s[0] == "decl":
            lines.append(f"decl   {s[1]}" + (f" = {format_expr(s[2])}" if s[2] is not None else ""))
        elif s[0] == "assign":
            lines.append(f"assign {s[1]} = {format_expr(s[2])}")
        else:
            lines.append(f"print  {format_expr(s[1])}")
    return "\n".join(lines)
