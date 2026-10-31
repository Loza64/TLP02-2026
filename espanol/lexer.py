"""Analizador léxico del subconjunto de español.

Cada palabra del vocabulario se traduce a un terminal de la gramática
(``det_m_sg``, ``n_f_pl``, ``v_sg``, ...). El punto es un token aparte.
Los espacios se ignoran; cualquier palabra fuera del léxico es error léxico.
"""
from __future__ import annotations

import re

from parser.grammar import END
from parser.lexer import LexError, Token

LEXICON: dict[str, str] = {
    # Determinantes
    "el": "det_m_sg", "un": "det_m_sg",
    "la": "det_f_sg", "una": "det_f_sg",
    "los": "det_m_pl", "unos": "det_m_pl",
    "las": "det_f_pl", "unas": "det_f_pl",
    # Sustantivos
    "gato": "n_m_sg", "perro": "n_m_sg", "niño": "n_m_sg",
    "jardín": "n_m_sg", "jardin": "n_m_sg", "parque": "n_m_sg",
    "gata": "n_f_sg", "perra": "n_f_sg", "niña": "n_f_sg", "casa": "n_f_sg",
    "gatos": "n_m_pl", "perros": "n_m_pl", "niños": "n_m_pl",
    "gatas": "n_f_pl", "perras": "n_f_pl", "niñas": "n_f_pl",
    # Adjetivos flexionados
    "negro": "adj_m_sg", "rápido": "adj_m_sg", "rapido": "adj_m_sg",
    "negra": "adj_f_sg", "rápida": "adj_f_sg", "rapida": "adj_f_sg",
    "negros": "adj_m_pl", "rápidos": "adj_m_pl", "rapidos": "adj_m_pl",
    "negras": "adj_f_pl", "rápidas": "adj_f_pl", "rapidas": "adj_f_pl",
    # Adjetivos invariables en género (grande / grandes)
    "grande": "adj_inv_sg",
    "grandes": "adj_inv_pl",
    # Verbos
    "duerme": "v_sg", "corre": "v_sg", "juega": "v_sg", "observa": "v_sg",
    "duermen": "v_pl", "corren": "v_pl", "juegan": "v_pl", "observan": "v_pl",
    # Modificadores y nexos
    "muy": "adv_intens",
    "rápidamente": "adv_modo", "rapidamente": "adv_modo",
    "tranquilamente": "adv_modo",
    "en": "prep", "con": "prep", "bajo": "prep",
    "que": "que",
    "y": "conj",
}

_TOKEN_RE = re.compile(
    r"(?P<NL>\n)"
    r"|(?P<WS>[ \t\r]+)"
    r"|(?P<WORD>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)"
    r"|(?P<DOT>\.)"
    r"|(?P<BAD>.)"
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
        elif kind == "WS":
            continue
        elif kind == "DOT":
            tokens.append(Token(".", text, line, col))
        elif kind == "WORD":
            key = text.casefold()
            tipo = LEXICON.get(key)
            if tipo is None:
                raise LexError(f"palabra fuera del léxico {text!r}", line, col)
            tokens.append(Token(tipo, text, line, col))
        else:
            raise LexError(f"carácter no reconocido {text!r}", line, col)
    tokens.append(Token(END, "", line, max(1, len(source) - line_start + 1)))
    return tokens
