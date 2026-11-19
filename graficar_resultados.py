import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

# Directorio de salida
ROOT = Path(__file__).resolve().parent
FIGURAS = ROOT / "figuras"
FIGURAS.mkdir(exist_ok=True)

# Resultados de la evaluación
herramientas = [
    "Parser LL(1)",
    "Gemini Zero-Shot",
    "Gemini Few-Shot",
    "spaCy",
    "HuggingFace"
]

exactitud = [100, 100, 100, 80, 82.5]
precision = [100, 100, 100, 88.46, 80]
recall = [100, 100, 100, 82.14, 100]
especificidad = [100, 100, 100, 75, 41.67]
f1_score = [100, 100, 100, 85.19, 88.89]

vp = [28, 28, 28, 23, 28]
vn = [12, 12, 12, 9, 5]
fp = [0, 0, 0, 3, 7]
fn = [0, 0, 0, 5, 0]


def guardar_grafica(nombre):
    plt.tight_layout()
    plt.savefig(FIGURAS / nombre, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Gráfica guardada: figuras/{nombre}")


# ----------------------------------
# 1. Comparación de exactitud
# ----------------------------------

plt.figure(figsize=(10, 6))

barras = plt.bar(herramientas, exactitud)

plt.title("Comparación de exactitud por herramienta")
plt.xlabel("Herramienta")
plt.ylabel("Exactitud (%)")
plt.ylim(0, 110)
plt.xticks(rotation=15, ha="right")
plt.grid(axis="y", alpha=0.3)

for barra, valor in zip(barras, exactitud):
    plt.text(
        barra.get_x() + barra.get_width() / 2,
        barra.get_height() + 1,
        f"{valor}%",
        ha="center"
    )

guardar_grafica("comparacion_exactitud.png")


# ----------------------------------
# 2. Comparación de métricas
# ----------------------------------

metricas = {
    "Precisión": precision,
    "Recall": recall,
    "Especificidad": especificidad,
    "F1-score": f1_score
}

x = np.arange(len(herramientas))
ancho = 0.2

plt.figure(figsize=(12, 6))

for i, (nombre, valores) in enumerate(metricas.items()):
    desplazamiento = (i - 1.5) * ancho

    barras = plt.bar(
        x + desplazamiento,
        valores,
        ancho,
        label=nombre
    )

    for barra, valor in zip(barras, valores):
        plt.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + 1,
            f"{valor:.1f}",
            ha="center",
            fontsize=7
        )

plt.title("Comparación de métricas de evaluación")
plt.xlabel("Herramienta")
plt.ylabel("Porcentaje (%)")
plt.xticks(x, herramientas, rotation=15, ha="right")
plt.ylim(0, 115)
plt.legend()
plt.grid(axis="y", alpha=0.3)

guardar_grafica("comparacion_metricas.png")


# ----------------------------------
# 3. Comparación de errores
# ----------------------------------

x = np.arange(len(herramientas))
ancho = 0.35

plt.figure(figsize=(10, 6))

barras_fp = plt.bar(
    x - ancho / 2,
    fp,
    ancho,
    label="Falsos positivos (FP)"
)

barras_fn = plt.bar(
    x + ancho / 2,
    fn,
    ancho,
    label="Falsos negativos (FN)"
)

plt.title("Comparación de errores de clasificación")
plt.xlabel("Herramienta")
plt.ylabel("Cantidad de errores")
plt.xticks(x, herramientas, rotation=15, ha="right")
plt.ylim(0, 10)
plt.legend()
plt.grid(axis="y", alpha=0.3)

for barras in [barras_fp, barras_fn]:
    for barra in barras:
        plt.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + 0.15,
            str(int(barra.get_height())),
            ha="center"
        )

guardar_grafica("errores_clasificacion.png")


print("\nGeneración de gráficas finalizada.")
