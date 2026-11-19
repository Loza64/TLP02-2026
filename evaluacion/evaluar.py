"""
Script de evaluacion de la Fase 2 (Actividad 4).

Compara las decisiones de los cinco enfoques con las etiquetas esperadas de
corpus/corpus_pruebas.csv y genera las tablas y graficas a partir de los logs
originales. No contiene ningun resultado escrito a mano: si se vuelve a
ejecutar con los mismos logs produce exactamente los mismos archivos.

    python -m evaluacion.evaluar

Entradas (logs originales de cada enfoque):
    logs/parser_propio.json        parser LL(1) propio
    logs/spacy.json                spaCy
    logs/segunda_herramienta.json  HuggingFace Transformers
    logs/llm_zero_shot.json        Gemini zero-shot (llm/ejecutar_llm.py)
    logs/llm_few_shot.json         Gemini few-shot  (llm/ejecutar_llm.py)

Salidas (evaluacion/):
    resultados.csv            tabla comparativa (metrica x enfoque)
    resultados_por_nivel.csv  VP/VN/FP/FN y errores de etiquetado por nivel
    resultados_por_oracion.csv decision y clasificacion de cada oracion
    cumplimiento_llm.csv      respeto de la CFG por parte del LLM
    resultados.json           todo lo anterior en un unico archivo
    tabla_comparativa.md      tablas listas para el informe
    graficas/*.png            graficas comparativas

Metricas (positivo = ACEPTADA):
    Precision        = VP / (VP + FP)
    Recall           = VP / (VP + FN)
    Rechazo correcto = VN / (VN + FP)
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from espanol.grammar import PRODUCTIONS, TERMINALS
from espanol.lexer import LEXICON

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "corpus" / "corpus_pruebas.csv"
LOGS = ROOT / "logs"
SALIDA = ROOT / "evaluacion"
GRAFICAS = SALIDA / "graficas"

ENFOQUES = [
    ("parser_propio", "Parser propio"),
    ("spacy", "spaCy"),
    ("segunda_herramienta", "HuggingFace"),
    ("llm_zero_shot", "LLM zero-shot"),
    ("llm_few_shot", "LLM few-shot"),
]

DECISIONES = ("ACEPTADA", "RECHAZADA")
CLASES = ("VP", "VN", "FP", "FN")


# ======================================================================
# Corpus y metricas
# ======================================================================

def cargar_corpus():
    with open(CORPUS_PATH, encoding="utf-8-sig", newline="") as archivo:
        corpus = {}
        for fila in csv.DictReader(archivo):
            if fila["esperado"] not in DECISIONES:
                raise ValueError(f"Etiqueta invalida en el corpus: {fila}")
            corpus[int(fila["id"])] = {
                "oracion": fila["oracion"],
                "nivel": int(fila["nivel"]),
                "esperado": fila["esperado"],
                "fenomeno": fila.get("fenomeno", ""),
            }
    return corpus


def clasificar(esperado, obtenido):
    if obtenido not in DECISIONES:
        raise ValueError(f"Decision invalida: {obtenido!r}")
    if esperado == "ACEPTADA":
        return "VP" if obtenido == "ACEPTADA" else "FN"
    return "VN" if obtenido == "RECHAZADA" else "FP"


def razon(numerador, denominador):
    """Porcentaje con 2 decimales; None si el denominador es 0 (N/D)."""
    if denominador == 0:
        return None
    return round(100 * numerador / denominador, 2)


def calcular_metricas(conteo):
    vp, vn, fp, fn = (conteo[c] for c in CLASES)
    return {
        "precision": razon(vp, vp + fp),
        "recall": razon(vp, vp + fn),
        "rechazo_correcto": razon(vn, vn + fp),
        "exactitud": razon(vp + vn, vp + vn + fp + fn),
    }


# ======================================================================
# Arboles en notacion de corchetes (salida del LLM)
# ======================================================================

def parsear_corchetes(texto):
    """
    Convierte arboles en notacion de corchetes o funcional en:
        (etiqueta, [hijos])

    Formatos admitidos:
        [Oracion [Sujeto_sg [SN_m_sg ...]]]
        Oracion(Sujeto_sg(SN_m_sg(det_m_sg(El))))

    Los hijos son tuplas (subarboles) o cadenas (palabras/simbolos).
    Devuelve None si el texto no es un arbol bien formado.
    """
    if not isinstance(texto, str):
        return None

    texto = texto.replace(",", " ")
    tokens = re.findall(r"\[|\]|\(|\)|[^\s\[\]()]+", texto)

    if not tokens:
        return None

    pos = 0

    def parsear_funcional(etiqueta):
        nonlocal pos

        if pos >= len(tokens) or tokens[pos] != "(":
            raise ValueError

        pos += 1
        hijos = []

        while pos < len(tokens) and tokens[pos] != ")":
            if tokens[pos] == "[":
                hijos.append(parsear_bloque())

            elif (
                pos + 1 < len(tokens)
                and tokens[pos + 1] == "("
            ):
                etiqueta_hijo = tokens[pos]
                pos += 1
                hijos.append(parsear_funcional(etiqueta_hijo))

            elif tokens[pos] in ("]", ")"):
                raise ValueError

            else:
                hijos.append(tokens[pos])
                pos += 1

        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError

        pos += 1
        return (etiqueta, hijos)

    def parsear_bloque():
        nonlocal pos

        if pos >= len(tokens) or tokens[pos] != "[":
            raise ValueError

        pos += 1

        if pos >= len(tokens) or tokens[pos] in ("[", "]", "(", ")"):
            raise ValueError

        etiqueta = tokens[pos]
        pos += 1
        hijos = []

        while pos < len(tokens) and tokens[pos] != "]":
            if tokens[pos] == "[":
                hijos.append(parsear_bloque())

            elif (
                pos + 1 < len(tokens)
                and tokens[pos + 1] == "("
            ):
                etiqueta_hijo = tokens[pos]
                pos += 1
                hijos.append(parsear_funcional(etiqueta_hijo))

            elif tokens[pos] in ("(", ")"):
                raise ValueError

            else:
                hijos.append(tokens[pos])
                pos += 1

        if pos >= len(tokens) or tokens[pos] != "]":
            raise ValueError

        pos += 1
        return (etiqueta, hijos)

    try:
        if tokens[0] == "[":
            arbol = parsear_bloque()
        else:
            etiqueta = tokens[pos]
            pos += 1
            arbol = parsear_funcional(etiqueta)

    except (ValueError, IndexError):
        return None

    return arbol if pos == len(tokens) else None


def arbol_desde_parser(nodo):
    """Convierte el arbol JSON del parser propio a (etiqueta, [hijos])."""
    if "palabra" in nodo and not nodo["hijos"]:
        return (nodo["simbolo"], [nodo["palabra"]])
    return (nodo["simbolo"], [arbol_desde_parser(h) for h in nodo["hijos"]])


def normalizar_arbol(arbol):
    """
    Forma canonica para comparar arboles: elimina las producciones vacias
    (ε) y escribe como hoja simple los terminales cuyo nombre es la propia
    palabra ('.', 'que'), que pueden aparecer con o sin envoltorio.
    """
    if isinstance(arbol, str):
        return None if arbol == "ε" else arbol
    etiqueta, hijos = arbol
    if (len(hijos) == 1 and isinstance(hijos[0], str)
            and hijos[0].casefold() == etiqueta):
        return hijos[0]
    nuevos = [n for n in (normalizar_arbol(h) for h in hijos) if n is not None]
    if not nuevos:
        return None
    return (etiqueta, tuple(nuevos))


# ======================================================================
# Errores de etiquetado del LLM
# ======================================================================

def errores_etiquetado_llm(oracion, decision, estructura):
    """
    Mismo criterio que nlp/ (POS frente al lexico de la CFG), aplicado a la
    estructura que devuelve el LLM: cada palabra del lexico debe aparecer
    bajo su categoria terminal. Tipos de error:
      - categoria_incorrecta: la palabra cuelga de otro terminal.
      - sin_categoria: la palabra cuelga directamente de un no terminal.
      - palabra_omitida_o_alterada: la palabra no aparece (o aparece
        escrita de otra forma, p. ej. sin tilde) en la estructura.
    Solo se evalua cuando el LLM acepta la oracion o entrega una estructura.
    """
    """
    Compara las palabras del arbol del LLM con el lexico de la CFG.
    Los arboles no reconocidos no se evalúan para evitar falsos errores.
    """
    arbol = parsear_corchetes(estructura)

    # No evaluar árboles inexistentes o mal formados.
    if arbol is None:
        return []

    hojas = []  # (palabra, etiqueta_padre)

    def recorrer(nodo):
        etiqueta, hijos = nodo
        for h in hijos:
            if isinstance(h, tuple):
                recorrer(h)
            elif h not in ("Îµ", "."):
                hojas.append((h, etiqueta))

    recorrer(arbol)

    errores = []
    restantes = Counter(p.casefold() for p, _ in hojas)

    for palabra, padre in hojas:
        esperado = LEXICON.get(palabra.casefold())

        # 'que' es a la vez palabra y terminal.
        if esperado is None or padre == esperado or esperado == palabra.casefold():
            continue

        tipo = ("categoria_incorrecta" if padre in TERMINALS
                else "sin_categoria")

        errores.append({
            "palabra": palabra,
            "tipo": tipo,
            "etiqueta_llm": padre,
            "categoria_cfg": esperado
        })

    for palabra in re.findall(r"[^\W\d_]+", oracion):
        clave = palabra.casefold()

        if clave not in LEXICON:
            continue

        if restantes[clave] > 0:
            restantes[clave] -= 1
        else:
            errores.append({
                "palabra": palabra,
                "tipo": "palabra_omitida_o_alterada",
                "etiqueta_llm": None,
                "categoria_cfg": LEXICON[clave]
            })

    return errores



def _norm_regla(texto):
    texto = texto.replace("→", "->")
    izq, _, der = texto.partition("->")
    return izq.strip(), " ".join(der.split())


PRODUCCIONES_CFG = {
    (izq, " ".join(der) if der else "ε") for izq, der in PRODUCTIONS
}


def clasificar_regla(texto):
    """'produccion' | 'lexica' | 'inexistente' para una regla citada."""
    izq, der = _norm_regla(texto)
    if (izq, der) in PRODUCCIONES_CFG:
        return "produccion"
    if izq in TERMINALS and LEXICON.get(der.casefold()) == izq:
        return "lexica"
    return "inexistente"


# ======================================================================
# Carga de cada enfoque -> {id: {"decision", "errores_etiquetado", ...}}
# ======================================================================

def _leer_json(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def cargar_parser_propio():
    datos = _leer_json(LOGS / "parser_propio.json")
    info = {"fuente": "logs/parser_propio.json",
            "herramienta": datos["metadatos"]["enfoque"],
            "nota_etiquetado": "0 por construccion: el parser asigna las "
                               "categorias desde el lexico de la CFG, que es "
                               "la referencia."}
    salida = {}
    for r in datos["resultados"]:
        salida[int(r["id"])] = {
            "decision": r["obtenido"],
            "errores_etiquetado": 0,
            "arbol": arbol_desde_parser(r["arbol"]) if r.get("arbol") else None,
        }
    return info, salida


def cargar_nlp(nombre):
    ruta = LOGS / f"{nombre}.json"
    datos = _leer_json(ruta)
    modelo = datos["modelo"]
    if isinstance(modelo, dict):
        modelo = ", ".join(modelo.values())
    info = {"fuente": f"logs/{nombre}.json",
            "herramienta": f"{datos['herramienta']} "
                           f"{datos['version_libreria']} ({modelo})",
            "nota_etiquetado": "POS de la herramienta frente al lexico de la "
                               "CFG (criterio de nlp/comun.py)."}
    salida = {}
    for r in datos["resultados"]:
        salida[int(r["id"])] = {
            "decision": r["decision"],
            "errores_etiquetado": r["errores_etiquetado"]["total"],
        }
    return info, salida


def localizar_log_llm(modo):
    """
    Prefiere el log consolidado logs/llm_<modo>.json (llm/ejecutar_llm.py).
    Si no existe, usa la carpeta de ejecucion mas reciente logs/llm_<modo>_*
    (ejecuciones preliminares) y lo avisa.
    """
    consolidado = LOGS / f"llm_{modo}.json"
    if consolidado.exists():
        datos = _leer_json(consolidado)
        return (f"logs/{consolidado.name}", datos["metadatos"],
                datos["resultados"], True)

    carpetas = sorted(p for p in LOGS.glob(f"llm_{modo}_*") if p.is_dir())
    if not carpetas:
        raise FileNotFoundError(
            f"No hay resultados del LLM {modo}. "
            "Ejecuta: python -m llm.ejecutar_llm ambos")
    carpeta = carpetas[-1]  # el nombre incluye AAAAMMDD_HHMMSS
    meta = _leer_json(carpeta / "metadatos.json")
    resultados = _leer_json(carpeta / "resultados.json")["resultados"]
    return (carpeta.relative_to(ROOT).as_posix(), meta, resultados, False)


def cargar_llm(modo):
    fuente, meta, resultados, consolidado = localizar_log_llm(modo)
    if not consolidado:
        print(f"[aviso] logs/llm_{modo}.json no existe; se usa la ejecucion "
              f"preliminar {fuente} (sin timestamp por llamada).",
              file=sys.stderr)
    info = {"fuente": fuente,
            "herramienta": f"Google Gemini ({meta['modelo']}, "
                           f"temperatura {meta.get('temperatura', meta.get('parametros', {}).get('temperature'))})",
            "nota_etiquetado": "Categoria de cada palabra en la estructura "
                               "devuelta frente al lexico de la CFG."}
    salida = {}
    for r in resultados:
        identificador = int(r["id"])
        if identificador in salida:
            raise ValueError(f"ID duplicado en {fuente}: {identificador}")
        arbol = parsear_corchetes(r.get("estructura"))

        errores = errores_etiquetado_llm(
            r["oracion"],
            r["decision"],
            r.get("estructura")
        )

        arbol_mal_formado = (
            r["decision"] == "ACEPTADA"
            and bool(r.get("estructura"))
            and arbol is None
        )
        reglas = r.get("producciones_aplicadas") or []
        clases = [clasificar_regla(x) for x in reglas]
        salida[identificador] = {
            "decision": r["decision"],
            "errores_etiquetado": len(errores),
            "detalle_etiquetado": errores,
            "reglas_citadas": len(reglas),
            "reglas_inexistentes": [x for x, c in zip(reglas, clases)
                                    if c == "inexistente"],
            "arbol": arbol,
            "arbol_mal_formado": arbol_mal_formado,
        }
    return info, salida


def cargar_enfoques():
    return {
        "parser_propio": cargar_parser_propio(),
        "spacy": cargar_nlp("spacy"),
        "segunda_herramienta": cargar_nlp("segunda_herramienta"),
        "llm_zero_shot": cargar_llm("zero_shot"),
        "llm_few_shot": cargar_llm("few_shot"),
    }


# ======================================================================
# Evaluacion
# ======================================================================

def evaluar(corpus, enfoques):
    por_oracion = {i: dict(corpus[i]) for i in corpus}
    resumen = {}

    for clave, (info, preds) in enfoques.items():
        if set(preds) != set(corpus):
            faltan = sorted(set(corpus) - set(preds))
            sobran = sorted(set(preds) - set(corpus))
            raise ValueError(f"{clave}: IDs no coinciden con el corpus "
                             f"(faltan {faltan}, sobran {sobran})")

        conteo = Counter({c: 0 for c in CLASES})
        niveles = {}
        etiquetado = 0
        oraciones_con_error = 0

        for i, fila in corpus.items():
            p = preds[i]
            clase = clasificar(fila["esperado"], p["decision"])
            conteo[clase] += 1
            etiquetado += p["errores_etiquetado"]
            oraciones_con_error += p["errores_etiquetado"] > 0

            nivel = niveles.setdefault(fila["nivel"], {
                **{c: 0 for c in CLASES}, "errores_etiquetado": 0})
            nivel[clase] += 1
            nivel["errores_etiquetado"] += p["errores_etiquetado"]

            por_oracion[i][f"{clave}_decision"] = p["decision"]
            por_oracion[i][f"{clave}_clase"] = clase
            por_oracion[i][f"{clave}_errores_etiquetado"] = p["errores_etiquetado"]

        for nivel in niveles.values():
            nivel.update(calcular_metricas(nivel))

        resumen[clave] = {
            **info,
            **{c: conteo[c] for c in CLASES},
            **calcular_metricas(conteo),
            "errores_etiquetado": etiquetado,
            "oraciones_con_error_etiquetado": oraciones_con_error,
            "por_nivel": {str(n): niveles[n] for n in sorted(niveles)},
        }

    return resumen, por_oracion



def cumplimiento_llm(corpus, enfoques):
    """Respeto de la CFG por el LLM: reglas inventadas y arboles."""
    _, parser = enfoques["parser_propio"]
    filas, resumen = [], {}

    for clave in ("llm_zero_shot", "llm_few_shot"):
        _, preds = enfoques[clave]

        citadas = inexistentes = 0
        aceptados = mal_formados = reconocidos = 0
        comparables = identicos = 0

        tipos = Counter()

        for i in sorted(corpus):
            p = preds[i]
            ref = parser[i]["arbol"]

            coincide = None

            es_aceptada = p["decision"] == "ACEPTADA"
            arbol = p["arbol"]
            arbol_mal_formado = p.get("arbol_mal_formado", False)

            if es_aceptada:
                aceptados += 1

                if arbol_mal_formado:
                    mal_formados += 1
                elif arbol is not None:
                    reconocidos += 1

            # Comparar solamente árboles aceptados y reconocidos.
            if es_aceptada and arbol is not None and ref is not None:
                comparables += 1

                coincide = (
                    normalizar_arbol(arbol)
                    == normalizar_arbol(ref)
                )

                if coincide:
                    identicos += 1

            citadas += p["reglas_citadas"]
            inexistentes += len(p["reglas_inexistentes"])

            tipos.update(
                e["tipo"] for e in p["detalle_etiquetado"]
            )

            filas.append({
                "modo": clave.replace("llm_", "").replace("_", "-"),
                "id": i,
                "oracion": corpus[i]["oracion"],
                "esperado": corpus[i]["esperado"],
                "decision": p["decision"],
                "reglas_citadas": p["reglas_citadas"],
                "reglas_inexistentes": len(p["reglas_inexistentes"]),
                "detalle_reglas_inexistentes": " | ".join(
                    p["reglas_inexistentes"]
                ),
                "errores_etiquetado": p["errores_etiquetado"],
                "detalle_etiquetado": " | ".join(
                    f"{e['palabra']}:{e['tipo']}"
                    for e in p["detalle_etiquetado"]
                ),
                "arbol_mal_formado": arbol_mal_formado,
                "arbol_reconocido": arbol is not None,
                "arbol_igual_al_parser": (
                    "" if coincide is None else coincide
                ),
            })

        resumen[clave] = {
            "reglas_citadas": citadas,
            "reglas_inexistentes": inexistentes,
            "arboles_aceptados": aceptados,
            "arboles_mal_formados": mal_formados,
            "arboles_reconocidos": reconocidos,
            "arboles_comparables": comparables,
            "arboles_identicos_al_parser": identicos,
            "porcentaje_arboles_identicos": (
                round(identicos / comparables * 100, 2)
                if comparables else 0
            ),
            "errores_etiquetado_por_tipo": dict(
                sorted(tipos.items())
            ),
        }

    return resumen, filas



# ======================================================================
# Escritura de tablas
# ======================================================================

FILAS_TABLA = [
    ("Precisión (%)", "precision"),
    ("Recall (%)", "recall"),
    ("Rechazo correcto (%)", "rechazo_correcto"),
    ("VP", "VP"),
    ("VN", "VN"),
    ("FP", "FP"),
    ("FN", "FN"),
    ("Errores de etiquetado", "errores_etiquetado"),
    ("Exactitud (%)", "exactitud"),
]


def fmt(valor):
    if valor is None:
        return "N/D"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


def escribir_csv(ruta, campos, filas):
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos,
                                  lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def escribir_tablas(resumen, por_oracion, cumplimiento, filas_cumpl):
    nombres = dict(ENFOQUES)

    escribir_csv(
        SALIDA / "resultados.csv",
        ["metrica"] + [nombres[c] for c, _ in ENFOQUES],
        [{"metrica": etiqueta,
          **{nombres[c]: fmt(resumen[c][k]) for c, _ in ENFOQUES}}
         for etiqueta, k in FILAS_TABLA],
    )

    filas_nivel = []
    for c, nombre in ENFOQUES:
        for nivel, v in resumen[c]["por_nivel"].items():
            filas_nivel.append({
                "enfoque": nombre, "nivel": nivel,
                **{k: v[k] for k in CLASES},
                "errores_clasificacion": v["FP"] + v["FN"],
                "errores_etiquetado": v["errores_etiquetado"],
                "exactitud": fmt(v["exactitud"]),
            })
    escribir_csv(SALIDA / "resultados_por_nivel.csv",
                 list(filas_nivel[0].keys()), filas_nivel)

    campos = ["id", "nivel", "fenomeno", "oracion", "esperado"]
    for c, _ in ENFOQUES:
        campos += [f"{c}_decision", f"{c}_clase", f"{c}_errores_etiquetado"]
    escribir_csv(SALIDA / "resultados_por_oracion.csv", campos,
                 [{"id": i, **por_oracion[i]} for i in sorted(por_oracion)])

    escribir_csv(SALIDA / "cumplimiento_llm.csv",
                 list(filas_cumpl[0].keys()), filas_cumpl)

    with open(SALIDA / "resultados.json", "w", encoding="utf-8") as archivo:
        json.dump({
            "corpus": "corpus/corpus_pruebas.csv",
            "positivo": "ACEPTADA",
            "formulas": {
                "precision": "VP / (VP + FP)",
                "recall": "VP / (VP + FN)",
                "rechazo_correcto": "VN / (VN + FP)",
                "exactitud": "(VP + VN) / total",
            },
            "enfoques": resumen,
            "cumplimiento_llm": cumplimiento,
        }, archivo, ensure_ascii=False, indent=2)

    escribir_markdown(resumen, cumplimiento)


def escribir_markdown(resumen, cumplimiento):
    nombres = [n for _, n in ENFOQUES]
    claves = [c for c, _ in ENFOQUES]
    lineas = [
        "# Resultados cuantitativos (generado por `evaluacion/evaluar.py`)",
        "",
        "> Archivo generado automáticamente a partir de los logs. No editar a mano.",
        "",
        "## Tabla comparativa",
        "",
        "| Métrica | " + " | ".join(nombres) + " |",
        "|---|" + "---:|" * len(nombres),
    ]
    for etiqueta, k in FILAS_TABLA:
        lineas.append(f"| {etiqueta} | "
                      + " | ".join(fmt(resumen[c][k]) for c in claves) + " |")

    lineas += ["", "## Errores de clasificación (FP + FN) por nivel", "",
               "| Nivel | " + " | ".join(nombres) + " |",
               "|---|" + "---:|" * len(nombres)]
    for nivel in ("1", "2", "3"):
        celdas = []
        for c in claves:
            v = resumen[c]["por_nivel"][nivel]
            celdas.append(f"{v['FP'] + v['FN']} (FP {v['FP']}, FN {v['FN']})")
        lineas.append(f"| {nivel} | " + " | ".join(celdas) + " |")

    lineas += ["", "## Cumplimiento de la CFG por el LLM", "",
               "| Indicador | LLM zero-shot | LLM few-shot |",
               "|---|---:|---:|"]

    z = cumplimiento["llm_zero_shot"]
    f = cumplimiento["llm_few_shot"]

    lineas += [
        f"| Reglas citadas | {z['reglas_citadas']} | {f['reglas_citadas']} |",
        f"| Reglas inexistentes en la CFG | {z['reglas_inexistentes']} "
        f"| {f['reglas_inexistentes']} |",
        f"| Árboles generados para oraciones aceptadas | "
        f"{z['arboles_aceptados']} | {f['arboles_aceptados']} |",
        f"| Árboles reconocidos | "
        f"{z['arboles_reconocidos']} | {f['arboles_reconocidos']} |",
        f"| Árboles mal formados | "
        f"{z['arboles_mal_formados']} | {f['arboles_mal_formados']} |",
        f"| Árboles idénticos al del parser propio | "
        f"{z['arboles_identicos_al_parser']}/{z['arboles_comparables']} | "
        f"{f['arboles_identicos_al_parser']}/{f['arboles_comparables']} |",
        f"| Coincidencia estructural (%) | "
        f"{z['porcentaje_arboles_identicos']:.2f}% | "
        f"{f['porcentaje_arboles_identicos']:.2f}% |",
        f"| Errores de etiquetado | "
        f"{resumen['llm_zero_shot']['errores_etiquetado']} | "
        f"{resumen['llm_few_shot']['errores_etiquetado']} |",
    ]

    lineas += ["", "## Fuentes", ""]
    for c, n in ENFOQUES:
        lineas.append(f"- **{n}**: {resumen[c]['herramienta']} — "
                      f"`{resumen[c]['fuente']}`. Etiquetado: "
                      f"{resumen[c]['nota_etiquetado']}")
    lineas += ["", "N/D: la métrica no se puede calcular porque su "
               "denominador es 0.", ""]

    (SALIDA / "tabla_comparativa.md").write_text("\n".join(lineas),
                                                 encoding="utf-8")


# ======================================================================
# Graficas
# ======================================================================

# Paleta categórica de referencia (slots 1-3, validados en todos los pares)
SERIE = ["#2a78d6", "#eb6834", "#1baf7a"]
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"
FONDO = "#fcfcfb"
NIVELES = ["#9ec5f4", "#4a90e2", "#1f5aa6"]  # secuencial: azul claro -> oscuro


def _estilo(plt):
    plt.rcParams.update({
        "figure.facecolor": FONDO, "axes.facecolor": FONDO,
        "axes.edgecolor": REJILLA, "axes.labelcolor": TINTA_2,
        "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "text.color": TINTA, "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "svg.hashsalt": "tlp02",
    })


def _barras_agrupadas(ax, categorias, series, etiquetas, colores, sufijo=""):
    import numpy as np
    x = np.arange(len(categorias))
    n = len(series)
    ancho = 0.8 / n
    for k, (valores, etiqueta, color) in enumerate(zip(series, etiquetas, colores)):
        pos = x + (k - (n - 1) / 2) * ancho
        alturas = [0 if v is None else v for v in valores]
        barras = ax.bar(pos, alturas, ancho * 0.92, label=etiqueta,
                        color=color, edgecolor=FONDO, linewidth=1, zorder=3)
        for b, v in zip(barras, valores):
            texto = "N/D" if v is None else (f"{v:g}{sufijo}")
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    texto, ha="center", va="bottom", fontsize=7.5,
                    color=TINTA_2)
    ax.set_xticks(x, categorias)
    ax.yaxis.grid(True, color=REJILLA, linewidth=0.8, zorder=0)
    ax.legend(frameon=False, ncols=n, loc="upper center",
              bbox_to_anchor=(0.5, -0.08))


def generar_graficas(resumen):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _estilo(plt)
    GRAFICAS.mkdir(parents=True, exist_ok=True)
    claves = [c for c, _ in ENFOQUES]
    nombres = [n for _, n in ENFOQUES]
    meta = {"Software": None}

    # 1. Precision, recall y rechazo correcto
    fig, ax = plt.subplots(figsize=(10, 5.2))
    _barras_agrupadas(
        ax, nombres,
        [[resumen[c][m] for c in claves]
         for m in ("precision", "recall", "rechazo_correcto")],
        ["Precisión", "Recall", "Rechazo correcto"], SERIE)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Porcentaje (%)")
    ax.set_title("Precisión, recall y rechazo correcto por enfoque",
                 loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(GRAFICAS / "metricas_comparativas.png", dpi=200, metadata=meta)
    plt.close(fig)

    # 2. FP, FN y errores de etiquetado
    fig, ax = plt.subplots(figsize=(10, 5.2))
    series = [[resumen[c][m] for c in claves]
              for m in ("FP", "FN", "errores_etiquetado")]
    _barras_agrupadas(ax, nombres, series,
                      ["Falsos positivos (FP)", "Falsos negativos (FN)",
                       "Errores de etiquetado"], SERIE)
    tope = max(max(s) for s in series)
    ax.set_ylim(0, max(1, tope) * 1.15 + 0.5)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_ylabel("Cantidad")
    ax.set_title("Errores por enfoque", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(GRAFICAS / "errores_comparativos.png", dpi=200, metadata=meta)
    plt.close(fig)

    # 3. Errores de clasificacion (FP + FN) por nivel de complejidad
    fig, ax = plt.subplots(figsize=(10, 5.2))
    series = [[resumen[c]["por_nivel"][n]["FP"] + resumen[c]["por_nivel"][n]["FN"]
               for c in claves] for n in ("1", "2", "3")]
    _barras_agrupadas(ax, nombres, series,
                      ["Nivel 1 (simples)", "Nivel 2 (intermedias)",
                       "Nivel 3 (complejas)"], NIVELES)
    tope = max(max(s) for s in series)
    ax.set_ylim(0, max(1, tope) * 1.15 + 0.5)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_ylabel("Errores de clasificación (FP + FN)")
    ax.set_title("Errores de clasificación por nivel de complejidad",
                 loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(GRAFICAS / "errores_por_nivel.png", dpi=200, metadata=meta)
    plt.close(fig)


# ======================================================================

def imprimir(resumen, cumplimiento):
    claves = [c for c, _ in ENFOQUES]
    ancho = 15
    print("\n" + "Métrica".ljust(24) + "".join(n.rjust(ancho) for _, n in ENFOQUES))
    for etiqueta, k in FILAS_TABLA:
        print(etiqueta.ljust(24)
              + "".join(fmt(resumen[c][k]).rjust(ancho) for c in claves))
    for c in ("llm_zero_shot", "llm_few_shot"):
        v = cumplimiento[c]
        print(f"\n{c}: reglas inexistentes {v['reglas_inexistentes']}/"
              f"{v['reglas_citadas']}, árboles idénticos al parser "
              f"{v['arboles_identicos_al_parser']}/{v['arboles_comparables']}")


def main():
    corpus = cargar_corpus()
    enfoques = cargar_enfoques()
    resumen, por_oracion = evaluar(corpus, enfoques)
    cumplimiento, filas_cumpl = cumplimiento_llm(corpus, enfoques)

    SALIDA.mkdir(exist_ok=True)
    escribir_tablas(resumen, por_oracion, cumplimiento, filas_cumpl)
    generar_graficas(resumen)
    imprimir(resumen, cumplimiento)
    print("\nArchivos generados en evaluacion/ y evaluacion/graficas/")


if __name__ == "__main__":
    main()
