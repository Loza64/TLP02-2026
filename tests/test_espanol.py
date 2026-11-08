"""Pruebas de la extensión LL(1) al español.

Ejecutar desde la raíz del proyecto:
    python -m unittest tests.test_espanol -v
"""
import unittest
from pathlib import Path

from parser.ll1 import EPSILON, GrammarError

from espanol.grammar import FIRST, FOLLOW, NONTERMINALS, TABLE, intento_coordinacion
from espanol.lexer import LEXICON, tokenize
from espanol.parser import ParseError, accepts, parse, pretty_tree
from parser.lexer import LexError

ROOT = Path(__file__).resolve().parent.parent


def _oraciones(nombre: str) -> list[str]:
    texto = (ROOT / "examples" / nombre).read_text(encoding="utf-8")
    return [l.strip() for l in texto.splitlines() if l.strip() and not l.startswith("#")]


class GramaticaEspanolTests(unittest.TestCase):
    def test_tabla_sin_conflictos_y_cubre_no_terminales(self):
        self.assertEqual(set(TABLE), set(NONTERMINALS))
        self.assertTrue(all(row for row in TABLE.values()))

    def test_oracion_distingue_singular_y_plural_por_el_determinante(self):
        self.assertIn("det_m_sg", FIRST["Oracion"])
        self.assertIn("det_m_pl", FIRST["Oracion"])
        self.assertIn("det_m_sg", FIRST["Sujeto_sg"])
        self.assertNotIn("det_m_sg", FIRST["Sujeto_pl"])
        self.assertIn("det_m_pl", FIRST["Sujeto_pl"])

    def test_modificadores_nominales_son_anulables(self):
        for nt in ("ModNom_m_sg", "ModNom_f_sg", "ModNom_m_pl", "ModNom_f_pl"):
            self.assertIn(EPSILON, FIRST[nt])

    def test_follow_de_subordinada_relativa_es_el_verbo_principal(self):
        self.assertIn("v_sg", FOLLOW["SubOpt_sg"])
        self.assertIn("v_pl", FOLLOW["SubOpt_pl"])

    def test_coordinacion_provoca_conflicto_ll1(self):
        with self.assertRaises(GrammarError) as ctx:
            intento_coordinacion()
        msg = str(ctx.exception)
        self.assertIn("Conflicto LL(1)", msg)
        self.assertIn("Oracion", msg)
        self.assertTrue("det_m_sg" in msg or "det_f_sg" in msg)


class AceptacionRechazoTests(unittest.TestCase):
    def test_ejemplos_validos_se_aceptan(self):
        casos = _oraciones("espanol_valid.txt")
        self.assertGreaterEqual(len(casos), 8)
        for src in casos:
            with self.subTest(src=src):
                parse(src)

    def test_ejemplos_invalidos_se_rechazan(self):
        casos = _oraciones("espanol_invalid.txt")
        self.assertGreaterEqual(len(casos), 5)
        for src in casos:
            with self.subTest(src=src):
                self.assertFalse(accepts(src))

    def test_fenomenos_del_enunciado(self):
        validos = [
            "el gato negro duerme.",
            "la gata negra corre.",
            "los gatos negros duermen.",
            "la gata muy rápida corre rápidamente en el jardín.",
            "el niño que corre juega en la casa.",
            "el niño observa que la gata duerme.",
        ]
        invalidos = [
            "el gato negra duerme.",
            "los gato negros duermen.",
            "el gato negro duermen.",
            "los gatos que corre duermen.",
            "el niño y la niña duermen.",
        ]
        for src in validos:
            with self.subTest(src=src):
                self.assertTrue(accepts(src))
        for src in invalidos:
            with self.subTest(src=src):
                self.assertFalse(accepts(src))


class ErrorYArbolTests(unittest.TestCase):
    def test_discordancia_de_genero_en_el_adjetivo(self):
        with self.assertRaises(ParseError) as ctx:
            parse("el gato negra duerme.")
        self.assertIn("adj_f_sg", ctx.exception.message)

    def test_palabra_fuera_del_lexico(self):
        with self.assertRaises(LexError):
            tokenize("el elefante negro duerme.")

    def test_arbol_de_una_oracion_simple(self):
        root = parse("el gato negro duerme.")
        self.assertEqual(root.symbol, "Oracion")
        texto = pretty_tree(root)
        self.assertIn("det_m_sg(el)", texto)
        self.assertIn("n_m_sg(gato)", texto)
        self.assertIn("adj_m_sg(negro)", texto)
        self.assertIn("v_sg(duerme)", texto)

    def test_lexicon_cubre_formas_con_tilde_y_sin_ella(self):
        self.assertEqual(LEXICON["jardín"], LEXICON["jardin"])
        self.assertEqual(LEXICON["rápido"], LEXICON["rapido"])


if __name__ == "__main__":
    unittest.main()
