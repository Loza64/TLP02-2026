"""Pruebas de la Fase 2: corpus, log del parser propio y visualización de árboles.

Ejecutar desde la raíz del proyecto:
    python -m unittest tests.test_corpus -v
"""
import json
import tempfile
import unittest
from pathlib import Path

from espanol.ejecutar_corpus import (
    CORPUS_POR_DEFECTO, analizar, arbol_parentesis, ejecutar, escribir, leer_corpus,
)
from espanol.grammar import explicar_conflicto
from espanol.visualizacion_arboles import generar


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.log = ejecutar(CORPUS_POR_DEFECTO)
        cls.por_id = {r["id"]: r for r in cls.log["resultados"]}

    def test_corpus_tiene_40_oraciones_en_tres_niveles(self):
        filas = leer_corpus(CORPUS_POR_DEFECTO)
        self.assertEqual(len(filas), 40)
        conteo = {n: sum(f["nivel"] == n for f in filas) for n in (1, 2, 3)}
        self.assertEqual(conteo, {1: 12, 2: 16, 3: 12})

    def test_el_parser_coincide_con_las_etiquetas_esperadas(self):
        no_coinciden = [r["id"] for r in self.log["resultados"] if not r["coincide"]]
        self.assertEqual(no_coinciden, [])

    def test_aceptadas_tienen_arbol_y_rechazadas_motivo(self):
        for r in self.log["resultados"]:
            with self.subTest(id=r["id"]):
                if r["obtenido"] == "ACEPTADA":
                    self.assertIsNotNone(r["arbol"])
                    self.assertTrue(r["arbol_parentesis"].startswith("(Oracion "))
                    self.assertIsNone(r["motivo"])
                else:
                    self.assertIsNone(r["arbol"])
                    self.assertTrue(r["motivo"]["descripcion"])

    def test_motivos_de_rechazo_clasificados(self):
        esperado = {
            29: "discordancia_genero",
            30: "coordinacion_no_contemplada",
            31: "discordancia_numero",
            32: "discordancia_numero",
            33: "discordancia_numero",
            34: "discordancia_genero",
            35: "palabra_fuera_del_lexico",
            36: "falta_determinante",
            37: "estructura_incompleta",
            38: "estructura_incompleta",
            39: "coordinacion_no_contemplada",
            40: "discordancia_genero_y_numero",
        }
        for ident, categoria in esperado.items():
            with self.subTest(id=ident):
                self.assertEqual(self.por_id[ident]["motivo"]["categoria"], categoria)

    def test_regla_de_concordancia_sujeto_verbo(self):
        motivo = self.por_id[32]["motivo"]
        self.assertEqual(motivo["regla"], "Oracion → Sujeto_sg SV_sg .")
        motivo = self.por_id[33]["motivo"]
        self.assertEqual(motivo["regla"], "SubOpt_pl → que SV_pl")
        self.assertIn("relativa", motivo["descripcion"])

    def test_derivacion_empieza_en_el_simbolo_inicial(self):
        r = self.por_id[1]
        self.assertTrue(r["derivacion"][0].startswith("Oracion → "))
        self.assertEqual(r["traza"][-1]["accion"], "Aceptar")

    def test_metricas_del_resumen(self):
        m = self.log["resumen"]["metricas"]
        self.assertEqual((m["VP"], m["VN"], m["FP"], m["FN"]), (28, 12, 0, 0))
        self.assertEqual(m["precision"], 1.0)

    def test_arbol_en_parentesis(self):
        arbol = analizar("el gato negro duerme.")["arbol"]
        self.assertEqual(
            arbol_parentesis(arbol),
            "(Oracion (Sujeto_sg (SN_m_sg (det_m_sg el) (n_m_sg gato) "
            "(ModNom_m_sg (Adj_m_sg (adj_m_sg negro))))) (SV_sg (v_sg duerme)) (. .))",
        )

    def test_conflicto_ll1_se_reporta_siempre_en_la_misma_celda(self):
        self.assertIn("M[Oracion, det_m_sg]", explicar_conflicto())

    def test_archivos_de_salida_y_arboles(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp)
            rutas = escribir(self.log, salida)
            self.assertTrue(all(r.exists() for r in rutas))
            datos = json.loads((salida / "parser_propio.json").read_text(encoding="utf-8"))
            self.assertEqual(len(datos["resultados"]), 40)

            generados = generar(salida / "parser_propio.json", salida / "arboles")
            svgs = [r for r in generados if r.suffix == ".svg"]
            self.assertEqual(len(svgs), self.log["resumen"]["aceptadas"])
            self.assertTrue(svgs[0].read_text(encoding="utf-8").startswith("<svg"))
            self.assertTrue((salida / "arboles" / "index.html").exists())
            self.assertTrue((salida / "arboles" / "arboles_forest.tex").exists())


if __name__ == "__main__":
    unittest.main()
