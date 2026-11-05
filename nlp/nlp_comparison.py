import os
import spacy
from spacy import displacy

def cargar_modelo():
    try:
        nlp = spacy.load("es_core_news_sm")
        return nlp
    except OSError:
        print("[-] El modelo 'es_core_news_sm' no está instalado.")
        print("    Ejecuta en tu terminal: python -m spacy download es_core_news_sm")
        exit(1)

def analizar_oraciones(nlp, oraciones):
    print("=" * 80)
    print(" ANÁLISIS DE ORACIONES CON SPACY (NLP)")
    print("=" * 80)
    
    docs = []
    for idx, oracion in enumerate(oraciones, 1):
        doc = nlp(oracion)
        docs.append(doc)
        print(f"\n[{idx}] Oración: '{oracion}'")
        print("-" * 60)
        print(f"{'Texto':<15} | {'POS':<8} | {'Dependencia':<12} | {'Cabeza (Head)':<15}")
        print("-" * 60)
        for token in doc:
            print(f"{token.text:<15} | {token.pos_:<8} | {token.dep_:<12} | {token.head.text:<15}")
    
    return docs

def exportar_visualizacion(docs):
    # Crear la carpeta nlp/results si no existe
    dir_salida = os.path.join("nlp", "results")
    os.makedirs(dir_salida, exist_ok=True)
    
    html = displacy.render(docs, style="dep", page=True)
    ruta_salida = os.path.join(dir_salida, "arboles_dependencias_nlp.html")
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n[+] Visualización exportada con éxito a '{ruta_salida}'")

if __name__ == "__main__":
    nlp = cargar_modelo()
    
    oraciones_prueba = [
        "El gato negro duerme.",
        "Los perros grandes juegan con la niña.",
        "La gata muy rápida corre rápidamente en el jardín.",
        "El niño que corre juega en la casa.",
        "El niño observa que la gata duerme.",
        "El gato negra duerme.",
        "El gato negro duermen.",
        "Los gatos que corre duermen.",
        "El niño y la niña duermen."
    ]
    
    documentos_procesados = analizar_oraciones(nlp, oraciones_prueba)
    exportar_visualizacion(documentos_procesados)