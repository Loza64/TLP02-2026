"""Utilidades compartidas por spacy_comparison.py y segunda_herramienta.py.

- Lectura del corpus (corpus/corpus_pruebas.csv).
- Referencia léxica de la CFG para contar errores de etiquetado POS.
- Comparación con la columna opcional ``estructura_esperada``.
- Clasificación VP / VN / FP / FN y resumen de métricas.
- Metadatos y escritura del log JSON en logs/.
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from espanol.lexer import LEXICON  # noqa: E402  (léxico cerrado de la CFG)

CORPUS_POR_DEFECTO = ROOT / "corpus" / "corpus_pruebas.csv"
LOGS_DIR = ROOT / "logs"
ETIQUETAS = {"ACEPTADA", "RECHAZADA"}
ROLES = ("sujeto", "verbo", "objeto")


def ahora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def configurar_salida() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------
def cargar_corpus(ruta: Path) -> list[dict]:
    """Lee el CSV del corpus. Columnas obligatorias: id, oracion, nivel, esperado.

    Columnas opcionales: fenomeno, estructura_esperada.
    """
    if not ruta.exists():
        raise SystemExit(
            f"[-] No se encontró el corpus en '{ruta}'.\n"
            "    El corpus lo entrega el Integrante 1 (corpus/corpus_pruebas.csv) "
            "o se indica otra ruta con --corpus."
        )
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    faltan = {"id", "oracion", "nivel", "esperado"} - set(filas[0] if filas else {})
    if faltan:
        raise SystemExit(f"[-] Al corpus le faltan columnas: {', '.join(sorted(faltan))}")
    for fila in filas:
        fila["esperado"] = fila["esperado"].strip().upper()
        if fila["esperado"] not in ETIQUETAS:
            raise SystemExit(f"[-] Etiqueta inválida en id={fila['id']}: {fila['esperado']!r}")
        fila["oracion"] = fila["oracion"].strip()
    return filas


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def parsear_estructura(texto: str | None) -> dict[str, str]:
    """'sujeto=niño; verbo=come; objeto=pan' -> {'sujeto': 'niño', ...}."""
    if not texto:
        return {}
    resultado = {}
    for parte in texto.split(";"):
        if "=" in parte:
            clave, valor = parte.split("=", 1)
            clave = clave.strip().lower()
            if clave in ROLES:
                resultado[clave] = valor.strip()
    return resultado


# ---------------------------------------------------------------------------
# Errores de etiquetado
# ---------------------------------------------------------------------------
def categoria_lexico(palabra: str) -> str | None:
    """Categoría de la palabra en el léxico de la CFG (det, n, adj, v, ...)."""
    terminal = LEXICON.get(palabra.casefold())
    return terminal.split("_")[0] if terminal else None


def errores_pos(tokens: list[tuple[str, str]], aceptables: dict, coincide) -> list[dict]:
    """Compara la POS de cada palabra del léxico de la CFG con su categoría.

    ``tokens``: pares (texto, etiqueta_pos). ``coincide(etiqueta, aceptables)``
    decide si la etiqueta es compatible.
    """
    errores = []
    for texto, pos in tokens:
        cat = categoria_lexico(texto)
        if cat is None or cat not in aceptables:
            continue
        if not coincide(pos, aceptables[cat]):
            errores.append({
                "palabra": texto,
                "categoria_cfg": cat,
                "pos_herramienta": pos,
                "pos_aceptables": sorted(aceptables[cat]),
            })
    return errores


def errores_roles(obtenido: dict, esperado: dict) -> list[dict] | None:
    """Compara sujeto/verbo/objeto con estructura_esperada. None si no hay referencia."""
    if not esperado:
        return None
    errores = []
    for rol, valor in esperado.items():
        hallado = obtenido.get(rol)
        if (hallado or "").casefold() != valor.casefold():
            errores.append({"rol": rol, "esperado": valor, "obtenido": hallado})
    return errores


# ---------------------------------------------------------------------------
# Decisión y métricas
# ---------------------------------------------------------------------------
def decidir(criterios: dict[str, dict]) -> tuple[str, list[str]]:
    motivos = [f"{c}: {v['detalle']}" for c, v in criterios.items() if v["cumple"] is False]
    return ("RECHAZADA" if motivos else "ACEPTADA"), motivos


def clasificar(esperado: str, decision: str) -> str:
    if decision == "ACEPTADA":
        return "VP" if esperado == "ACEPTADA" else "FP"
    return "VN" if esperado == "RECHAZADA" else "FN"


def _div(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


def resumen(resultados: list[dict]) -> dict:
    """Métricas de referencia. El cálculo oficial lo hace evaluacion/evaluar.py."""
    conteo = {k: 0 for k in ("VP", "VN", "FP", "FN")}
    por_nivel: dict[str, dict[str, int]] = {}
    oraciones_con_error_etiq = 0
    total_errores_etiq = 0
    for r in resultados:
        conteo[r["clasificacion"]] += 1
        nivel = por_nivel.setdefault(str(r["nivel"]), {k: 0 for k in conteo})
        nivel[r["clasificacion"]] += 1
        n = r["errores_etiquetado"]["total"]
        total_errores_etiq += n
        oraciones_con_error_etiq += n > 0
    vp, vn, fp, fn = conteo["VP"], conteo["VN"], conteo["FP"], conteo["FN"]
    return {
        **conteo,
        "precision": _div(vp, vp + fp),
        "recall": _div(vp, vp + fn),
        "rechazo_correcto": _div(vn, vn + fp),
        "exactitud": _div(vp + vn, len(resultados)),
        "errores_etiquetado": total_errores_etiq,
        "oraciones_con_error_etiquetado": oraciones_con_error_etiq,
        "por_nivel": por_nivel,
    }


# ---------------------------------------------------------------------------
# Metadatos y salida
# ---------------------------------------------------------------------------
def version(paquete: str) -> str | None:
    try:
        return metadata.version(paquete)
    except metadata.PackageNotFoundError:
        return None


def _modulo() -> str:
    """'nlp.spacy_comparison' a partir del script en ejecución (sin rutas locales)."""
    return ".".join(Path(relativa(Path(sys.argv[0]))).with_suffix("").parts)


def entorno() -> dict:
    return {
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "comando": " ".join(["python -m", _modulo(), *sys.argv[1:]]),
    }


def relativa(ruta: Path) -> str:
    """Ruta relativa a la raíz del proyecto si está dentro de él (para logs portables)."""
    try:
        return ruta.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(ruta)


def escribir_log(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def imprimir_resumen(nombre: str, res: dict, ruta: Path) -> None:
    pct = lambda v: "n/d" if v is None else f"{v * 100:.1f} %"  # noqa: E731
    print("\n" + "=" * 70)
    print(f" RESUMEN — {nombre}")
    print("=" * 70)
    print(f"  VP={res['VP']}  VN={res['VN']}  FP={res['FP']}  FN={res['FN']}")
    print(f"  Precisión        : {pct(res['precision'])}")
    print(f"  Recall           : {pct(res['recall'])}")
    print(f"  Rechazo correcto : {pct(res['rechazo_correcto'])}")
    print(f"  Errores de etiquetado: {res['errores_etiquetado']} "
          f"(en {res['oraciones_con_error_etiquetado']} oraciones)")
    print(f"\n[+] Log guardado en '{relativa(ruta)}'")
