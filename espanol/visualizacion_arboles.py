"""Fase 2: dibuja los árboles sintácticos de las oraciones aceptadas.

Lee el log del parser propio (``logs/parser_propio.json``, generado por
``python -m espanol.ejecutar_corpus``) y produce, sin dependencias externas:

* ``arbol_XX.svg``       un árbol por oración aceptada (se abre en el navegador o
                         se inserta en Word / Google Docs);
* ``index.html``         galería con todos los árboles y su notación con paréntesis;
* ``arboles_forest.tex`` los mismos árboles para LaTeX (paquete ``forest``).

Por defecto se omiten los nodos que solo derivan ε (modificadores ausentes);
con ``--con-epsilon`` se dibuja el árbol de derivación completo.

Uso (desde la raíz del proyecto):

    python -m espanol.visualizacion_arboles
    python -m espanol.visualizacion_arboles --con-epsilon
    python -m espanol.visualizacion_arboles --oracion "el gato negro duerme." --salida figuras
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from .ejecutar_corpus import SALIDA_POR_DEFECTO, arbol_dict, arbol_parentesis
from .grammar import PRODUCTIONS
from .parser import parse

_NO_TERMINALES = {lhs for lhs, _ in PRODUCTIONS}

# Medidas del dibujo (px)
CHAR_W = 8.2          # ancho aproximado de un carácter monoespaciado de 13px
PAD_X = 14            # relleno horizontal dentro de cada caja
CAJA_H = 26
SEP_X = 14            # separación mínima entre subárboles hermanos
NIVEL_H = 64          # distancia vertical entre niveles
MARGEN = 24
CABECERA_H = 40

COLOR_NT = ("#EEF2FA", "#2F4A7A")      # (relleno, borde) no terminal
COLOR_T = ("#FCEBDD", "#B4541C")       # terminal (categoría de la palabra)
COLOR_PALABRA = "#13203A"
COLOR_ARISTA = "#8A94A6"
FUENTE_SIMBOLO = "Consolas, 'Courier New', monospace"
FUENTE_TEXTO = "'Segoe UI', Arial, sans-serif"


# --------------------------------------------------------------------------- #
# Disposición
# --------------------------------------------------------------------------- #
def _ancho_etiqueta(texto: str) -> float:
    return len(texto) * CHAR_W + 2 * PAD_X


def _medir(nodo: dict) -> float:
    """Ancho del subárbol; lo guarda en nodo['_w']."""
    propio = _ancho_etiqueta(nodo["simbolo"])
    if "palabra" in nodo:
        propio = max(propio, _ancho_etiqueta(nodo["palabra"]))
    hijos = nodo["hijos"]
    if hijos:
        suma = sum(_medir(h) for h in hijos) + SEP_X * (len(hijos) - 1)
        nodo["_w"] = max(propio, suma)
    else:
        nodo["_w"] = propio
    return nodo["_w"]


def _profundidad(nodo: dict) -> int:
    return 1 + max((_profundidad(h) for h in nodo["hijos"]), default=0)


def _ubicar(nodo: dict, x0: float, nivel: int) -> None:
    """Asigna nodo['_x'] (centro) y nodo['_nivel']; hijos centrados en su espacio."""
    nodo["_nivel"] = nivel
    hijos = nodo["hijos"]
    if not hijos:
        nodo["_x"] = x0 + nodo["_w"] / 2
        return
    suma = sum(h["_w"] for h in hijos) + SEP_X * (len(hijos) - 1)
    x = x0 + (nodo["_w"] - suma) / 2
    for h in hijos:
        _ubicar(h, x, nivel + 1)
        x += h["_w"] + SEP_X
    nodo["_x"] = (hijos[0]["_x"] + hijos[-1]["_x"]) / 2


# --------------------------------------------------------------------------- #
# SVG
# --------------------------------------------------------------------------- #
def svg_arbol(arbol: dict, titulo: str = "") -> str:
    arbol = json.loads(json.dumps(arbol))           # copia: no ensuciar el original
    ancho_arbol = _medir(arbol)
    niveles = _profundidad(arbol)
    _ubicar(arbol, MARGEN, 0)

    alto_cab = CABECERA_H if titulo else 0
    y_palabras = alto_cab + MARGEN + niveles * NIVEL_H + 8
    ancho = max(ancho_arbol + 2 * MARGEN, _ancho_etiqueta(titulo) * 0.9 if titulo else 0)
    alto = y_palabras + CAJA_H + MARGEN

    def y_nivel(n: int) -> float:
        return alto_cab + MARGEN + n * NIVEL_H

    aristas: list[str] = []
    cajas: list[str] = []

    def dibujar(nodo: dict) -> None:
        cx, cy = nodo["_x"], y_nivel(nodo["_nivel"])
        for h in nodo["hijos"]:
            hx, hy = h["_x"], y_nivel(h["_nivel"])
            aristas.append(
                f'<line x1="{cx:.1f}" y1="{cy + CAJA_H:.1f}" x2="{hx:.1f}" y2="{hy:.1f}" '
                f'stroke="{COLOR_ARISTA}" stroke-width="1.3"/>'
            )
            dibujar(h)
        es_nt = nodo["simbolo"] in _NO_TERMINALES
        relleno, borde = COLOR_NT if es_nt else COLOR_T
        w = _ancho_etiqueta(nodo["simbolo"])
        cajas.append(
            f'<rect x="{cx - w / 2:.1f}" y="{cy:.1f}" width="{w:.1f}" height="{CAJA_H}" rx="6" '
            f'fill="{relleno}" stroke="{borde}" stroke-width="1.2"/>'
            f'<text x="{cx:.1f}" y="{cy + CAJA_H / 2 + 4.5:.1f}" text-anchor="middle" '
            f'font-family="{FUENTE_SIMBOLO}" font-size="13" fill="{borde}">'
            f'{html.escape(nodo["simbolo"])}</text>'
        )
        if "palabra" in nodo:
            # La palabra va abajo, alineada con las demás palabras de la oración.
            aristas.append(
                f'<line x1="{cx:.1f}" y1="{cy + CAJA_H:.1f}" x2="{cx:.1f}" y2="{y_palabras:.1f}" '
                f'stroke="{COLOR_ARISTA}" stroke-width="1" stroke-dasharray="3 3"/>'
            )
            cajas.append(
                f'<text x="{cx:.1f}" y="{y_palabras + 18:.1f}" text-anchor="middle" '
                f'font-family="{FUENTE_TEXTO}" font-size="16" font-weight="600" '
                f'fill="{COLOR_PALABRA}">{html.escape(nodo["palabra"])}</text>'
            )

    dibujar(arbol)
    cabecera = ""
    if titulo:
        cabecera = (
            f'<text x="{MARGEN}" y="{MARGEN + 6}" font-family="{FUENTE_TEXTO}" font-size="16" '
            f'font-weight="600" fill="{COLOR_PALABRA}">{html.escape(titulo)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho:.0f}" height="{alto:.0f}" '
        f'viewBox="0 0 {ancho:.0f} {alto:.0f}">'
        f'<title>{html.escape(titulo or "Árbol sintáctico")}</title>'
        f'<rect width="100%" height="100%" fill="#FFFFFF"/>'
        f'{cabecera}{"".join(aristas)}{"".join(cajas)}</svg>\n'
    )


# --------------------------------------------------------------------------- #
# LaTeX (forest)
# --------------------------------------------------------------------------- #
def _tex(texto: str) -> str:
    return "{" + texto.replace("\\", r"\textbackslash{}").replace("_", r"\_") + "}"


def forest(arbol: dict) -> str:
    if "palabra" in arbol:
        return f"[{_tex(arbol['simbolo'])} [{_tex(arbol['palabra'])}, tier=palabra]]"
    hijos = " ".join(forest(h) for h in arbol["hijos"])
    return f"[{_tex(arbol['simbolo'])} {hijos}]"


def documento_forest(arboles: list[tuple[str, str, dict]]) -> str:
    partes = [
        "% Árboles sintácticos generados por: python -m espanol.visualizacion_arboles",
        "% Uso: \\usepackage{forest} en el preámbulo y \\input{arboles_forest.tex}",
        "% (o copiar el entorno forest de la oración que se necesite).",
        "",
    ]
    for ident, oracion, arbol in arboles:
        partes += [
            f"% {ident}: {oracion}",
            "\\begin{forest}",
            "  for tree={font=\\ttfamily\\small, s sep=4mm}",
            "  " + forest(arbol),
            "\\end{forest}",
            "",
        ]
    return "\n".join(partes)


# --------------------------------------------------------------------------- #
# Galería HTML
# --------------------------------------------------------------------------- #
def galeria(entradas: list[dict], con_epsilon: bool) -> str:
    filas = []
    for e in entradas:
        filas.append(
            f'<section id="id{e["id"]}"><h2>ID {e["id"]} · nivel {e["nivel"]} · '
            f'{html.escape(e["oracion"])}</h2>'
            f'<p class="fen">{html.escape(e.get("fenomeno", ""))}</p>'
            f'<img src="{e["archivo"]}" alt="Árbol sintáctico de: {html.escape(e["oracion"])}">'
            f'<pre>{html.escape(e["parentesis"])}</pre></section>'
        )
    indice = " · ".join(f'<a href="#id{e["id"]}">{e["id"]}</a>' for e in entradas)
    modo = "árbol de derivación completo (incluye ε)" if con_epsilon else "nodos que solo derivan ε omitidos"
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Árboles sintácticos — parser propio</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;margin:32px;color:#13203A;background:#FAFAF7}}
h1{{font-size:24px}} h2{{font-size:18px;margin:0 0 4px}}
section{{background:#fff;border:1px solid #DDD7C9;border-radius:10px;padding:16px;margin:0 0 20px;overflow-x:auto}}
.fen{{color:#5E6779;margin:0 0 8px;font-size:14px}}
pre{{font-family:Consolas,'Courier New',monospace;font-size:13px;white-space:pre-wrap;color:#4A5568}}
img{{max-width:none}}
</style></head><body>
<h1>Árboles sintácticos del parser propio ({len(entradas)} oraciones aceptadas)</h1>
<p>Generado con <code>python -m espanol.visualizacion_arboles</code> a partir de
<code>logs/parser_propio.json</code>; {modo}.</p>
<p>{indice}</p>
{''.join(filas)}
</body></html>
"""


# --------------------------------------------------------------------------- #
# Programa
# --------------------------------------------------------------------------- #
def generar(log_path: Path, salida: Path, con_epsilon: bool = False) -> list[Path]:
    log = json.loads(log_path.read_text(encoding="utf-8"))
    salida.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []
    entradas: list[dict] = []
    para_tex: list[tuple[str, str, dict]] = []
    ancho_id = max(2, len(str(max((r["id"] for r in log["resultados"]), default=0))))

    for r in log["resultados"]:
        if r["obtenido"] != "ACEPTADA":
            continue
        arbol = arbol_dict(parse(r["oracion"]), con_epsilon=True) if con_epsilon else r["arbol"]
        nombre = f"arbol_{r['id']:0{ancho_id}d}.svg"
        ruta = salida / nombre
        ruta.write_text(svg_arbol(arbol, f"ID {r['id']}: {r['oracion']}"), encoding="utf-8")
        escritos.append(ruta)
        entradas.append({
            "id": r["id"], "nivel": r["nivel"], "oracion": r["oracion"],
            "fenomeno": r.get("fenomeno", ""), "archivo": nombre,
            "parentesis": arbol_parentesis(arbol),
        })
        para_tex.append((f"ID {r['id']}", r["oracion"], arbol))

    indice = salida / "index.html"
    indice.write_text(galeria(entradas, con_epsilon), encoding="utf-8")
    tex = salida / "arboles_forest.tex"
    tex.write_text(documento_forest(para_tex), encoding="utf-8")
    return escritos + [indice, tex]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        prog="python -m espanol.visualizacion_arboles",
        description="Dibuja en SVG los árboles sintácticos de las oraciones aceptadas.",
    )
    ap.add_argument("--log", type=Path, default=SALIDA_POR_DEFECTO / "parser_propio.json",
                    help="log JSON del parser propio")
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO / "arboles",
                    help="carpeta donde se guardan los árboles")
    ap.add_argument("--con-epsilon", action="store_true",
                    help="dibujar también los nodos que solo derivan ε")
    ap.add_argument("--oracion", help="dibujar solo esta oración (no usa el log)")
    args = ap.parse_args(argv)

    if args.oracion:
        arbol = arbol_dict(parse(args.oracion), con_epsilon=args.con_epsilon)
        args.salida.mkdir(parents=True, exist_ok=True)
        ruta = args.salida / "arbol.svg"
        ruta.write_text(svg_arbol(arbol, args.oracion), encoding="utf-8")
        print(f"Guardado: {ruta}")
        return 0

    if not args.log.exists():
        print(f"No existe {args.log}. Ejecute primero: python -m espanol.ejecutar_corpus")
        return 1
    rutas = generar(args.log, args.salida, args.con_epsilon)
    svgs = sum(r.suffix == ".svg" for r in rutas)
    print(f"{svgs} árboles SVG, index.html y arboles_forest.tex en {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
