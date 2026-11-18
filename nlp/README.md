# nlp/ — Herramientas modernas de NLP (Fase 2, Integrante 3)

| Archivo | Qué hace |
|---|---|
| `spacy_comparison.py` | spaCy + `es_core_news_sm`: tokens, POS, morfología, dependencias → `logs/spacy.json` y `nlp/results/arboles_spacy.html` |
| `segunda_herramienta.py` | HuggingFace Transformers, dos modelos BETO (AnCora): POS EAGLES + función sintáctica → `logs/segunda_herramienta.json` |
| `criterios.py` | Metodología común: criterios C1–C4 y tablas relación/función → producción de la CFG |
| `comun.py` | Lectura del corpus, referencia léxica, clasificación VP/VN/FP/FN, escritura del log |

## Ejecución

Desde la raíz del proyecto y con el entorno virtual activo:

```bash
pip install -r requirements.txt
pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu   # torch solo CPU
python -m spacy download es_core_news_sm

python -m nlp.spacy_comparison        # lee corpus/corpus_pruebas.csv
python -m nlp.segunda_herramienta     # la 1.ª vez descarga ~880 MB de modelos
```

Opciones: `--corpus RUTA`, `--salida RUTA` (y `--modelo`, `--html` en spaCy).

## Corpus de entrada

`corpus/corpus_pruebas.csv` (UTF-8). Columnas:

| Columna | Obligatoria | Ejemplo |
|---|---|---|
| `id` | sí | `1` |
| `oracion` | sí | `El niño come pan.` |
| `nivel` | sí | `1`, `2` o `3` |
| `esperado` | sí | `ACEPTADA` / `RECHAZADA` (según la CFG, no según la intuición) |
| `fenomeno` | no | `relativa de sujeto` |
| `estructura_esperada` | no | `sujeto=niño; verbo=come; objeto=pan` (núcleos, separados por `;`) |

Si existe `estructura_esperada`, se cuentan los errores de rol (sujeto, verbo, objeto).

## Esquema de los logs (`logs/spacy.json`, `logs/segunda_herramienta.json`)

Ambos archivos comparten la misma estructura. Cambian solo `tokens` y algunos metadatos.

```jsonc
{
  "herramienta": "spaCy",                       // o "HuggingFace Transformers"
  "version_libreria": "3.8.18",
  "modelo": "es_core_news_sm",                  // HF: {"pos": "...", "sintaxis": "..."}
  "version_modelo": "3.8.0",                    // HF: commit del Hub de cada modelo
  "configuracion": { "pipeline": [...], "dispositivo": "CPU", ... },
  "entorno": { "python": "3.13.13", "plataforma": "...", "comando": "python -m nlp.spacy_comparison" },
  "inicio": "2026-11-18T10:00:00-06:00",
  "fin":    "2026-11-18T10:00:02-06:00",
  "corpus": { "ruta": "corpus/corpus_pruebas.csv", "sha256": "…", "n_oraciones": 40 },
  "metodologia": {
    "version_criterios": "1.0",
    "criterios": { "C1_raiz_verbal": "...", "C2_sujeto_nominal": "...", "C3_concordancia": "...", "C4_alcance_cfg": "..." },
    "regla_decision": "ACEPTADA si C1, C2, C3 y C4 se cumplen; RECHAZADA en otro caso.",
    "relaciones_permitidas": { "nsubj": "Oracion → Sujeto SV .", ... }   // HF: "funciones_permitidas"
  },
  "resultados": [
    {
      "id": "1", "oracion": "El niño come pan.", "nivel": "1", "fenomeno": "...", "esperado": "ACEPTADA",
      "timestamp": "2026-11-18T10:00:00-06:00", "tiempo_ms": 2.1,
      "produjo_analisis": true,
      "tokens": [
        // spaCy:
        { "i": 0, "texto": "El", "lema": "el", "pos": "DET", "tag": "DET",
          "morph": { "Gender": "Masc", "Number": "Sing" }, "dep": "det", "head_i": 1, "head_texto": "niño" }
        // HF:
        // { "i": 0, "texto": "El", "pos": "DA", "conf_pos": 0.9999, "funcion": "_", "conf_funcion": 0.9998 }
      ],
      "arbol": "(ROOT come/VERB (nsubj niño/NOUN (det El/DET)) (obj pan/NOUN) (punct ./PUNCT))",  // solo spaCy
      "roles": { "sujeto": "niño", "verbo": "come", "objeto": "pan" },
      "criterios": {
        "C1_raiz_verbal":    { "cumple": true,  "detalle": "raíz verbal 'come'" },
        "C2_sujeto_nominal": { "cumple": true,  "detalle": "sujeto 'niño'" },
        "C3_concordancia":   { "cumple": true,  "detalle": "…", "no_evaluables": 0 },   // HF: cumple = null
        "C4_alcance_cfg":    { "cumple": false, "detalle": "'pan' con relación 'obj' sin producción en la CFG" }
      },
      "decision": "RECHAZADA",
      "motivos_rechazo": ["C4_alcance_cfg: ..."],
      "clasificacion": "FN",                    // VP | VN | FP | FN frente a "esperado"
      "errores_etiquetado": {
        "pos_vs_lexico_cfg": [ { "palabra": "come", "categoria_cfg": "v", "pos_herramienta": "PROPN", "pos_aceptables": ["AUX","VERB"] } ],
        "roles_vs_estructura_esperada": [ { "rol": "objeto", "esperado": "pan", "obtenido": null } ],  // null si no hay referencia
        "total": 2
      }
    }
  ],
  "resumen": {
    "VP": 0, "VN": 0, "FP": 0, "FN": 0,
    "precision": 0.0, "recall": 0.0, "rechazo_correcto": 0.0, "exactitud": 0.0,
    "errores_etiquetado": 0, "oraciones_con_error_etiquetado": 0,
    "por_nivel": { "1": { "VP": 0, "VN": 0, "FP": 0, "FN": 0 }, "2": {...}, "3": {...} }
  }
}
```

**Para el script de evaluación (Integrante 4):** basta con leer `resultados[].id` y
`resultados[].decision` y cruzarlos con el corpus. `resumen` sirve de comprobación, pero las
métricas oficiales se calculan en `evaluacion/evaluar.py`. Los errores de etiquetado de cada
herramienta están en `resultados[].errores_etiquetado.total`.

## Antes de ejecutar con el corpus final

Las tablas de `criterios.py` reflejan la gramática actual de `espanol/grammar.py`, que **no
tiene objeto directo ni nombres propios**. Si el Integrante 2 amplía la CFG para el corpus,
hay que agregar las relaciones equivalentes (por ejemplo `obj` en spaCy y `CD` nominal en HF)
**antes** de generar los logs y subir `VERSION_CRITERIOS`.
