"""Fase 2 — Herramienta moderna 2: HuggingFace Transformers (BETO).

Se usan dos modelos BERT en español (BETO) ajustados sobre AnCora, ambos con la
tarea ``token-classification``:

    mrm8488/bert-spanish-cased-finetuned-pos         categoría gramatical (EAGLES)
    mrm8488/bert-spanish-cased-finetuned-pos-syntax  función sintáctica (SUJ, CD, CC, ROOT...)

Juntos dan, por palabra, la POS y la función sintáctica, que se comparan con la
estructura esperada (sujeto, verbo, objeto). La decisión ACEPTADA / RECHAZADA
se obtiene con los mismos criterios C1–C4 que spaCy (nlp/criterios.py),
adaptados a esta salida: no hay árbol de dependencias ni rasgos de género y
número, así que C3 queda «no evaluable».

Uso (desde la raíz del proyecto):
    python -m nlp.segunda_herramienta
    python -m nlp.segunda_herramienta --corpus corpus/corpus_pruebas.csv

Requisitos:
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install transformers
La primera ejecución descarga los modelos (~440 MB cada uno) desde el Hub.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForTokenClassification, AutoTokenizer

from . import comun
from . import criterios as C

MODELO_POS = "mrm8488/bert-spanish-cased-finetuned-pos"
MODELO_SINTAXIS = "mrm8488/bert-spanish-cased-finetuned-pos-syntax"
_PALABRA = re.compile(r"\w+|[^\w\s]")


class Etiquetador:
    """Clasificación de tokens a nivel de palabra (primer subtoken de cada palabra)."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.tokenizer = AutoTokenizer.from_pretrained(nombre)
        self.modelo = AutoModelForTokenClassification.from_pretrained(nombre).eval()

    @property
    def revision(self) -> str | None:
        """Commit del modelo en el Hub (carpeta snapshots/<sha>/ de la caché local)."""
        sha = getattr(self.modelo.config, "_commit_hash", None)
        if sha:
            return sha
        try:
            from transformers.utils import cached_file
            return Path(cached_file(self.nombre, "config.json")).parent.name
        except Exception:  # noqa: BLE001
            return None

    def __call__(self, palabras: list[str]) -> list[tuple[str, float]]:
        enc = self.tokenizer(palabras, is_split_into_words=True, return_tensors="pt", truncation=True)
        with torch.no_grad():
            probs = self.modelo(**enc).logits[0].softmax(-1)
        salida: list[tuple[str, float] | None] = [None] * len(palabras)
        for k, w in enumerate(enc.word_ids()):
            if w is not None and salida[w] is None:
                p, idx = probs[k].max(-1)
                salida[w] = (self.modelo.config.id2label[int(idx)], round(float(p), 4))
        return [s or ("O", 0.0) for s in salida]


# ---------------------------------------------------------------------------
# Criterios C1–C4 sobre la salida por palabra
# ---------------------------------------------------------------------------
def _es(tok: dict, prefijos) -> bool:
    return tok["pos"].startswith(tuple(prefijos) if not isinstance(prefijos, str) else prefijos)


def _raices(toks: list[dict]) -> list[dict]:
    return [t for t in toks if t["funcion"] == "ROOT"]


def _sujeto_principal(toks: list[dict]) -> dict | None:
    """Primer sustantivo con función SUJ antes del verbo principal."""
    raices = _raices(toks)
    limite = raices[0]["i"] if len(raices) == 1 else len(toks)
    return next((t for t in toks[:limite] if t["funcion"] == "SUJ" and _es(t, C.EAGLES_SUSTANTIVO)), None)


def c1_raiz_verbal(toks: list[dict]) -> dict:
    raices = _raices(toks)
    if len(raices) != 1:
        return {"cumple": False, "detalle": f"{len(raices)} tokens con función ROOT"}
    r = raices[0]
    if not _es(r, C.EAGLES_VERBO_FINITO):
        return {"cumple": False, "detalle": f"la raíz '{r['texto']}' es {r['pos']}, no un verbo conjugado"}
    return {"cumple": True, "detalle": f"raíz verbal '{r['texto']}' ({r['pos']})"}


def c2_sujeto_nominal(toks: list[dict]) -> dict:
    s = _sujeto_principal(toks)
    if s is None:
        return {"cumple": False, "detalle": "ningún sustantivo con función SUJ antes del verbo principal"}
    if s["i"] == 0 or not _es(toks[s["i"] - 1], C.EAGLES_DETERMINANTE):
        return {"cumple": False, "detalle": f"el sujeto '{s['texto']}' no va precedido de determinante"}
    return {"cumple": True, "detalle": f"sujeto '{s['texto']}'"}


def c3_concordancia(toks: list[dict]) -> dict:
    return {
        "cumple": None,
        "detalle": "no evaluable: las etiquetas EAGLES del modelo no incluyen género ni número",
        "no_evaluables": None,
    }


def c4_alcance_cfg(toks: list[dict]) -> dict:
    fuera = []
    for t in toks:
        f = t["funcion"]
        if t["pos"] == C.EAGLES_COORDINANTE:
            fuera.append(f"coordinación '{t['texto']}' (CC) sin producción en la CFG")
        if f not in C.FUNCIONES_HF_PERMITIDAS:
            fuera.append(f"'{t['texto']}' con función '{f}' sin producción en la CFG")
        elif f == "CD":
            previos = toks[: t["i"]]
            completiva = _es(t, "V") and any(p["pos"] == "CS" and p["texto"].lower() == "que" for p in previos)
            if not completiva:
                fuera.append(f"'{t['texto']}' es objeto directo (CD) y la CFG no tiene objeto directo")
        elif f == "CREG" and t["pos"] != "SP":
            fuera.append(f"'{t['texto']}' con función CREG no es un SP")
        elif f == "SUJ" and _es(t, "PR"):
            antecedente = next((p for p in reversed(toks[: t["i"]]) if _es(p, "N")), None)
            if antecedente is None or antecedente["funcion"] != "SUJ":
                fuera.append(f"relativa '{t['texto']}' no modifica a un sujeto")
        elif f == "SUJ" and not _es(t, ("N", "PR")):
            fuera.append(f"sujeto '{t['texto']}' ({t['pos']}) no es nominal")
    if fuera:
        return {"cumple": False, "detalle": "; ".join(fuera)}
    return {"cumple": True, "detalle": "todas las funciones tienen producción equivalente"}


def evaluar(toks: list[dict]) -> dict:
    return {
        "C1_raiz_verbal": c1_raiz_verbal(toks),
        "C2_sujeto_nominal": c2_sujeto_nominal(toks),
        "C3_concordancia": c3_concordancia(toks),
        "C4_alcance_cfg": c4_alcance_cfg(toks),
    }


def roles(toks: list[dict]) -> dict:
    raices = _raices(toks)
    s = _sujeto_principal(toks)
    objeto = None
    cd = next((t for t in toks if t["funcion"] == "CD"), None)
    if cd is not None:
        objeto = cd if _es(cd, "N") else next((t for t in toks[cd["i"]:] if _es(t, "N")), None)
    return {
        "sujeto": s["texto"] if s else None,
        "verbo": raices[0]["texto"] if len(raices) == 1 else None,
        "objeto": objeto["texto"] if objeto else None,
    }


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------
def procesar(pos: Etiquetador, sint: Etiquetador, corpus: list[dict]) -> list[dict]:
    resultados = []
    for fila in corpus:
        marca = comun.ahora()
        t0 = time.perf_counter()
        palabras = _PALABRA.findall(fila["oracion"])
        etiq_pos, etiq_fun = pos(palabras), sint(palabras)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        toks = [
            {"i": i, "texto": w, "pos": p, "conf_pos": cp, "funcion": f, "conf_funcion": cf}
            for i, (w, (p, cp), (f, cf)) in enumerate(zip(palabras, etiq_pos, etiq_fun))
        ]

        crit = evaluar(toks)
        decision, motivos = comun.decidir(crit)
        obtenido = roles(toks)
        e_pos = comun.errores_pos(
            [(t["texto"], t["pos"]) for t in toks], C.CATEGORIA_A_EAGLES, lambda p, ok: p.startswith(ok)
        )
        e_roles = comun.errores_roles(obtenido, comun.parsear_estructura(fila.get("estructura_esperada")))

        r = {
            "id": fila["id"],
            "oracion": fila["oracion"],
            "nivel": fila["nivel"],
            "fenomeno": fila.get("fenomeno"),
            "esperado": fila["esperado"],
            "timestamp": marca,
            "tiempo_ms": ms,
            "produjo_analisis": bool(toks),
            "tokens": toks,
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
        }
        resultados.append(r)
        imprimir_oracion(r)
    return resultados


def imprimir_oracion(r: dict) -> None:
    print(f"\n[{r['id']}] (nivel {r['nivel']}) {r['oracion']}")
    print("-" * 70)
    print(f"  {'Texto':<14} {'POS':<6} {'Función':<8} Confianza (POS / función)")
    for t in r["tokens"]:
        print(f"  {t['texto']:<14} {t['pos']:<6} {t['funcion']:<8} {t['conf_pos']:.2f} / {t['conf_funcion']:.2f}")
    print(f"  -> {r['decision']} (esperado {r['esperado']}, {r['clasificacion']})")
    for m in r["motivos_rechazo"]:
        print(f"     · {m}")


def main(argv: list[str] | None = None) -> int:
    comun.configurar_salida()
    ap = argparse.ArgumentParser(prog="python -m nlp.segunda_herramienta", description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, default=comun.CORPUS_POR_DEFECTO)
    ap.add_argument("--salida", type=Path, default=comun.LOGS_DIR / "segunda_herramienta.json")
    args = ap.parse_args(argv)

    corpus = comun.cargar_corpus(args.corpus)
    transformers.logging.set_verbosity_error()
    transformers.utils.logging.disable_progress_bar()
    torch.manual_seed(0)
    pos, sint = Etiquetador(MODELO_POS), Etiquetador(MODELO_SINTAXIS)

    inicio = comun.ahora()
    resultados = procesar(pos, sint, corpus)
    fin = comun.ahora()

    res = comun.resumen(resultados)
    comun.escribir_log(args.salida, {
        "herramienta": "HuggingFace Transformers",
        "version_libreria": transformers.__version__,
        "version_torch": torch.__version__,
        "modelo": {"pos": MODELO_POS, "sintaxis": MODELO_SINTAXIS},
        "version_modelo": {"pos": pos.revision, "sintaxis": sint.revision},
        "configuracion": {
            "tarea": "token-classification",
            "agregacion": "etiqueta del primer subtoken de cada palabra (argmax)",
            "segmentacion": r"regex \w+|[^\w\s]",
            "dispositivo": "CPU",
            "modo": "eval, sin muestreo (determinista)",
            "etiquetas_pos": list(pos.modelo.config.id2label.values()),
            "etiquetas_funcion": list(sint.modelo.config.id2label.values()),
        },
        "entorno": comun.entorno(),
        "inicio": inicio,
        "fin": fin,
        "corpus": {"ruta": comun.relativa(args.corpus), "sha256": comun.sha256(args.corpus), "n_oraciones": len(corpus)},
        "metodologia": {
            "version_criterios": C.VERSION_CRITERIOS,
            "criterios": C.CRITERIOS,
            "regla_decision": "ACEPTADA si C1, C2 y C4 se cumplen (C3 no evaluable); RECHAZADA en otro caso.",
            "funciones_permitidas": C.FUNCIONES_HF_PERMITIDAS,
        },
        "resultados": resultados,
        "resumen": res,
    })
    comun.imprimir_resumen(f"Transformers {transformers.__version__} / BETO (AnCora)", res, args.salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
