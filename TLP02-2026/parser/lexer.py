"""Analizador léxico: convierte el texto fuente en una lista de tokens.

Tokens producidos (coinciden con los terminales de la gramática):
    int, cout          palabras reservadas
    id                 identificador  [A-Za-z_][A-Za-z0-9_]*
    num                número entero  [0-9]+
    <<  =  ;  +  -  *  /  (  )
    $                  fin de la entrada

Los comentarios de línea (// ...) y los espacios se ignoran.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .grammar import END

KEYWORDS = {"int", "cout"}


class LanguageError(Exception):
    """Error léxico o sintáctico: la entrada no pertenece al lenguaje."""

    def __init__(self, message: str, line: int, col: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def __str__(self) -> str:
        return f"Error (línea {self.line}, columna {self.col}): {self.message}"


class LexError(LanguageError):
    """Carácter o secuencia que no forma ningún token."""


@dataclass(frozen=True)
class Token:
    type: str    # terminal de la gramática ("id", "num", "int", "+", "$", ...)
    value: str   # texto original
    line: int
    col: int


_TOKEN_RE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in [
        ("COMMENT", r"//[^\n]*"),
        ("NL",      r"\n"),
        ("WS",      r"[ \t\r]+"),
        ("BADNUM",  r"[0-9]+[A-Za-z_][A-Za-z0-9_]*"),
        ("NUM",     r"[0-9]+"),
        ("ID",      r"[A-Za-z_][A-Za-z0-9_]*"),
        ("SHL",     r"<<"),
        ("OP",      r"[=;+\-*/()]"),
        ("BAD",     r"."),
    ])
)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    line, line_start = 1, 0
    for m in _TOKEN_RE.finditer(source):
        kind, text = m.lastgroup, m.group()
        col = m.start() - line_start + 1
        if kind == "NL":
            line += 1
            line_start = m.end()
        elif kind in ("WS", "COMMENT"):
            continue
        elif kind == "ID":
            tokens.append(Token(text if text in KEYWORDS else "id", text, line, col))
        elif kind == "NUM":
            tokens.append(Token("num", text, line, col))
        elif kind in ("SHL", "OP"):
            tokens.append(Token(text, text, line, col))
        elif kind == "BADNUM":
            raise LexError(f"token mal formado {text!r} (un número no puede unirse a letras)", line, col)
        else:  # BAD
            hint = " (¿quiso escribir '<<'?)" if text == "<" else ""
            raise LexError(f"carácter no reconocido {text!r}{hint}", line, col)
    tokens.append(Token(END, "", line, len(source) - line_start + 1))
    return tokens
