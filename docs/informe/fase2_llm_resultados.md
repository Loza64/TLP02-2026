# 4–6. Resultados cuantitativos, análisis de errores y comportamiento del LLM

> **Fuente de los datos.** Todas las cifras de esta sección salen de
> `python -m evaluacion.evaluar` (tablas en `evaluacion/tabla_comparativa.md`, gráficas en
> `evaluacion/graficas/`). **Pendiente:** las cifras del LLM corresponden a las ejecuciones
> preliminares `logs/llm_*_20261118_*`. Hay que repetirlas con `python -m llm.ejecutar_llm
> ambos` (mismas instrucciones en las dos modalidades y timestamp por llamada) y actualizar
> esta sección con la nueva salida del evaluador.

## 4.1 Configuración del LLM

| Parámetro | Valor |
|---|---|
| Modelo | Google Gemini `gemini-3.5-flash-lite` (SDK `google-genai` 3.5.0) |
| Parámetros | `temperature = 0`, `response_mime_type = application/json` |
| Envío | 8 llamadas por modalidad, lotes de 5 oraciones, hasta 5 intentos por lote |
| Zero-shot | Instrucciones + 48 producciones + 22 terminales + léxico de 55 palabras (`llm/prompt_zero_shot.txt`) |
| Few-shot | Lo mismo + 4 ejemplos resueltos, 2 aceptados y 2 rechazados, ajenos al corpus (`llm/prompt_few_shot.txt`) |
| Salida pedida | ID, decisión, producciones aplicadas, justificación y estructura |
| Evidencia | `prompt_lote_XX.txt`, respuestas brutas, `llamadas.json` (timestamps), `metadatos.json` |

## 4.2 Tabla comparativa

Positivo = ACEPTADA. Precisión = VP/(VP+FP); Recall = VP/(VP+FN); Rechazo correcto = VN/(VN+FP).

| Métrica | Parser propio | spaCy | HuggingFace | LLM zero-shot | LLM few-shot |
|---|---:|---:|---:|---:|---:|
| Precisión (%) | 100.00 | 88.46 | 80.00 | 100.00 | 100.00 |
| Recall (%) | 100.00 | 82.14 | 100.00 | 100.00 | 100.00 |
| Rechazo correcto (%) | 100.00 | 75.00 | 41.67 | 100.00 | 100.00 |
| VP | 28 | 23 | 28 | 28 | 28 |
| VN | 12 | 9 | 5 | 12 | 12 |
| FP | 0 | 3 | 7 | 0 | 0 |
| FN | 0 | 5 | 0 | 0 | 0 |
| Errores de etiquetado | 0 | 8 | 0 | 2 | 22 |

Figuras: `evaluacion/graficas/metricas_comparativas.png` (precisión, recall y rechazo
correcto), `errores_comparativos.png` (FP, FN y errores de etiquetado) y
`errores_por_nivel.png`.

**Errores de clasificación (FP + FN) por nivel:**

| Nivel | Parser propio | spaCy | HuggingFace | LLM zero-shot | LLM few-shot |
|---|---:|---:|---:|---:|---:|
| 1 — simples (12) | 0 | 2 (FN) | 0 | 0 | 0 |
| 2 — intermedias (16) | 0 | 3 (FN) | 0 | 0 | 0 |
| 3 — complejas (12) | 0 | 3 (FP) | 7 (FP) | 0 | 0 |

## 5. Análisis de errores

**Mayor precisión y rechazo correcto.** El parser propio y el LLM, en sus dos modalidades,
obtuvieron 100 % en las tres métricas. En el parser es esperable: las etiquetas del corpus se
definieron a partir de su propia CFG, así que funciona como referencia. Lo interesante es que
el LLM, al recibir explícitamente la gramática, reprodujo las 40 decisiones del parser.

**Mayor cobertura.** El parser, HuggingFace y el LLM aceptaron las 28 oraciones que debían
aceptarse (recall 100 %). spaCy fue el único con falsos negativos (5).

**Más falsos positivos: HuggingFace (7).** Todos están en el nivel 3, en oraciones que la CFG
rechaza por concordancia o por estar incompletas: *El gato negra duerme* (29), *Los gato negros
duermen* (31), *Los gatos que corre duermen* (33), *La gata negro duerme* (34), *El elefante negro
duerme* (35, palabra fuera del léxico), *El gato duerme en* (37) y *El gato muy negras duerme* (40).
El modelo BETO asigna categoría y función a cada palabra aunque la oración no concuerde. No
predice rasgos de género y número, así que el criterio C3 de concordancia no tiene con qué
comprobarse. **Producir un análisis no equivale a validar la gramaticalidad.**

**Más falsos negativos: spaCy (5).** Son oraciones válidas para la CFG en las que el modelo
etiquetó mal una palabra, y ese error bastó para que fallara un criterio: *Un perro corre* (7) y
*El perro grande duerme* (11), donde «perro» se etiquetó como nombre propio (PROPN), y *El perro
negro juega tranquilamente bajo la casa* (14), *El perro observa que el gato duerme* (24) y *Las
gatas negras duermen bajo la casa* (26). Sus 8 errores de etiquetado se concentran en «perro» y
«negro» etiquetados como PROPN. spaCy también aceptó 3 oraciones del nivel 3 (29, 31 y 37).

**Nivel con más errores.** El nivel 3 acumula 10 de los 15 errores de clasificación del
experimento: 3 de spaCy y 7 de HuggingFace. Las estructuras más difíciles fueron la
**discordancia de género y número** (29, 31, 33, 34, 40) y la **oración incompleta** (37),
justo los fenómenos que una CFG con concordancia codificada en los no terminales resuelve por
construcción y que un analizador estadístico no tiene por qué rechazar.

## 6. Comportamiento del LLM

**¿Respetó las reglas de la CFG?** En la decisión, sí: 0 FP y 0 FN en ambas modalidades. No
aceptó ninguna oración que la gramática rechaza, ni siquiera las gramaticales en español pero
ausentes del léxico (*El elefante negro duerme*). Sus justificaciones citan la regla concreta
que falla. Por ejemplo, para *El gato duerme en.* (37) respondió que «la preposición 'en' requiere
un SN_Prep a continuación según la regla SPOpt -> prep SN_Prep». Para *El niño observa que.* (38)
dijo que «RestoSV -> que Clausula» exige una cláusula completa.

En la **estructura** que justifica cada decisión, el cumplimiento no es perfecto:

| Indicador (`evaluacion/cumplimiento_llm.csv`) | Zero-shot | Few-shot |
|---|---:|---:|
| Reglas citadas que no existen en la CFG | 0 de 346 | 3 de 322 |
| Árboles idénticos al del parser (ignorando ε) | 24 de 28 | 23 de 28 |
| Errores de etiquetado | 2 | 22 |

- En zero-shot, los 4 árboles distintos añaden niveles que la gramática no tiene, como
  `[v_pl v_pl(duermen)]` (26, 27, 28), o reescriben palabras sin tilde (*rapidas*,
  *rapidamente* en la 23). Esos dos cambios explican sus 2 errores de etiquetado.
- En few-shot, 5 árboles (11 a 15) dejan las palabras sin categoría, por ejemplo
  `[SN_m_sg El perro …]` sin `det_m_sg` ni `n_m_sg`. Eso genera 22 errores de etiquetado. Además,
  en 26, 27 y 28 cita `Oracion -> Sujeto_pl SV_pl` sin el punto final, una producción que no
  existe.

**¿Mejoró con few-shot?** En la clasificación no hubo diferencia medible: las dos modalidades
llegaron al 100 % y no había margen de mejora. En la fidelidad formal, few-shot salió **peor**:
22 errores de etiquetado frente a 2 y 3 reglas inexistentes frente a 0. Los ejemplos
resueltos solo tienen justificación en prosa, sin árbol, y es plausible que el modelo imitara
ese formato más informal en la estructura. Con un corpus de 40 oraciones y una sola ejecución
por modalidad, esta diferencia es una observación, no una conclusión general.

**Advertencia metodológica.** En las ejecuciones preliminares, el prompt zero-shot se envió con
una redacción de las instrucciones distinta de la del few-shot. Por tanto, la comparación de
esta sección no aísla el efecto de los ejemplos. La repetición con `llm/ejecutar_llm.py` corrige
esto: ambas modalidades se generan desde la misma plantilla y la única diferencia es el bloque de
ejemplos.

## 6.1 Parser formal, modelo estadístico y LLM

| Criterio | Parser propio (CFG LL(1)) | spaCy / HuggingFace | LLM (Gemini) |
|---|---|---|---|
| **Decisión de gramaticalidad** | Explícita y exacta respecto de su gramática | No existe; hubo que derivarla con los criterios C1–C4 | Explícita, pero depende de que el modelo siga las instrucciones |
| **Robustez** | Rechaza todo lo que no está en su léxico o sus reglas | Analiza cualquier oración, incluso agramatical (7 FP en HF) | Acierta en las decisiones, pero su estructura varía de forma y a veces altera el texto |
| **Ambigüedad** | La tabla LL(1) no admite conflictos: la coordinación quedó fuera por eso | Elige el análisis más probable | Elige una derivación sin garantía de que sea la única |
| **Escalabilidad** | Ampliar cobertura exige escribir reglas y léxico a mano | Cubre el español general sin cambios | Basta con cambiar el prompt, pero el prompt crece con la gramática (≈ 5–6 KB por lote) |
| **Costo computacional** | 0.04 ms por oración, local | 2.8 ms (spaCy) y 35.5 ms (HF) por oración, local | ≈ 26 s por modalidad para 8 llamadas remotas, con reintentos por errores 503, dependiente de un servicio externo |
| **Aplicabilidad práctica** | Verificar un lenguaje formal cerrado | Extraer información de texto real | Prototipar o explicar decisiones; no sustituye a un verificador formal |

## 7. Conclusiones (aporte de esta sección)

1. Con la gramática explícita en el prompt, el LLM reprodujo las 40 decisiones de la CFG en
   ambas modalidades. Ninguna herramienta estadística lo logró: spaCy acertó 80 % y
   HuggingFace 82.5 %.
2. Acertar la decisión no implica seguir la derivación. Entre 4 y 5 de los 28 árboles del
   LLM difieren del árbol del parser, y en few-shot aparecen producciones inexistentes.
3. spaCy y HuggingFace fallan sobre todo en el nivel 3 y en la concordancia, porque analizan
   en lugar de validar. spaCy además pierde oraciones válidas por errores de etiquetado (PROPN).
4. Few-shot no mejoró la clasificación y empeoró la fidelidad de la estructura. Esta
   conclusión debe confirmarse al repetir el experimento con instrucciones idénticas.
