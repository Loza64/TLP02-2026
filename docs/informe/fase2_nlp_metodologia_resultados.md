# 3.2 Metodología: herramientas modernas de NLP

## 3.2.1 Herramientas, modelos y versiones

| | spaCy | HuggingFace Transformers |
|---|---|---|
| Versión de la librería | spaCy 3.8.18 | Transformers 5.23.0 (PyTorch 2.15.0, CPU) |
| Modelo(s) | `es_core_news_sm` 3.8.0 (≈ 16 MB) | `mrm8488/bert-spanish-cased-finetuned-pos` (POS) y `mrm8488/bert-spanish-cased-finetuned-pos-syntax` (función sintáctica), ≈ 420 MB de pesos cada uno |
| Tipo de modelo | Pipeline estadístico (tok2vec + morfologizador + parser de dependencias) | BETO (BERT en español) ajustado para clasificación de tokens sobre AnCora |
| Salida por palabra | Lema, POS universal, rasgos morfológicos, relación de dependencia y núcleo | Categoría EAGLES (DA, NC, AQ, VMI…) y función sintáctica (SUJ, CD, CC, CREG, ROOT…) con su probabilidad |
| Script | `nlp/spacy_comparison.py` | `nlp/segunda_herramienta.py` |
| Log | `logs/spacy.json` | `logs/segunda_herramienta.json` |

Se eligió Transformers en lugar de NLTK porque NLTK no incluye un analizador sintáctico entrenado
para el español: para obtener sujeto, verbo y objeto habría que escribir otra gramática a mano.
Los dos modelos BETO dan, para cada palabra, su categoría gramatical y su función sintáctica, que
se pueden comparar con la estructura esperada. Ambas herramientas se ejecutaron en CPU y en modo
de inferencia, sin muestreo. Al repetir la ejecución se obtuvieron las mismas 40 decisiones.

## 3.2.2 Procedimiento

1. Cada script lee `corpus/corpus_pruebas.csv` (40 oraciones: 12 de nivel 1, 16 de nivel 2 y
   12 de nivel 3). El log guarda el hash SHA-256 del corpus, lo que prueba que todas las
   condiciones procesaron el mismo archivo.
2. Cada oración se procesa por separado. Se registran su marca de tiempo, el tiempo de proceso y
   la salida completa de la herramienta.
3. Sobre esa salida se aplican los criterios C1–C4 (sección 3.2.3), que producen la decisión
   ACEPTADA / RECHAZADA y los motivos de rechazo.
4. La decisión se compara con la etiqueta esperada del corpus (VP, VN, FP o FN). Además, se
   cuentan los errores de etiquetado (sección 3.2.4).
5. spaCy exporta, además, los árboles de dependencias con displaCy (`nlp/results/arboles_spacy.html`).

## 3.2.3 Del análisis a una decisión de aceptación

spaCy y los modelos BETO **no validan la gramaticalidad**: siempre devuelven un análisis. En
este experimento, las dos herramientas produjeron un análisis para las 40 oraciones, incluidas
las 12 que la CFG rechaza. Por eso, que la herramienta produzca un análisis no equivale a
aceptar la oración. Se definieron cuatro criterios, comunes a ambas herramientas y derivados de
las producciones de la CFG. Una oración se considera **ACEPTADA solo si cumple todos los
criterios evaluables**:

| Criterio | Regla | spaCy | Transformers |
|---|---|---|---|
| **C1** Raíz verbal finita | Hay exactamente un núcleo principal y es un verbo conjugado | Un solo `ROOT`, POS `VERB`/`AUX`, `VerbForm` distinto de Inf/Ger/Part | Un solo token con función `ROOT` y etiqueta de verbo conjugado (`VMI`, `VMS`, `VMM`, …) |
| **C2** Sujeto nominal | El verbo principal tiene un sujeto con núcleo sustantivo y determinante (`SN → det n ModNom`) | Un hijo `nsubj` de la raíz, POS `NOUN`, con un hijo `det` | Un `NC` con función `SUJ` antes del verbo principal y precedido por un determinante (`D…`) |
| **C3** Concordancia | det–n y adj–n en género y número; sujeto–verbo y relativa–antecedente en número | Compara los rasgos `Gender`/`Number` predichos por el morfologizador | **No evaluable**: las etiquetas EAGLES del modelo no incluyen género ni número |
| **C4** Alcance de la CFG | Cada relación del análisis corresponde a una producción de la gramática | Relaciones permitidas: `nsubj`, `det`, `amod`, `advmod`, `obl`+`case` (solo tras el verbo), `acl` (relativa de sujeto), `ccomp`+`mark que` (completiva), `punct` | Funciones permitidas: `SUJ`, `ROOT`, `CC`, `CREG` (si es SP), `CD` (solo si es el verbo de una completiva), `PUNC`; la conjunción `y` (CC) queda fuera |

Si una herramienta no predice un rasgo, el par afectado queda *no evaluable* y no se cuenta como
violación. No se completa lo que la herramienta no sabe con conocimiento externo; si se hiciera,
se estarían evaluando reglas propias y no la herramienta. Por la misma razón, la decisión **no
aplica el léxico cerrado** de la CFG: si lo aplicara, cualquier palabra fuera del vocabulario
provocaría un rechazo automático, y las herramientas solo copiarían el filtro léxico del parser
propio. La correspondencia completa entre relaciones y producciones está en `nlp/criterios.py` y
se copia en cada log (campo `metodologia`). Los criterios se fijaron antes de ejecutar las
herramientas sobre el corpus y no se modificaron después de ver los resultados.

## 3.2.4 Errores de etiquetado

Para cada palabra del corpus que está en el léxico de la CFG, se compara la categoría asignada por
la herramienta con la categoría de su terminal. Por ejemplo, *perro* es `n` y se espera `NOUN` en
spaCy o `N…` en EAGLES. El corpus no incluye la columna `estructura_esperada`, por lo que no se
evaluaron los errores de rol (sujeto, verbo, objeto). Los rasgos morfológicos erróneos, como un
verbo conjugado marcado como infinitivo, no se cuentan aquí: se reflejan en los criterios C1 y C3.

## 3.2.5 Limitaciones de la metodología

* Los criterios son una **aproximación** a la CFG a partir del análisis de cada herramienta, no
  un reconocedor formal. Una oración puede rechazarse correctamente por un motivo distinto del
  fenómeno que se quería probar. Por eso el log registra los motivos (ver 5.2).
* Ningún criterio exige que una preposición tenga un sustantivo detrás. Por eso *El gato duerme
  en.* fue aceptada por ambas herramientas (sección 5.2). Esta limitación se identificó después de
  ejecutar y se documenta en lugar de corregirse, para no ajustar los criterios a los resultados.
* La salida de Transformers no es un árbol: no tiene enlaces núcleo–dependiente. La pertenencia
  del sujeto al verbo principal y el antecedente de la relativa se infieren por posición.
* C3 depende de la calidad del morfologizador. En spaCy, los rasgos se predicen **según el
  contexto**, no según el diccionario.

# 4.2 Resultados: herramientas modernas de NLP

| Métrica | spaCy | Transformers (BETO) |
|---|---|---|
| Precisión | 88,5 % (23/26) | 80,0 % (28/35) |
| Recall | 82,1 % (23/28) | 100,0 % (28/28) |
| Rechazo correcto | 75,0 % (9/12) | 41,7 % (5/12) |
| Exactitud | 80,0 % (32/40) | 82,5 % (33/40) |
| VP / VN / FP / FN | 23 / 9 / 3 / 5 | 28 / 5 / 7 / 0 |
| Errores de etiquetado | 8 (en 7 oraciones) | 0 |
| Oraciones con análisis | 40 / 40 | 40 / 40 |
| Tiempo medio por oración | 2,8 ms | 35,5 ms (dos modelos) |

**Errores de decisión por nivel:**

| Nivel | spaCy | Transformers |
|---|---|---|
| 1 — simples (12, todas ACEPTADA) | 2 FN | 0 |
| 2 — intermedias (16, todas ACEPTADA) | 3 FN | 0 |
| 3 — complejas (12, todas RECHAZADA) | 3 FP | 7 FP |

**Criterios incumplidos** (número de oraciones en que cada criterio falló; una oración puede
incumplir varios):

| Criterio | spaCy | Transformers |
|---|---|---|
| C1 raíz verbal | 5 | 0 |
| C2 sujeto nominal | 7 | 2 |
| C3 concordancia | 3 | no evaluable |
| C4 alcance de la CFG | 7 | 3 |

# 5.2 Análisis de errores: herramientas modernas de NLP

**Falsos negativos de spaCy: errores de etiquetado del modelo.** Los 5 FN de spaCy están en los
niveles 1 y 2, y ninguno se debe a la estructura de la oración. En cuatro (ids 7, 11, 14 y 24),
`es_core_news_sm` etiqueta *perro* como nombre propio (`PROPN`), por lo que C2 no encuentra un
sujeto sustantivo. En el id 14 además une *perro negro* con la relación `flat`, propia de los
nombres compuestos. En el quinto (id 26, *Las gatas negras duermen bajo la casa.*), etiqueta
*duermen* como infinitivo y falla C1. Estos son también los errores de etiquetado contados: *perro*
como `PROPN` (4), *negro* como `PROPN` (ids 14, 15 y 35) y *Gato* como `PROPN` (id 36). El modelo
BETO no cometió ningún error de POS en las palabras del léxico, y su menor confianza en una
etiqueta POS fue 0,992.

**Falsos positivos: analizar no es validar la concordancia.** Las dos herramientas aceptaron
oraciones que la CFG rechaza por discordancia:

* *El gato negra duerme.* (id 29): spaCy etiqueta *negra* como `Gender=Masc`. El morfologizador
  ajusta el rasgo al contexto y la discordancia desaparece antes de evaluarse. En cambio, en *La
  gata negro duerme.* (id 34) sí conserva `negro` = `Masc` y C3 la rechaza: el resultado depende de
  la predicción en cada caso, no de una regla.
* *Los gato negros duermen.* (id 31): spaCy no asigna número a *gato*, el par queda no evaluable
  y la oración se acepta.
* Transformers acepta las cinco oraciones con discordancia que no rechaza por otro criterio (ids
  29, 31, 33, 34 y 40), porque sus etiquetas no tienen género ni número.

**Léxico.** *El elefante negro duerme.* (id 35) es correcta en español, pero está fuera del léxico
de la CFG. Transformers la acepta (FP esperado, porque la decisión no aplica el léxico). spaCy la
rechaza, pero porque etiqueta *elefante* como `PROPN`, no porque conozca el léxico de la gramática.

**Estructuras incompletas.** *El gato duerme en.* (id 37) fue aceptada por ambas herramientas:
spaCy analiza la preposición suelta como `advmod` del verbo y BETO le asigna la función CC. Es la
limitación metodológica descrita en 3.2.5. *El niño observa que.* (id 38) sí se rechazó en ambas,
por C4.

**Rechazos correctos por el motivo equivocado.** En spaCy, *El gato negro duermen.* (id 32) se
rechazó porque *duermen* se etiquetó como infinitivo (C1), no por detectar la discordancia de
número. *Los gatos que corre duermen.* (id 33) se rechazó porque el modelo tomó *gatos* como raíz,
aunque C3 también detectó la discordancia de la relativa. En Transformers, el id 32 se rechazó
porque el modelo no asignó la función SUJ a *gato* (su menor confianza de función en todo el
corpus, 0,833). Son aciertos según la métrica, pero no prueban que la herramienta valide la
concordancia.

**Estructuras fuera de la CFG.** La coordinación (ids 30 y 39) se rechazó en ambas herramientas
por C4, y precisamente porque la reconocieron: spaCy produce las relaciones `cc` y `conj`, y BETO
etiqueta *y* como conjunción coordinante. Las herramientas modernas sí procesan estructuras que la
gramática no contempla; lo que no hacen es decidir si la oración pertenece al lenguaje.

**Comparación entre ambas herramientas.** spaCy entrega un árbol de dependencias completo y rasgos
morfológicos. Eso permite aplicar los cuatro criterios y le da el mayor rechazo correcto (75,0 %
frente a 41,7 %), pero su modelo pequeño comete errores de POS que causan todos sus FN. BETO etiqueta
con más precisión (recall del 100 %, sin errores de POS), pero no da estructura jerárquica ni
morfología, así que no detecta ninguna discordancia. spaCy es unas 12 veces más rápido por oración
(2,8 ms frente a 35,5 ms) y su modelo ocupa unas 50 veces menos (≈ 16 MB frente a ≈ 840 MB).
Ninguno de los dos enfoques es un reconocedor: ambos son analizadores robustos que **siempre**
producen una salida, mientras que el parser LL(1) decide si una oración pertenece al lenguaje.
Todos los FP de las dos herramientas están en el nivel 3, y la mayoría corresponden a
discordancias: 2 de 3 en spaCy y 5 de 7 en Transformers. El resto se reparte entre la SP
incompleta (ambas) y la palabra fuera del léxico (Transformers). Esto indica que la debilidad
principal de ambas no es la cobertura estructural, sino validar la concordancia.
