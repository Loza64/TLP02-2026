"""Pruebas del ejecutor LLM y del script de evaluacion (Fase 2)."""

import unittest

from evaluacion import evaluar as ev
from llm import ejecutar_llm, prompts


class TestMetricas(unittest.TestCase):
    def test_clasificar(self):
        self.assertEqual(ev.clasificar("ACEPTADA", "ACEPTADA"), "VP")
        self.assertEqual(ev.clasificar("RECHAZADA", "RECHAZADA"), "VN")
        self.assertEqual(ev.clasificar("RECHAZADA", "ACEPTADA"), "FP")
        self.assertEqual(ev.clasificar("ACEPTADA", "RECHAZADA"), "FN")
        with self.assertRaises(ValueError):
            ev.clasificar("ACEPTADA", "QUIZA")

    def test_formulas_del_documento(self):
        m = ev.calcular_metricas({"VP": 23, "VN": 9, "FP": 3, "FN": 5})
        self.assertEqual(m["precision"], 88.46)        # VP / (VP + FP)
        self.assertEqual(m["recall"], 82.14)           # VP / (VP + FN)
        self.assertEqual(m["rechazo_correcto"], 75.0)  # VN / (VN + FP)
        self.assertEqual(m["exactitud"], 80.0)

    def test_denominador_cero_es_nd(self):
        m = ev.calcular_metricas({"VP": 0, "VN": 5, "FP": 0, "FN": 0})
        self.assertIsNone(m["precision"])
        self.assertIsNone(m["recall"])
        self.assertEqual(ev.fmt(m["precision"]), "N/D")


class TestArbolesLLM(unittest.TestCase):
    def test_notacion_corchetes_y_funcional_equivalentes(self):
        a = ev.parsear_corchetes("[Oracion [Sujeto_sg [SN_m_sg [det_m_sg El] "
                                 "[n_m_sg gato] [ModNom_m_sg ε]]] "
                                 "[SV_sg [v_sg duerme]] .]")
        b = ev.parsear_corchetes("[Oracion [Sujeto_sg [SN_m_sg det_m_sg(El) "
                                 "n_m_sg(gato) ModNom_m_sg(ε)]] "
                                 "[SV_sg v_sg(duerme)] .]")
        self.assertIsNotNone(a)
        self.assertEqual(ev.normalizar_arbol(a), ev.normalizar_arbol(b))

    def test_arbol_mal_formado(self):
        self.assertIsNone(ev.parsear_corchetes("[Oracion [Sujeto_sg"))
        self.assertIsNone(ev.parsear_corchetes(None))

    def test_sin_errores_de_etiquetado(self):
        errores = ev.errores_etiquetado_llm(
            "El gato duerme.", "ACEPTADA",
            "[Oracion [Sujeto_sg [SN_m_sg det_m_sg(El) n_m_sg(gato)]] "
            "[SV_sg v_sg(duerme)] .]")
        self.assertEqual(errores, [])

    def test_tipos_de_error_de_etiquetado(self):
        errores = ev.errores_etiquetado_llm(
            "El gato duerme.", "ACEPTADA",
            "[Oracion [SN_m_sg El [n_f_sg gato]] .]")
        tipos = {e["palabra"]: e["tipo"] for e in errores}
        self.assertEqual(tipos, {"El": "sin_categoria",
                                 "gato": "categoria_incorrecta",
                                 "duerme": "palabra_omitida_o_alterada"})

    def test_rechazada_sin_estructura_no_cuenta(self):
        self.assertEqual(
            ev.errores_etiquetado_llm("Los gato duerme.", "RECHAZADA", None), [])

    def test_clasificar_regla(self):
        self.assertEqual(ev.clasificar_regla("Oracion -> Sujeto_sg SV_sg ."),
                         "produccion")
        self.assertEqual(ev.clasificar_regla("det_m_pl → los"), "lexica")
        self.assertEqual(ev.clasificar_regla("Oracion -> Sujeto_sg SV_sg"),
                         "inexistente")


class TestPrompts(unittest.TestCase):
    def test_plantillas_versionadas_al_dia(self):
        self.assertEqual(prompts.verificar_plantillas(), [])

    def test_mismas_instrucciones_en_ambos_modos(self):
        zero = prompts.plantilla_por_modo("zero-shot")
        few = prompts.plantilla_por_modo("few-shot")
        self.assertNotIn("EJEMPLOS RESUELTOS", zero)
        self.assertIn("EJEMPLOS RESUELTOS", few)
        # Quitando el bloque de ejemplos, el resto del prompt es identico.
        inicio = few.index("EJEMPLOS RESUELTOS")
        fin = few.index("FORMATO DE RESPUESTA")
        self.assertEqual(" ".join((few[:inicio] + few[fin:]).split()),
                         " ".join(zero.split()))

    def test_ejemplos_few_shot_fuera_del_corpus(self):
        corpus = {e["oracion"] for e in ejecutar_llm.cargar_corpus()}
        for ejemplo in prompts.EJEMPLOS_FEW_SHOT:
            self.assertNotIn(ejemplo["oracion"], corpus)
        decisiones = {e["decision"] for e in prompts.EJEMPLOS_FEW_SHOT}
        self.assertEqual(decisiones, {"ACEPTADA", "RECHAZADA"})


class TestValidacionRespuesta(unittest.TestCase):
    LOTE = [{"id": 1, "oracion": "El gato duerme."},
            {"id": 2, "oracion": "La gata corre."}]

    def _json(self, *resultados):
        import json
        return json.dumps({"resultados": list(resultados)})

    def test_respuesta_valida(self):
        texto = self._json(
            {"id": 2, "oracion": "La gata corre.", "decision": "ACEPTADA"},
            {"id": 1, "oracion": "El gato duerme.", "decision": "RECHAZADA"})
        r = ejecutar_llm.validar_respuesta(texto, self.LOTE)
        self.assertEqual([x["id"] for x in r], [1, 2])

    def test_rechaza_ids_faltantes_oracion_alterada_o_decision_invalida(self):
        casos = [
            self._json({"id": 1, "oracion": "El gato duerme.",
                        "decision": "ACEPTADA"}),
            self._json({"id": 1, "oracion": "El gato duerme",
                        "decision": "ACEPTADA"},
                       {"id": 2, "oracion": "La gata corre.",
                        "decision": "ACEPTADA"}),
            self._json({"id": 1, "oracion": "El gato duerme.",
                        "decision": "SI"},
                       {"id": 2, "oracion": "La gata corre.",
                        "decision": "ACEPTADA"}),
        ]
        for texto in casos:
            with self.assertRaises(ValueError):
                ejecutar_llm.validar_respuesta(texto, self.LOTE)


class TestEvaluacionCompleta(unittest.TestCase):
    """Corre la evaluacion sobre los logs reales del repositorio."""

    @classmethod
    def setUpClass(cls):
        cls.corpus = ev.cargar_corpus()
        cls.enfoques = ev.cargar_enfoques()
        cls.resumen, _ = ev.evaluar(cls.corpus, cls.enfoques)

    def test_cinco_enfoques_cuarenta_oraciones(self):
        self.assertEqual(len(self.corpus), 40)
        self.assertEqual(set(self.resumen), {c for c, _ in ev.ENFOQUES})
        for v in self.resumen.values():
            self.assertEqual(v["VP"] + v["VN"] + v["FP"] + v["FN"], 40)

    def test_coincide_con_los_resumenes_de_cada_log(self):
        import json
        for nombre in ("spacy", "segunda_herramienta"):
            with open(ev.LOGS / f"{nombre}.json", encoding="utf-8") as f:
                propio = json.load(f)["resumen"]
            for k in ("VP", "VN", "FP", "FN", "errores_etiquetado"):
                self.assertEqual(self.resumen[nombre][k], propio[k], (nombre, k))
        with open(ev.LOGS / "parser_propio.json", encoding="utf-8") as f:
            propio = json.load(f)["resumen"]["metricas"]
        for k in ("VP", "VN", "FP", "FN"):
            self.assertEqual(self.resumen["parser_propio"][k], propio[k])


if __name__ == "__main__":
    unittest.main()
