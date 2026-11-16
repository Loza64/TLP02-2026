"""Fase 2: ejecuta el corpus de prueba con el parser propio y guarda el log.

Para cada oración de ``corpus/corpus_pruebas.csv`` registra:

* si el parser la acepta o la rechaza, y si coincide con la etiqueta esperada;
* los tokens (palabra → terminal de la gramática);
* las producciones aplicadas (derivación por la izquierda) y la traza de la pila;
* el árbol sintáctico, en estructura anidada y en notación con paréntesis;
* para las rechazadas: el motivo clasificado (léxico, discordancia de género o
  número, coordinación, estructura incompleta…), la regla donde falló y el
  mensaje original del parser.

Salidas (por defecto en ``logs/``):

* ``parser_propio.json``           log completo, con metadatos y resumen.
* ``parser_propio.txt``            el mismo log en formato legible.
* ``parser_propio_resultados.csv`` una fila por oración, para el script de evaluación.

Uso (desde la raíz del proyecto):

    python -m espanol.ejecutar_corpus
    python -m espanol.ejecutar_corpus --corpus corpus/corpus_pruebas.csv --salida logs
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from parser.lexer import LanguageError, LexError
from parser.ll1 import END, EPSILON

from .grammar import GRAMMAR, PRODUCTIONS, TABLE, TERMINALS
from .lexer import tokenize
from .parser import ParseError, parse, pretty_tree

ROOT = Path(__file__).resolve().parent.parent
CORPUS_POR_DEFECTO = ROOT / "corpus" / "corpus_pruebas.csv"
SALIDA_POR_DEFECTO = ROOT / "logs"

ACEPTADA = "ACEPTADA"
RECHAZADA = "RECHAZADA"


# --------------------------------------------------------------------------- #
# Nombres legibles de los terminales
# --------------------------------------------------------------------------- #
_CATEGORIAS = {
    "det": "determinante", "n": "sustantivo", "adj": "adjetivo", "v": "verbo",
}
_GENEROS = {"m": "masculino", "f": "femenino"}
_NUMEROS = {"sg": "singular", "pl": "plural"}
_OTROS = {
    "adv_intens": "intensificador «muy»",
    "adv_modo": "adverbio de modo",
    "prep": "preposición",
    "que": "«que»",
    "conj": "conjunción «y»",
    ".": "punto final",
    END: "fin de la oración",
}


def rasgos(terminal: str) -> tuple[str, str | None, str | None]:
    """('adj', 'f', 'sg') para 'adj_f_sg'; ('v', None, 'pl') para 'v_pl'."""
    partes = terminal.split("_")
    if partes[0] in _CATEGORIAS:
        if len(partes) == 3:
            return partes[0], partes[1], partes[2]
        if len(partes) == 2:
            return partes[0], None, partes[1]
    return terminal, None, None


def nombre_terminal(terminal: str) -> str:
    if terminal in _OTROS:
        return _OTROS[terminal]
    cat, gen, num = rasgos(terminal)
    if cat not in _CATEGORIAS:
        return terminal
    piezas = [_CATEGORIAS[cat]]
    if gen in _GENEROS:
        piezas.append(_GENEROS[gen])
    if num:
        piezas.append(_NUMEROS.get(num, num))
    if gen == "inv":
        piezas.append("invariable en género")
    return " ".join(piezas)


def lista_esperados(terminales: list[str]) -> str:
    """'un determinante' si todos son determinantes; si no, 'A o B o C'."""
    if terminales and all(rasgos(t)[0] == "det" for t in terminales):
        return "un determinante"
    return " o ".join(nombre_terminal(t) for t in terminales)


# --------------------------------------------------------------------------- #
# Árboles
# --------------------------------------------------------------------------- #
def _vacio(node) -> bool:
    """True si el subárbol no produce ninguna palabra (solo ε)."""
    if node.symbol == EPSILON:
        return True
    if node.token is not None:
        return False
    return bool(node.children) and all(_vacio(c) for c in node.children)


def arbol_dict(node, con_epsilon: bool = False) -> dict:
    """Árbol como estructura anidada: {"simbolo", "palabra"?, "hijos"}."""
    d: dict = {"simbolo": node.symbol}
    if node.token is not None and node.token.type != END:
        d["palabra"] = node.token.value
    hijos = [c for c in node.children if con_epsilon or not _vacio(c)]
    d["hijos"] = [arbol_dict(c, con_epsilon) for c in hijos]
    return d


def arbol_parentesis(d: dict) -> str:
    """(Oracion (Sujeto_sg (SN_m_sg (det_m_sg El) (n_m_sg gato))) …)."""
    if "palabra" in d:
        return f"({d['simbolo']} {d['palabra']})"
    if not d["hijos"]:
        return f"({d['simbolo']})"
    return f"({d['simbolo']} " + " ".join(arbol_parentesis(h) for h in d["hijos"]) + ")"


def _ancestros(raiz, objetivo) -> list:
    """Camino de nodos desde la raíz hasta ``objetivo`` (incluidos)."""
    camino: list = []

    def buscar(n) -> bool:
        camino.append(n)
        if n is objetivo:
            return True
        for c in n.children:
            if buscar(c):
                return True
        camino.pop()
        return False

    buscar(raiz)
    return camino


# --------------------------------------------------------------------------- #
# Clasificación del motivo de rechazo
# --------------------------------------------------------------------------- #
def _lugar(contexto: list[str]) -> str:
    if any(s.startswith("SubOpt") for s in contexto):
        return " dentro de la oración relativa"
    if "Clausula" in contexto:
        return " dentro de la oración completiva"
    if "SN_Prep" in contexto:
        return " dentro del sintagma preposicional"
    return ""


_ENTRE = {
    "adj": "entre el sustantivo y el adjetivo",
    "n": "entre el determinante y el sustantivo",
    "v": "entre el sujeto y el verbo",
    "det": "en el determinante",
}


def clasificar_lexico(err: LexError) -> dict:
    m = re.search(r"'(.+?)'", err.message)
    palabra = m.group(1) if m else ""
    if "léxico" in err.message:
        categoria = "palabra_fuera_del_lexico"
        descripcion = f"La palabra '{palabra}' no está en el léxico de la gramática."
    else:
        categoria = "caracter_no_reconocido"
        descripcion = f"El carácter '{palabra}' no forma parte del lenguaje."
    return {
        "tipo": "lexico",
        "categoria": categoria,
        "descripcion": descripcion,
        "palabra": palabra,
        "mensaje": str(err),
        "linea": err.line,
        "columna": err.col,
    }


def clasificar_sintactico(err: ParseError) -> dict:
    found = err.found
    esperados: list[str] = err.expected
    camino = _ancestros(err.tree, err.node)
    contexto = [n.symbol for n in camino]

    def produccion(n) -> str:
        return f"{n.symbol} → " + " ".join(c.symbol for c in n.children)

    padre = camino[-2] if len(camino) >= 2 else None
    regla = produccion(padre) if padre is not None else f"{err.symbol} (símbolo inicial)"
    palabra = found.value if found.type != END else ""
    encontrado = nombre_terminal(found.type)
    esperado_txt = lista_esperados(esperados)

    cat_f, gen_f, num_f = rasgos(found.type)
    mismos = [e for e in esperados if rasgos(e)[0] == cat_f] if cat_f in _CATEGORIAS else []
    if cat_f == "v" and mismos:
        # El número del verbo lo fija la producción que coloca SV_sg / SV_pl
        # (Oracion, SubOpt o Clausula), no la regla del punto exacto del fallo.
        for n in reversed(camino[:-1]):
            if any(c.symbol.startswith("SV_") for c in n.children):
                regla = produccion(n)
                break
    # Dónde está el fallo: los ancestros, sin contar el propio símbolo que falló.
    lugar = _lugar(contexto[:-1])

    if found.type == "conj":
        categoria = "coordinacion_no_contemplada"
        descripcion = (
            "La gramática no tiene reglas de coordinación con 'y'. Agregarlas produce "
            "un conflicto LL(1) en M[Oracion, det_m_sg] (ver: python -m espanol --conflicto)."
        )
    elif found.type in (END, ".") and found.type not in esperados:
        categoria = "estructura_incompleta"
        descripcion = (
            f"La oración termina antes de completar la regla {regla}: "
            f"se esperaba {esperado_txt}."
        )
    elif mismos:
        con_genero = [rasgos(e)[1] for e in mismos if rasgos(e)[1] in ("m", "f")]
        dif_genero = gen_f in ("m", "f") and bool(con_genero) and all(g != gen_f for g in con_genero)
        dif_numero = all(rasgos(e)[2] != num_f for e in mismos)
        if dif_genero and dif_numero:
            categoria, que = "discordancia_genero_y_numero", "género y número"
        elif dif_genero:
            categoria, que = "discordancia_genero", "género"
        elif dif_numero:
            categoria, que = "discordancia_numero", "número"
        else:
            categoria, que = "estructura_no_contemplada", ""
        if que:
            descripcion = (
                f"Discordancia de {que} {_ENTRE.get(cat_f, '')}{lugar}: "
                f"se encontró '{palabra}' ({encontrado}) y la regla {regla} "
                f"exige {lista_esperados(mismos)}."
            )
        else:
            descripcion = f"Se encontró '{palabra}' ({encontrado}); se esperaba {esperado_txt}."
    elif esperados and all(rasgos(e)[0] == "det" for e in esperados):
        categoria = "falta_determinante"
        descripcion = (
            f"Se encontró '{palabra}' ({encontrado}) donde la gramática exige un "
            "determinante: todo sintagma nominal empieza con determinante."
        )
    else:
        categoria = "estructura_no_contemplada"
        descripcion = (
            f"Se encontró '{palabra}' ({encontrado}) en una posición que la gramática "
            f"no contempla; se esperaba {esperado_txt}."
        )

    return {
        "tipo": "sintactico",
        "categoria": categoria,
        "descripcion": descripcion,
        "palabra": palabra,
        "terminal_encontrado": found.type,
        "simbolo_en_tope": err.symbol,
        "esperados": esperados,
        "regla": regla,
        "regla_donde_fallo": produccion(padre) if padre is not None else None,
        "contexto": contexto,
        "mensaje": str(err),
        "linea": err.line,
        "columna": err.col,
    }


# --------------------------------------------------------------------------- #
# Ejecución
# --------------------------------------------------------------------------- #
def leer_corpus(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    for f in filas:
        f["id"] = int(f["id"])
        f["nivel"] = int(f["nivel"])
        f["esperado"] = f["esperado"].strip().upper()
    return filas


def analizar(oracion: str) -> dict:
    """Analiza una oración y devuelve el registro (sin los datos del corpus)."""
    traza: list = []
    registro: dict = {}
    try:
        tokens = tokenize(oracion)
        registro["tokens"] = [
            {"palabra": t.value, "terminal": t.type} for t in tokens if t.type != END
        ]
    except LexError:
        registro["tokens"] = None

    inicio = time.perf_counter()
    try:
        raiz = parse(oracion, trace=traza)
        registro["tiempo_ms"] = round((time.perf_counter() - inicio) * 1000, 4)
        registro["obtenido"] = ACEPTADA
        arbol = arbol_dict(raiz)
        registro["arbol"] = arbol
        registro["arbol_parentesis"] = arbol_parentesis(arbol)
        registro["arbol_texto"] = pretty_tree(raiz)
        registro["motivo"] = None
    except LanguageError as err:
        registro["tiempo_ms"] = round((time.perf_counter() - inicio) * 1000, 4)
        registro["obtenido"] = RECHAZADA
        registro["arbol"] = None
        registro["arbol_parentesis"] = None
        registro["arbol_texto"] = None
        registro["motivo"] = (
            clasificar_lexico(err) if isinstance(err, LexError) else clasificar_sintactico(err)
        )

    registro["derivacion"] = [
        accion.removeprefix("Expandir ") for (_, _, _, accion) in traza
        if accion.startswith("Expandir ")
    ]
    registro["traza"] = [
        {"paso": p, "pila": pila, "lookahead": look, "accion": accion}
        for (p, pila, look, accion) in traza
    ]
    return registro


def metricas(resultados: list[dict]) -> dict:
    vp = sum(r["esperado"] == ACEPTADA and r["obtenido"] == ACEPTADA for r in resultados)
    vn = sum(r["esperado"] == RECHAZADA and r["obtenido"] == RECHAZADA for r in resultados)
    fp = sum(r["esperado"] == RECHAZADA and r["obtenido"] == ACEPTADA for r in resultados)
    fn = sum(r["esperado"] == ACEPTADA and r["obtenido"] == RECHAZADA for r in resultados)

    def div(a: int, b: int):
        return round(a / b, 4) if b else None

    return {
        "VP": vp, "VN": vn, "FP": fp, "FN": fn,
        "precision": div(vp, vp + fp),
        "recall": div(vp, vp + fn),
        "rechazo_correcto": div(vn, vn + fp),
        "exactitud": div(vp + vn, len(resultados)),
    }


def resumen(resultados: list[dict]) -> dict:
    por_nivel = {}
    for nivel in sorted({r["nivel"] for r in resultados}):
        filas = [r for r in resultados if r["nivel"] == nivel]
        por_nivel[str(nivel)] = {
            "total": len(filas),
            "aceptadas": sum(r["obtenido"] == ACEPTADA for r in filas),
            "rechazadas": sum(r["obtenido"] == RECHAZADA for r in filas),
            "coinciden": sum(r["coincide"] for r in filas),
        }
    motivos: dict[str, int] = {}
    for r in resultados:
        if r["motivo"]:
            motivos[r["motivo"]["categoria"]] = motivos.get(r["motivo"]["categoria"], 0) + 1
    tiempos = [r["tiempo_ms"] for r in resultados]
    return {
        "total": len(resultados),
        "aceptadas": sum(r["obtenido"] == ACEPTADA for r in resultados),
        "rechazadas": sum(r["obtenido"] == RECHAZADA for r in resultados),
        "coinciden_con_esperado": sum(r["coincide"] for r in resultados),
        "metricas": metricas(resultados),
        "por_nivel": por_nivel,
        "motivos_de_rechazo": dict(sorted(motivos.items())),
        "tiempo_ms": {
            "total": round(sum(tiempos), 4),
            "promedio": round(sum(tiempos) / len(tiempos), 4) if tiempos else None,
            "maximo": max(tiempos) if tiempos else None,
        },
    }


def _commit_git() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def metadatos(corpus: Path) -> dict:
    datos = corpus.read_bytes()
    try:
        ruta_corpus = str(corpus.resolve().relative_to(ROOT))
    except ValueError:
        ruta_corpus = str(corpus)
    return {
        "enfoque": "parser propio LL(1) (CFG del español, Fase 1)",
        "fecha_ejecucion": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "comando": "python -m espanol.ejecutar_corpus " + " ".join(sys.argv[1:]),
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "commit_git": _commit_git(),
        "corpus": {
            "archivo": ruta_corpus.replace("\\", "/"),
            "sha256": hashlib.sha256(datos).hexdigest(),
        },
        "gramatica": {
            "simbolo_inicial": GRAMMAR.start,
            "producciones": len(PRODUCTIONS),
            "no_terminales": len(GRAMMAR.nonterminals),
            "terminales": len(TERMINALS),
            "celdas_tabla_ll1": sum(len(fila) for fila in TABLE.values()),
            "conflictos_ll1": 0,
        },
        "criterio": (
            "ACEPTADA si el parser LL(1) construye el árbol completo; RECHAZADA si falla "
            "el lexer o el análisis predictivo. Positivo = ACEPTADA."
        ),
    }


def ejecutar(corpus: Path) -> dict:
    resultados = []
    for fila in leer_corpus(corpus):
        r = {
            "id": fila["id"],
            "oracion": fila["oracion"],
            "nivel": fila["nivel"],
            "fenomeno": fila.get("fenomeno", ""),
            "esperado": fila["esperado"],
        }
        r.update(analizar(fila["oracion"]))
        r["coincide"] = r["obtenido"] == r["esperado"]
        resultados.append(r)
    return {"metadatos": metadatos(corpus), "resumen": resumen(resultados), "resultados": resultados}


# --------------------------------------------------------------------------- #
# Escritura de los archivos
# --------------------------------------------------------------------------- #
def texto_log(log: dict) -> str:
    m, s = log["metadatos"], log["resumen"]
    met = s["metricas"]
    lineas = [
        "LOG DEL PARSER PROPIO — Fase 2 (TLP02-2026)",
        "=" * 72,
        f"Fecha:      {m['fecha_ejecucion']}",
        f"Comando:    {m['comando'].strip()}",
        f"Python:     {m['python']}  ({m['plataforma']})",
        f"Commit:     {m['commit_git'] or 'desconocido'}",
        f"Corpus:     {m['corpus']['archivo']}  (sha256 {m['corpus']['sha256'][:16]}…)",
        f"Gramática:  {m['gramatica']['producciones']} producciones, "
        f"{m['gramatica']['celdas_tabla_ll1']} celdas LL(1), "
        f"símbolo inicial {m['gramatica']['simbolo_inicial']}",
        f"Criterio:   {m['criterio']}",
        "=" * 72,
        "",
    ]
    for r in log["resultados"]:
        marca = "coincide" if r["coincide"] else "NO COINCIDE"
        lineas += [
            f"ID: {r['id']}    Nivel: {r['nivel']}    Fenómeno: {r['fenomeno']}",
            f"Oración:    {r['oracion']}",
            f"Resultado:  {r['obtenido']}   (esperado {r['esperado']}: {marca})",
        ]
        if r["tokens"] is not None:
            lineas.append("Tokens:     " + " ".join(f"{t['palabra']}/{t['terminal']}" for t in r["tokens"]))
        if r["motivo"] is None:
            lineas.append(f"Árbol:      {r['arbol_parentesis']}")
            lineas.append("")
            lineas += ["    " + l for l in r["arbol_texto"].splitlines()]
        else:
            mo = r["motivo"]
            lineas.append(f"Motivo:     [{mo['categoria']}] {mo['descripcion']}")
            if mo["tipo"] == "sintactico":
                lineas.append(f"Regla:      {mo['regla']}   (falló en {mo['simbolo_en_tope']})")
            lineas.append(f"Mensaje:    {mo['mensaje']}")
        lineas.append(f"Tiempo:     {r['tiempo_ms']} ms")
        lineas += ["-" * 72, ""]

    lineas += [
        "RESUMEN",
        "=" * 72,
        f"Oraciones: {s['total']}   Aceptadas: {s['aceptadas']}   Rechazadas: {s['rechazadas']}   "
        f"Coinciden con lo esperado: {s['coinciden_con_esperado']}/{s['total']}",
        f"VP={met['VP']}  VN={met['VN']}  FP={met['FP']}  FN={met['FN']}",
        f"Precisión={met['precision']}  Recall={met['recall']}  "
        f"Rechazo correcto={met['rechazo_correcto']}  Exactitud={met['exactitud']}",
        "Por nivel:",
    ]
    for nivel, d in s["por_nivel"].items():
        lineas.append(
            f"  Nivel {nivel}: {d['total']} oraciones, {d['aceptadas']} aceptadas, "
            f"{d['rechazadas']} rechazadas, {d['coinciden']} coinciden"
        )
    lineas.append("Motivos de rechazo:")
    for cat, n in s["motivos_de_rechazo"].items():
        lineas.append(f"  {cat}: {n}")
    t = s["tiempo_ms"]
    lineas.append(f"Tiempo de análisis: total {t['total']} ms, promedio {t['promedio']} ms, máximo {t['maximo']} ms")
    return "\n".join(lineas) + "\n"


def escribir(log: dict, salida: Path) -> list[Path]:
    salida.mkdir(parents=True, exist_ok=True)
    rutas = [
        salida / "parser_propio.json",
        salida / "parser_propio.txt",
        salida / "parser_propio_resultados.csv",
    ]
    rutas[0].write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rutas[1].write_text(texto_log(log), encoding="utf-8")
    with open(rutas[2], "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "nivel", "oracion", "esperado", "obtenido", "coincide",
                    "motivo_categoria", "regla", "arbol"])
        for r in log["resultados"]:
            mo = r["motivo"] or {}
            w.writerow([r["id"], r["nivel"], r["oracion"], r["esperado"], r["obtenido"],
                        r["coincide"], mo.get("categoria", ""), mo.get("regla", ""),
                        r["arbol_parentesis"] or ""])
    return rutas


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        prog="python -m espanol.ejecutar_corpus",
        description="Ejecuta el corpus de la Fase 2 con el parser propio y guarda el log.",
    )
    ap.add_argument("--corpus", type=Path, default=CORPUS_POR_DEFECTO, help="CSV del corpus")
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO, help="carpeta de los logs")
    args = ap.parse_args(argv)

    log = ejecutar(args.corpus)
    rutas = escribir(log, args.salida)
    s = log["resumen"]
    met = s["metricas"]
    print(f"{s['total']} oraciones: {s['aceptadas']} aceptadas, {s['rechazadas']} rechazadas; "
          f"{s['coinciden_con_esperado']}/{s['total']} coinciden con lo esperado.")
    print(f"VP={met['VP']} VN={met['VN']} FP={met['FP']} FN={met['FN']} | "
          f"precisión={met['precision']} recall={met['recall']} "
          f"rechazo correcto={met['rechazo_correcto']}")
    for r in log["resultados"]:
        if not r["coincide"]:
            print(f"  ¡No coincide! ID {r['id']}: {r['oracion']} "
                  f"(esperado {r['esperado']}, obtenido {r['obtenido']})")
    for ruta in rutas:
        print(f"Guardado: {ruta}")
    return 0 if s["coinciden_con_esperado"] == s["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
