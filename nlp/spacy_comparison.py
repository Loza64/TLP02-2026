"""Fase 2 — Herramienta moderna 1: spaCy.

Procesa el corpus completo con spaCy y su modelo de español, registra tokens,
POS, rasgos morfológicos y dependencias, aplica los criterios de
nlp/criterios.py para obtener ACEPTADA / RECHAZADA y guarda el log en
logs/spacy.json. Además exporta los árboles de dependencias a HTML (displaCy).

Uso (desde la raíz del proyecto):
    python -m nlp.spacy_comparison
    python -m nlp.spacy_comparison --corpus corpus/corpus_pruebas.csv --modelo es_core_news_sm

Requisitos:
    pip install spacy
    python -m spacy download es_core_news_sm
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import spacy
from spacy import displacy

from . import comun
from . import criterios as C

HTML_POR_DEFECTO = comun.ROOT / "nlp" / "results" / "arboles_spacy.html"


def cargar_modelo(nombre: str):
    try:
        return spacy.load(nombre)
    except OSError:
        raise SystemExit(
            f"[-] El modelo '{nombre}' no está instalado.\n"
            f"    Ejecuta: python -m spacy download {nombre}"
        )


# ---------------------------------------------------------------------------
# Extracción
# ---------------------------------------------------------------------------
def token_a_dict(t) -> dict:
    return {
        "i": t.i,
        "texto": t.text,
        "lema": t.lemma_,
        "pos": t.pos_,
        "tag": t.tag_,
        "morph": t.morph.to_dict(),
        "dep": t.dep_,
        "head_i": t.head.i,
        "head_texto": t.head.text,
    }


def arbol_parentizado(t) -> str:
    """(ROOT duerme/VERB (nsubj gato/NOUN (det El/DET)) ...)"""
    hijos = " ".join(arbol_parentizado(h) for h in t.children)
    return f"({t.dep_} {t.text}/{t.pos_}{(' ' + hijos) if hijos else ''})"


def roles(doc) -> dict:
    raices = [t for t in doc if t.dep_ == "ROOT"]
    if len(raices) != 1:
        return {"sujeto": None, "verbo": None, "objeto": None}
    raiz = raices[0]
    hijo = lambda dep: next((h.text for h in raiz.children if h.dep_ == dep), None)  # noqa: E731
    return {"sujeto": hijo("nsubj"), "verbo": raiz.text, "objeto": hijo("obj")}


# ---------------------------------------------------------------------------
# Criterios C1–C4 (ver nlp/criterios.py)
# ---------------------------------------------------------------------------
def _rasgo(t, nombre: str) -> str | None:
    valores = t.morph.get(nombre)
    return valores[0] if valores else None


def c1_raiz_verbal(doc) -> dict:
    oraciones = list(doc.sents)
    raices = [t for t in doc if t.dep_ == "ROOT"]
    if len(oraciones) != 1 or len(raices) != 1:
        return {"cumple": False, "detalle": f"{len(raices)} raíces en {len(oraciones)} oraciones"}
    r = raices[0]
    if r.pos_ not in C.POS_VERBO_UD:
        return {"cumple": False, "detalle": f"la raíz '{r.text}' es {r.pos_}, no un verbo"}
    forma = _rasgo(r, "VerbForm")
    if forma in C.VERBFORM_NO_FINITA:
        return {"cumple": False, "detalle": f"la raíz '{r.text}' no está conjugada (VerbForm={forma})"}
    return {"cumple": True, "detalle": f"raíz verbal '{r.text}'"}


def c2_sujeto_nominal(doc) -> dict:
    raiz = next((t for t in doc if t.dep_ == "ROOT"), None)
    sujetos = [h for h in raiz.children if h.dep_ == "nsubj"] if raiz is not None else []
    if len(sujetos) != 1:
        return {"cumple": False, "detalle": f"el verbo principal tiene {len(sujetos)} sujetos"}
    s = sujetos[0]
    if s.pos_ not in C.POS_SUSTANTIVO_UD:
        return {"cumple": False, "detalle": f"el núcleo del sujeto '{s.text}' es {s.pos_}"}
    if not any(h.dep_ == "det" for h in s.children):
        return {"cumple": False, "detalle": f"el sujeto '{s.text}' no tiene determinante"}
    return {"cumple": True, "detalle": f"sujeto '{s.text}'"}


def c3_concordancia(doc) -> dict:
    violaciones, no_evaluables, revisados = [], 0, 0

    def comparar(a, b, rasgos, etiqueta):
        nonlocal no_evaluables, revisados
        for rasgo in rasgos:
            va, vb = _rasgo(a, rasgo), _rasgo(b, rasgo)
            if va is None or vb is None:
                no_evaluables += 1
                continue
            revisados += 1
            if va != vb:
                violaciones.append(f"{etiqueta} '{a.text}'({va}) ≠ '{b.text}'({vb}) en {rasgo}")

    for t in doc:
        if t.dep_ in ("det", "amod") and t.head.pos_ == "NOUN":
            comparar(t, t.head, ("Gender", "Number"), t.dep_)
        elif t.dep_ == "nsubj" and t.pos_ == "NOUN" and t.head.pos_ in C.POS_VERBO_UD:
            comparar(t, t.head, ("Number",), "sujeto–verbo")
        elif t.dep_ in C.RELATIVA_UD and t.head.pos_ == "NOUN":
            comparar(t, t.head, ("Number",), "relativa–antecedente")

    detalle = (f"{revisados} rasgos comparados, {no_evaluables} no evaluables "
               "(la herramienta no predijo el rasgo)")
    if violaciones:
        return {"cumple": False, "detalle": "; ".join(violaciones), "no_evaluables": no_evaluables}
    return {"cumple": True, "detalle": detalle, "no_evaluables": no_evaluables}


def c4_alcance_cfg(doc) -> dict:
    fuera = []
    for t in doc:
        if t.dep_ not in C.RELACIONES_UD_PERMITIDAS:
            fuera.append(f"'{t.text}' con relación '{t.dep_}' sin producción en la CFG")
        elif t.dep_ in C.RELATIVA_UD:
            if t.head.dep_ != "nsubj":
                fuera.append(f"relativa '{t.text}' no modifica a un sujeto")
            elif not any(h.dep_ == "nsubj" and h.lower_ == "que" for h in t.children):
                fuera.append(f"relativa '{t.text}' no es de sujeto (que + SV)")
        elif t.dep_ in C.COMPLETIVA_UD:
            if not any(h.dep_ == "mark" and h.lower_ == "que" for h in t.children):
                fuera.append(f"completiva '{t.text}' sin «que»")
        elif t.dep_ == "obl" and t.head.pos_ not in C.POS_VERBO_UD:
            fuera.append(f"SP '{t.text}' cuelga de '{t.head.text}' y la CFG solo lo admite tras el verbo")
    if fuera:
        return {"cumple": False, "detalle": "; ".join(fuera)}
    return {"cumple": True, "detalle": "todas las relaciones tienen producción equivalente"}


def evaluar(doc) -> dict:
    return {
        "C1_raiz_verbal": c1_raiz_verbal(doc),
        "C2_sujeto_nominal": c2_sujeto_nominal(doc),
        "C3_concordancia": c3_concordancia(doc),
        "C4_alcance_cfg": c4_alcance_cfg(doc),
    }


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------
def procesar(nlp, corpus: list[dict]) -> tuple[list[dict], list]:
    resultados, docs = [], []
    for fila in corpus:
        t0 = time.perf_counter()
        marca = comun.ahora()
        doc = nlp(fila["oracion"])
        ms = round((time.perf_counter() - t0) * 1000, 2)
        docs.append(doc)

        crit = evaluar(doc)
        decision, motivos = comun.decidir(crit)
        obtenido = roles(doc)
        e_pos = comun.errores_pos(
            [(t.text, t.pos_) for t in doc], C.CATEGORIA_A_UPOS, lambda p, ok: p in ok
        )
        e_roles = comun.errores_roles(obtenido, comun.parsear_estructura(fila.get("estructura_esperada")))
        raiz = next((t for t in doc if t.dep_ == "ROOT"), None)

        resultados.append({
            "id": fila["id"],
            "oracion": fila["oracion"],
            "nivel": fila["nivel"],
            "fenomeno": fila.get("fenomeno"),
            "esperado": fila["esperado"],
            "timestamp": marca,
            "tiempo_ms": ms,
            "produjo_analisis": len(doc) > 0,
            "tokens": [token_a_dict(t) for t in doc],
            "arbol": arbol_parentizado(raiz) if raiz is not None else None,
            "roles": obtenido,
            "criterios": crit,
            "decision": decision,
            "motivos_rechazo": motivos,
            "clasificacion": comun.clasificar(fila["esperado"], decision),
            "errores_etiquetado": {
                "pos_vs_lexico_cfg": e_pos,
                "roles_vs_estructura_esperada": e_roles,
                "total": len(e_pos) + len(e_roles or []),
            },
        })
        imprimir_oracion(resultados[-1], doc)
    return resultados, docs


def imprimir_oracion(r: dict, doc) -> None:
    print(f"\n[{r['id']}] (nivel {r['nivel']}) {r['oracion']}")
    print("-" * 70)
    print(f"  {'Texto':<14} {'POS':<6} {'Dep':<10} {'Cabeza':<14} Morfología")
    for t in doc:
        print(f"  {t.text:<14} {t.pos_:<6} {t.dep_:<10} {t.head.text:<14} {t.morph}")
    print(f"  -> {r['decision']} (esperado {r['esperado']}, {r['clasificacion']})")
    for m in r["motivos_rechazo"]:
        print(f"     · {m}")


def main(argv: list[str] | None = None) -> int:
    comun.configurar_salida()
    ap = argparse.ArgumentParser(prog="python -m nlp.spacy_comparison", description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, default=comun.CORPUS_POR_DEFECTO)
    ap.add_argument("--modelo", default="es_core_news_sm")
    ap.add_argument("--salida", type=Path, default=comun.LOGS_DIR / "spacy.json")
    ap.add_argument("--html", type=Path, default=HTML_POR_DEFECTO)
    args = ap.parse_args(argv)

    corpus = comun.cargar_corpus(args.corpus)
    nlp = cargar_modelo(args.modelo)
    inicio = comun.ahora()
    resultados, docs = procesar(nlp, corpus)
    fin = comun.ahora()

    res = comun.resumen(resultados)
    comun.escribir_log(args.salida, {
        "herramienta": "spaCy",
        "version_libreria": spacy.__version__,
        "modelo": args.modelo,
        "version_modelo": nlp.meta.get("version"),
        "configuracion": {
            "pipeline": nlp.pipe_names,
            "descripcion_modelo": nlp.meta.get("description"),
            "dispositivo": "CPU",
        },
        "entorno": comun.entorno(),
        "inicio": inicio,
        "fin": fin,
        "corpus": {"ruta": comun.relativa(args.corpus), "sha256": comun.sha256(args.corpus), "n_oraciones": len(corpus)},
        "metodologia": {
            "version_criterios": C.VERSION_CRITERIOS,
            "criterios": C.CRITERIOS,
            "regla_decision": "ACEPTADA si C1, C2, C3 y C4 se cumplen; RECHAZADA en otro caso.",
            "relaciones_permitidas": C.RELACIONES_UD_PERMITIDAS,
        },
        "resultados": resultados,
        "resumen": res,
    })

    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(displacy.render(docs, style="dep", page=True), encoding="utf-8")
    comun.imprimir_resumen(f"spaCy {spacy.__version__} / {args.modelo}", res, args.salida)
    print(f"[+] Árboles de dependencias en '{comun.relativa(args.html)}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
