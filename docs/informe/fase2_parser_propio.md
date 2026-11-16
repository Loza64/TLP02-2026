# Parser propio: funcionamiento y resultados (Fase 2)

## 1. Resumen del parser y de la gramática

El parser propio es el analizador sintáctico **LL(1) dirigido por tabla** desarrollado en la Fase 1. No se reescribió: se reutilizó el mismo motor (`parser/ll1.py`), que calcula los conjuntos FIRST y FOLLOW y la tabla predictiva a partir de la lista de producciones, y el mismo algoritmo de análisis con pila (`espanol/parser.py`).

La gramática del español (`espanol/grammar.py`) es una gramática libre de contexto con símbolo inicial `Oracion`:

| Elemento | Valor |
|---|---|
| Producciones | 48 |
| No terminales | 24 |
| Terminales | 22 |
| Celdas activas de la tabla LL(1) | 77 |
| Conflictos LL(1) | 0 |
| Léxico (`espanol/lexer.py`) | 55 entradas (49 palabras; 6 son variantes sin tilde) |

**Cómo se codifica la concordancia.** Una CFG no tiene atributos de género y número, así que se incorporan en los nombres de los símbolos. El lexer traduce cada palabra a un terminal que ya trae sus rasgos (`el` → `det_m_sg`, `negras` → `adj_f_pl`, `duermen` → `v_pl`). La gramática tiene una versión de cada sintagma por combinación de rasgos (`SN_m_sg`, `SN_f_sg`, `SN_m_pl`, `SN_f_pl`), y la oración se divide en `Oracion → Sujeto_sg SV_sg . | Sujeto_pl SV_pl .`. Como FIRST(Sujeto_sg) = {det_m_sg, det_f_sg} y FIRST(Sujeto_pl) = {det_m_pl, det_f_pl} son disjuntos, el número del verbo se decide con el primer determinante y desde ahí la pila exige un verbo concordante.

**Estructuras admitidas.** Sintagma nominal con determinante obligatorio, sustantivo y adjetivo opcional (flexionado o invariable, con intensificador *muy* opcional); verbo intransitivo en presente; adverbio de modo opcional; un sintagma preposicional opcional (*en*, *con*, *bajo*); relativa de sujeto (*el niño que corre juega*) y completiva (*observa que la gata duerme*).

**Fuera de alcance por diseño.** Coordinación (*y*), objetos directos, nombres propios, tiempos distintos del presente, más de un sintagma preposicional y cualquier palabra fuera del léxico.

### Ajustes realizados para la Fase 2

1. **Reporte de conflictos determinista.** `build_table` recorría un conjunto de Python, cuyo orden cambia entre ejecuciones; el conflicto de la coordinación se reportaba a veces en `M[Oracion, det_m_sg]` y a veces en `M[Oracion, det_f_sg]`. Ahora recorre los terminales en un orden fijo, de modo que la salida es reproducible.
2. **Contexto del error.** El `ParseError` del español conserva el token encontrado, el símbolo en el tope de la pila, los terminales esperados y el árbol parcial. Con esto se identifica la regla que provoca cada rechazo.
3. **Ejecución del corpus** (`python -m espanol.ejecutar_corpus`). Procesa las 40 oraciones y guarda `logs/parser_propio.json`, `logs/parser_propio.txt` y `logs/parser_propio_resultados.csv`.
4. **Visualización** (`python -m espanol.visualizacion_arboles`). Dibuja en SVG el árbol de cada oración aceptada, con una galería `logs/arboles/index.html` y una versión para LaTeX (`arboles_forest.tex`).
5. **Pruebas** (`tests/test_corpus.py`). Diez pruebas nuevas verifican las etiquetas, la clasificación de motivos, las métricas y la generación de archivos. El proyecto pasa de 31 a 41 pruebas, todas correctas.

## 2. Metodología

- **Entrada:** `corpus/corpus_pruebas.csv` (40 oraciones: 12 de nivel 1, 16 de nivel 2 y 12 de nivel 3).
- **Decisión:** el parser emite una decisión explícita. **ACEPTADA** si construye el árbol completo y llega al estado `$ / $`; **RECHAZADA** si falla el lexer (palabra desconocida) o el análisis predictivo (celda vacía o terminal que no coincide). Para las métricas, la clase positiva es ACEPTADA.
- **Evidencia por oración:** tokens con su terminal, producciones aplicadas (derivación por la izquierda), traza completa de la pila, árbol (estructura anidada y notación con paréntesis), tiempo de análisis y, si se rechaza, el motivo clasificado, la regla de la gramática que lo decide y el mensaje original del parser.
- **Clasificación de los rechazos:** se compara el terminal encontrado con los esperados. Si son de la misma categoría (por ejemplo, dos adjetivos) y difieren en género o número, es una *discordancia*. La conjunción *y* se clasifica como *coordinación no contemplada*. El fin de la oración antes de tiempo, como *estructura incompleta*. Un error del lexer, como *palabra fuera del léxico*.
- **Entorno de la ejecución registrada:** Python 3.10.12, commit `6ab8432`, corpus con SHA-256 `8e9ec84c5ccb235e…`, fecha 2026-11-16 05:38 UTC. Todo queda guardado en los metadatos del log.

## 3. Resultados

### 3.1 Resultado global

| Métrica | Valor |
|---|---|
| Oraciones | 40 |
| Aceptadas / rechazadas | 28 / 12 |
| VP / VN / FP / FN | 28 / 12 / 0 / 0 |
| Precisión | 1,00 |
| Recall | 1,00 |
| Rechazo correcto | 1,00 |
| Coincidencia con la etiqueta esperada | 40 / 40 |

### 3.2 Por nivel

| Nivel | Oraciones | Aceptadas | Rechazadas | Coinciden |
|---|---|---|---|---|
| 1 (simples) | 12 | 12 | 0 | 12 |
| 2 (intermedias) | 16 | 16 | 0 | 16 |
| 3 (complejas) | 12 | 0 | 12 | 12 |

### 3.3 Motivos de rechazo

| Motivo | Cantidad | IDs | Regla que lo decide (ejemplo) |
|---|---|---|---|
| Discordancia de número | 3 | 31, 32, 33 | `Oracion → Sujeto_sg SV_sg .` (32); `SubOpt_pl → que SV_pl` (33) |
| Discordancia de género | 2 | 29, 34 | `SN_m_sg → det_m_sg n_m_sg ModNom_m_sg` (29) |
| Discordancia de género y número | 1 | 40 | `ModNom_m_sg → adv_intens Adj_m_sg` |
| Coordinación no contemplada | 2 | 30, 39 | sin regla para `conj`; agregarla produce conflicto en `M[Oracion, det_m_sg]` |
| Estructura incompleta | 2 | 37, 38 | `SPOpt → prep SN_Prep` (37); `RestoSV → que Clausula` (38) |
| Falta de determinante | 1 | 36 | `Oracion` exige un determinante como primer token |
| Palabra fuera del léxico | 1 | 35 | error léxico: *elefante* |

Ejemplo del log (`logs/parser_propio.txt`):

```
ID: 33    Nivel: 3    Fenómeno: discordancia_numero_en_relativa
Oración:    Los gatos que corre duermen.
Resultado:  RECHAZADA   (esperado RECHAZADA: coincide)
Motivo:     [discordancia_numero] Discordancia de número entre el sujeto y el verbo dentro de
            la oración relativa: se encontró 'corre' (verbo singular) y la regla
            SubOpt_pl → que SV_pl exige verbo plural.
```

### 3.4 Árboles

Se generaron 28 árboles, uno por cada oración aceptada (`logs/arboles/arbol_01.svg` a `arbol_28.svg`). Las derivaciones van de 9 producciones (ID 5, *El niño juega.*) a 20 (ID 28, relativa y completiva en la misma oración). Por defecto se omiten los nodos que solo derivan ε; `--con-epsilon` dibuja el árbol de derivación completo.

> *Figura sugerida:* `logs/arboles/arbol_13.svg` (*La gata muy rápida corre rápidamente en el jardín.*), que muestra en un solo árbol el intensificador, el adverbio de modo y el sintagma preposicional.

### 3.5 Costo computacional

Las 40 oraciones se analizaron en **2,55 ms** en total: promedio de 0,064 ms, mediana de 0,046 ms y máximo de 0,63 ms (la primera oración, que incluye la carga inicial). El análisis es lineal en el número de tokens, sin retroceso, y la tabla se consulta en tiempo constante.

## 4. Análisis

**El 100 % es esperado y no mide calidad lingüística.** Las etiquetas del corpus se definieron según las reglas reales de la CFG y se verificaron contra el parser (criterio del Integrante 1). Por eso el parser propio funciona como **referencia** del experimento: sus métricas confirman que el corpus está bien etiquetado y que el parser es determinista. Lo que mide el benchmark es cuánto se acercan las demás herramientas a esa referencia, no si nuestra gramática describe bien el español.

**Lo que el parser hace bien.** Detecta todas las discordancias del corpus, incluso las que están dentro de una relativa (ID 33), y para cada una indica la regla exacta que la rechaza. Una herramienta estadística no da esa explicación. La decisión es explícita y reproducible: la misma entrada produce siempre la misma salida.

**Rechazos de español correcto.** Las oraciones 30 (*El niño y la niña duermen.*) y 39 (*Los niños y las niñas juegan.*) son correctas en español y se rechazan porque la gramática no contempla la coordinación. Al intentar agregarla aparece un conflicto LL(1): con un solo token (*el*) no se puede decidir si el verbo será singular o plural. Es un límite de **cómo está escrita la gramática** para LL(1), no una prueba de que el español no sea libre de contexto: factorizando por la izquierda (leer primero el sintagma y decidir después) la coordinación vuelve a ser LL(1).

**Limitaciones que el corpus no expone.** La gramática también acepta oraciones que no son correctas en español. Por ejemplo, *el niño corre que la gata duerme* se acepta porque cualquier verbo admite una completiva (no se distingue qué verbos la permiten). Ninguna oración del corpus prueba ese caso, así que en este experimento el parser no registra falsos positivos, aunque la gramática sí podría producirlos. Tampoco hay ambigüedad: una gramática LL(1) nunca es ambigua, y cada sintagma preposicional se adjunta solo al verbo (ID 25, *Un niño grande juega con la niña.*).

**Escalabilidad.** Con dos géneros y dos números, cada sintagma se escribe cuatro veces (48 producciones para un léxico de 49 palabras). Cada rasgo nuevo (persona, tiempo, transitividad) multiplicaría de nuevo los no terminales. La precisión del parser se paga con una cobertura que solo crece agregando reglas a mano.

**Robustez.** El parser no tolera nada fuera de lo previsto: una palabra desconocida (ID 35) o una estructura distinta (ID 36) bastan para rechazar. Para validar es una ventaja; para procesar texto real, una desventaja. Esto lo diferencia de spaCy y del LLM, que siempre producen un análisis.

## 5. Cómo reproducir

```bash
python -m espanol.ejecutar_corpus          # logs/parser_propio.json, .txt y _resultados.csv
python -m espanol.visualizacion_arboles    # logs/arboles/*.svg, index.html, arboles_forest.tex
python -m unittest discover -s tests -t .  # 41 pruebas
```
