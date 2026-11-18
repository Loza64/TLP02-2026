"""Metodología común para convertir un análisis de NLP en ACEPTADA / RECHAZADA.

spaCy y los modelos de HuggingFace no deciden si una oración es gramatical:
siempre devuelven algún análisis. Para compararlos con el parser propio se
define una regla de decisión explícita, igual para ambas herramientas, con
cuatro criterios. Una oración se marca ACEPTADA solo si cumple los cuatro.

    C1  Raíz verbal finita
        La herramienta identifica exactamente un núcleo principal y es un verbo
        conjugado (no infinitivo, gerundio ni participio, no un sustantivo).

    C2  Sujeto nominal explícito
        El verbo principal tiene un sujeto cuyo núcleo es un sustantivo y, como
        exige la CFG (SN → det n ModNom), va acompañado de un determinante.

    C3  Concordancia
        det–sustantivo y adjetivo–sustantivo (género y número), sujeto–verbo
        (número), según los rasgos morfológicos que la herramienta predice.
        Si la herramienta no predice el rasgo, el par queda «no evaluable» y no
        cuenta como violación: no se agrega conocimiento externo a la herramienta.

    C4  Alcance estructural de la CFG
        Todas las relaciones (spaCy) o funciones sintácticas (HuggingFace) que
        aparecen en el análisis tienen una producción equivalente en la CFG.
        Una relación sin equivalente (objeto directo, coordinación, etc.) hace
        que la oración quede fuera del lenguaje generado por la gramática.

El léxico cerrado de la CFG NO se aplica en la decisión: si se aplicara, las
herramientas solo repetirían el filtro léxico del parser propio. Sí se usa,
aparte, como referencia para contar errores de etiquetado POS.

IMPORTANTE: las tablas de este archivo describen la gramática de
espanol/grammar.py. Si se amplía la gramática para el corpus de la Fase 2
(por ejemplo, objeto directo), hay que actualizar RELACIONES_UD_PERMITIDAS y
FUNCIONES_HF_PERMITIDAS ANTES de ejecutar los scripts, y documentarlo.
"""
from __future__ import annotations

VERSION_CRITERIOS = "1.0"

CRITERIOS = {
    "C1_raiz_verbal": "Exactamente un núcleo principal y es un verbo conjugado.",
    "C2_sujeto_nominal": "El verbo principal tiene un sujeto con núcleo sustantivo y determinante.",
    "C3_concordancia": "Concordancia det–n, adj–n (género/número) y sujeto–verbo (número), "
                       "según los rasgos que predice la herramienta.",
    "C4_alcance_cfg": "Todas las relaciones/funciones del análisis tienen una producción "
                      "equivalente en la CFG.",
}

# ---------------------------------------------------------------------------
# spaCy (Universal Dependencies). Relación UD -> producción(es) de la CFG.
# ---------------------------------------------------------------------------
RELACIONES_UD_PERMITIDAS: dict[str, str] = {
    "ROOT":   "Oracion → Sujeto SV .   (núcleo del SV)",
    "nsubj":  "Oracion → Sujeto_x SV_x . / Clausula → Sujeto SV / relativa: que",
    "det":    "SN_g_n → det_g_n n_g_n ModNom_g_n",
    "amod":   "ModNom → Adj | adv_intens Adj",
    "advmod": "ModNom → adv_intens Adj  /  AdvOpt → adv_modo",
    "obl":    "SPOpt → prep SN_Prep",
    "case":   "SPOpt → prep SN_Prep   (la preposición)",
    "acl":    "SubOpt_x → que SV_x   (relativa de sujeto)",
    "acl:relcl": "SubOpt_x → que SV_x   (relativa de sujeto)",
    "ccomp":  "RestoSV → que Clausula   (completiva)",
    "mark":   "RestoSV → que Clausula   (el «que» completivo)",
    "punct":  "Oracion → ... '.'",
}
# Relaciones que la CFG actual NO genera (se listan para el informe):
#   obj, iobj (no hay complemento directo/indirecto), conj, cc (la coordinación
#   provoca un conflicto LL(1)), xcomp, advcl, csubj, cop, aux, nmod (el SP solo
#   cuelga del verbo), appos, flat, compound, nummod.

# Relaciones que solo pueden colgar de un tipo de núcleo concreto.
RELATIVA_UD = {"acl", "acl:relcl"}          # solo sobre el núcleo de un sujeto
COMPLETIVA_UD = {"ccomp"}                    # solo con «que» como mark

POS_SUSTANTIVO_UD = {"NOUN"}                 # la CFG no tiene nombres propios
POS_VERBO_UD = {"VERB", "AUX"}
VERBFORM_NO_FINITA = {"Inf", "Ger", "Part"}

# ---------------------------------------------------------------------------
# HuggingFace: funciones sintácticas de AnCora (modelo *-pos-syntax).
# ---------------------------------------------------------------------------
FUNCIONES_HF_PERMITIDAS: dict[str, str] = {
    "ROOT": "núcleo del SV principal",
    "SUJ":  "Sujeto_x (sustantivo) o «que» de la relativa de sujeto: SubOpt_x → que SV_x",
    "CC":   "AdvOpt → adv_modo  /  SPOpt → prep SN_Prep (complemento circunstancial)",
    "CREG": "SPOpt → prep SN_Prep (solo si empieza por preposición)",
    "CD":   "RestoSV → que Clausula (solo si es el verbo de una completiva con «que»)",
    "PUNC": "'.'",
    "_":    "token sin función propia (determinante, adjetivo, preposición, etc.)",
    "O":    "token sin función propia",
}
# Funciones que la CFG actual NO genera: CD nominal (objeto directo), CD.Q, CI,
# ATR, ATR.d, CPRED*, CAG, PASS, IMPERS, VOC, NEG, ET, MOD.

# Prefijos EAGLES (modelo *-pos) usados por los criterios.
EAGLES_VERBO_FINITO = ("VMI", "VMS", "VMM", "VAI", "VAS", "VAM", "VSI", "VSS", "VSM")
EAGLES_SUSTANTIVO = ("NC",)
EAGLES_DETERMINANTE = ("D",)
EAGLES_COORDINANTE = "CC"                    # conjunción coordinante «y»

# ---------------------------------------------------------------------------
# Referencia léxica para errores de etiquetado POS: categoría del terminal de
# la CFG (prefijo antes del primer «_») -> etiquetas aceptables.
# ---------------------------------------------------------------------------
CATEGORIA_A_UPOS: dict[str, set[str]] = {
    "det": {"DET"},
    "n": {"NOUN"},
    "adj": {"ADJ"},
    "v": {"VERB", "AUX"},
    "adv": {"ADV"},
    "prep": {"ADP"},
    "que": {"SCONJ", "PRON"},
    "conj": {"CCONJ"},
}
CATEGORIA_A_EAGLES: dict[str, tuple[str, ...]] = {
    "det": ("D",),
    "n": ("N",),
    "adj": ("A",),
    "v": ("V",),
    "adv": ("R",),
    "prep": ("SP",),
    "que": ("CS", "PR"),
    "conj": ("CC",),
}
