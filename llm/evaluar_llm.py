
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
CORPUS_PATH = ROOT / "corpus" / "corpus_pruebas.csv"
LOGS_PATH = ROOT / "logs"


def porcentaje(valor):
    return round(valor * 100, 2)


def division_segura(numerador, denominador):
    return numerador / denominador if denominador else 0


def evaluar(tipo):
    carpetas = sorted(
        LOGS_PATH.glob(f"llm_{tipo.replace('-', '_')}_*"),
        key=lambda ruta: ruta.stat().st_mtime,
        reverse=True
    )

    if not carpetas:
        raise FileNotFoundError(
            f"No se encontró una ejecución {tipo}."
        )

    carpeta = carpetas[0]
    resultados_path = carpeta / "resultados.json"

    if not resultados_path.exists():
        raise FileNotFoundError("No existe resultados.json.")

    # Cargar corpus esperado
    with open(CORPUS_PATH, "r", encoding="utf-8-sig") as archivo:
        corpus = {
            int(fila["id"]): fila
            for fila in csv.DictReader(archivo)
        }

    # Cargar respuestas Gemini
    with open(resultados_path, "r", encoding="utf-8") as archivo:
        resultados = json.load(archivo)["resultados"]

    predicciones = {}

    for resultado in resultados:
        identificador = int(resultado["id"])

        if identificador in predicciones:
            raise ValueError(f"ID duplicado: {identificador}")

        predicciones[identificador] = resultado["decision"]

    if set(predicciones) != set(corpus):
        raise ValueError(
            "Los IDs de Gemini no coinciden con los del corpus."
        )

    # Inicializar métricas
    VP = VN = FP = FN = 0

    por_nivel = defaultdict(lambda: {
        "VP": 0,
        "VN": 0,
        "FP": 0,
        "FN": 0
    })

    detalles = []

    for identificador, fila in corpus.items():
        esperado = fila["esperado"]
        predicho = predicciones[identificador]
        nivel = int(fila["nivel"])

        if esperado not in ("ACEPTADA", "RECHAZADA"):
            raise ValueError(
                f"Etiqueta esperada inválida para ID {identificador}."
            )

        if predicho not in ("ACEPTADA", "RECHAZADA"):
            raise ValueError(
                f"Decisión inválida de Gemini para ID "
                f"{identificador}: {predicho}"
            )

        # Clasificar resultado
        if esperado == "ACEPTADA" and predicho == "ACEPTADA":
            categoria = "VP"
        elif esperado == "RECHAZADA" and predicho == "RECHAZADA":
            categoria = "VN"
        elif esperado == "RECHAZADA" and predicho == "ACEPTADA":
            categoria = "FP"
        else:
            categoria = "FN"

        if categoria == "VP":
            VP += 1
        elif categoria == "VN":
            VN += 1
        elif categoria == "FP":
            FP += 1
        else:
            FN += 1

        por_nivel[nivel][categoria] += 1

        detalles.append({
            "id": identificador,
            "oracion": fila["oracion"],
            "nivel": nivel,
            "esperado": esperado,
            "predicho": predicho,
            "categoria": categoria,
            "correcto": esperado == predicho
        })

    # Calcular métricas generales
    total = VP + VN + FP + FN

    exactitud = division_segura(VP + VN, total)
    precision = division_segura(VP, VP + FP)
    recall = division_segura(VP, VP + FN)
    especificidad = division_segura(VN, VN + FP)

    f1 = division_segura(
        2 * precision * recall,
        precision + recall
    )

    metricas = {
        "modelo": "gemini-3.5-flash-lite",
        "tipo_prompt": tipo,
        "total": total,
        "VP": VP,
        "VN": VN,
        "FP": FP,
        "FN": FN,
        "exactitud": porcentaje(exactitud),
        "precision": porcentaje(precision),
        "recall": porcentaje(recall),
        "especificidad": porcentaje(especificidad),
        "f1_score": porcentaje(f1),
        "por_nivel": {}
    }

    # Calcular métricas por nivel
    for nivel, valores in sorted(por_nivel.items()):
        cantidad = sum(valores.values())
        correctos = valores["VP"] + valores["VN"]

        metricas["por_nivel"][str(nivel)] = {
            **valores,
            "total": cantidad,
            "correctos": correctos,
            "exactitud": porcentaje(
                division_segura(correctos, cantidad)
            )
        }

    # Guardar métricas
    with open(
        carpeta / "metricas.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            metricas,
            archivo,
            ensure_ascii=False,
            indent=2
        )

    # Guardar detalle de clasificación
    with open(
        carpeta / "detalle_evaluacion.csv",
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:
        campos = [
            "id",
            "oracion",
            "nivel",
            "esperado",
            "predicho",
            "categoria",
            "correcto"
        ]

        escritor = csv.DictWriter(
            archivo,
            fieldnames=campos
        )

        escritor.writeheader()
        escritor.writerows(detalles)

    # Mostrar resultados
    print(f"\n========== GEMINI {tipo.upper()} ==========")
    print(f"Modelo: {metricas['modelo']}")
    print(f"Total: {total}")
    print(f"VP: {VP} | VN: {VN} | FP: {FP} | FN: {FN}")
    print("--------------------------------------")
    print(f"Exactitud:     {metricas['exactitud']}%")
    print(f"Precision:     {metricas['precision']}%")
    print(f"Recall:        {metricas['recall']}%")
    print(f"Especificidad: {metricas['especificidad']}%")
    print(f"F1-score:      {metricas['f1_score']}%")

    print("\n========== RESULTADOS POR NIVEL ==========")

    for nivel, valores in metricas["por_nivel"].items():
        print(
            f"Nivel {nivel}: {valores['correctos']}/"
            f"{valores['total']} ({valores['exactitud']}%)"
        )

    print("\nArchivos generados:")
    print(carpeta / "metricas.json")
    print(carpeta / "detalle_evaluacion.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluar resultados de Gemini Zero-Shot o Few-Shot."
    )

    parser.add_argument(
        "tipo",
        choices=["zero-shot", "few-shot"],
        help="Tipo de experimento que se desea evaluar."
    )

    args = parser.parse_args()

    evaluar(args.tipo)
