# 4–6. Resultados cuantitativos, análisis de errores y comportamiento del LLM

**Fuente de los datos.** Las cifras de esta sección se obtuvieron mediante `python -m evaluacion.evaluar`. Las tablas se generan en `evaluacion/tabla_comparativa.md` y las gráficas en `evaluacion/graficas/`. Para el análisis del LLM se utilizaron las ejecuciones finales del 19 de noviembre de 2026, cuyos resultados consolidados se encuentran en `logs/llm_zero_shot.json` y `logs/llm_few_shot.json`.

## 4.1 Configuración del LLM

| Parámetro | Valor |
|---|---|
| Modelo | Google Gemini `gemini-3.5-flash-lite` (SDK `google-genai` 3.5.0) |
| Parámetros | `temperature = 0`, `response_mime_type = application/json` |
| Envío | 8 lotes por modalidad, 5 oraciones por lote, hasta 5 intentos por lote |
| Zero-shot | Instrucciones + 48 producciones + 22 terminales + léxico de 55 palabras (`llm/prompt_zero_shot.txt`) |
| Few-shot | Las mismas instrucciones + 4 ejemplos resueltos, 2 aceptados y 2 rechazados, ajenos al corpus (`llm/prompt_few_shot.txt`) |
| Salida solicitada | ID, decisión, producciones aplicadas, justificación y estructura |
| Evidencia | Prompts enviados, respuestas originales, `llamadas.json` con marcas de tiempo y `metadatos.json` |
| Ejecuciones finales | `logs/llm_zero_shot_20261119_085801/` y `logs/llm_few_shot_20261119_092553/` |

Ambas modalidades utilizaron la misma plantilla de instrucciones; la diferencia fue la inclusión de cuatro ejemplos en Few-Shot. Cada modalidad procesó las 40 oraciones del corpus. En Few-Shot, el lote 4 presentó errores HTTP 503 durante los primeros intentos, pero se recuperó mediante el mecanismo de reintentos, completando los 40 resultados sin iniciar una ejecución nueva.

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
| Errores de etiquetado | 0 | 8 | 0 | 62 | 31 |
| Exactitud (%) | 100.00 | 80.00 | 82.50 | 100.00 | 100.00 |

Figuras: `evaluacion/graficas/metricas_comparativas.png` (precisión, recall y rechazo correcto), `errores_comparativos.png` (FP, FN y errores de etiquetado) y `errores_por_nivel.png`.

**Errores de clasificación (FP + FN) por nivel:**

| Nivel | Parser propio | spaCy | HuggingFace | LLM zero-shot | LLM few-shot |
|---|---:|---:|---:|---:|---:|
| 1 — simples (12) | 0 | 2 (FN) | 0 | 0 | 0 |
| 2 — intermedias (16) | 0 | 3 (FN) | 0 | 0 | 0 |
| 3 — complejas (12) | 0 | 3 (FP) | 7 (FP) | 0 | 0 |

## 5. Análisis de errores

**Mayor precisión y rechazo correcto.** El parser propio y el LLM, en sus dos modalidades, obtuvieron 100 % en las tres métricas. En el parser es esperable: las etiquetas del corpus se definieron a partir de su propia CFG, por lo que funciona como referencia. Lo destacable es que el LLM, al recibir explícitamente la gramática, reprodujo las 40 decisiones del parser en ambas modalidades.

**Mayor cobertura.** El parser, HuggingFace y el LLM aceptaron las 28 oraciones que debían aceptarse (recall de 100 %). spaCy fue el único con falsos negativos (5).

**Más falsos positivos: HuggingFace (7).** Todos están en el nivel 3, en oraciones que la CFG rechaza por concordancia o por estar incompletas: *El gato negra duerme* (29), *Los gato negros duermen* (31), *Los gatos que corre duermen* (33), *La gata negro duerme* (34), *El elefante negro duerme* (35, palabra fuera del léxico), *El gato duerme en* (37) y *El gato muy negras duerme* (40). El modelo BETO asigna categoría y función a cada palabra aunque la oración no concuerde. No predice rasgos de género y número, así que el criterio C3 de concordancia no tiene con qué comprobarse. **Producir un análisis no equivale a validar la gramaticalidad.**

**Más falsos negativos: spaCy (5).** Son oraciones válidas para la CFG en las que el modelo etiquetó mal una palabra, y ese error bastó para que fallara un criterio: *Un perro corre* (7) y *El perro grande duerme* (11), donde «perro» se etiquetó como nombre propio (PROPN), y *El perro negro juega tranquilamente bajo la casa* (14), *El perro observa que el gato duerme* (24) y *Las gatas negras duermen bajo la casa* (26). Sus 8 errores de etiquetado se concentran en «perro» y «negro» etiquetados como PROPN. spaCy también aceptó 3 oraciones del nivel 3 (29, 31 y 37).

**Nivel con más errores.** El nivel 3 acumula 10 de los 15 errores de clasificación del experimento: 3 de spaCy y 7 de HuggingFace. Las estructuras más difíciles fueron la discordancia de género y número (29, 31, 33, 34, 40) y la oración incompleta (37), justamente los fenómenos que una CFG con concordancia codificada en los no terminales resuelve por construcción y que un analizador estadístico no tiene por qué rechazar.

## 6. Comportamiento del LLM

**¿Respetó las reglas de la CFG?** En la clasificación, sí: ambas modalidades obtuvieron 0 falsos positivos y 0 falsos negativos. No aceptaron ninguna oración que la gramática rechaza, incluidas las oraciones gramaticales en español pero ausentes del léxico, como *El elefante negro duerme*. Sus justificaciones citaron reglas concretas de la CFG para explicar las decisiones. Por ejemplo, para *El gato duerme en* (37), el modelo indicó que la preposición «en» requiere un `SN_Prep` a continuación, según la producción `SPOpt -> prep SN_Prep`. Para *El niño observa que* (38), señaló que `RestoSV -> que Clausula` exige una cláusula completa.

Sin embargo, acertar la decisión no significa reproducir fielmente la derivación formal. Para evaluar esta diferencia se compararon las estructuras generadas con los árboles del parser propio. Los resultados fueron:

| Indicador | Zero-shot | Few-shot |
|---|---:|---:|
| Reglas citadas | 327 | 327 |
| Reglas inexistentes en la CFG | 0 | 3 |
| Árboles generados para oraciones aceptadas | 28 | 28 |
| Árboles reconocidos por el evaluador | 28 | 26 |
| Árboles mal formados | 0 | 2 |
| Árboles idénticos al del parser propio | 18/28 | 21/26 |
| Coincidencia estructural (%) | 64.29 | 80.77 |
| Errores de etiquetado | 62 | 31 |

La coincidencia estructural se calcula únicamente sobre los árboles que el evaluador pudo reconocer. Por ello, los dos árboles mal formados de Few-Shot no forman parte del denominador de esa métrica.

**Diferencias en Zero-Shot.** Aunque los 28 árboles generados pudieron reconocerse, solo 18 coincidieron exactamente con los del parser propio. Se identificaron errores de etiquetado en 62 palabras. En los casos 16 a 20, la estructura omitió las palabras terminales y dejó únicamente categorías gramaticales, lo que impidió comprobar su correspondencia con el léxico. En los casos 21 a 25, algunas palabras aparecieron en el árbol sin la categoría terminal exigida por la CFG. Estos resultados muestran que el modelo puede acertar la clasificación sin reproducir correctamente todos los detalles de la derivación.

**Diferencias en Few-Shot.** La modalidad generó 28 árboles, de los cuales 26 pudieron reconocerse y 2 estaban mal formados (casos 13 y 14). Los árboles mal formados se excluyeron de la comparación estructural y del análisis de etiquetado que requiere un árbol válido. Entre los árboles reconocidos, 21 coincidieron con el parser propio, lo que representa una coincidencia estructural de 80.77 %. También se registraron 31 errores de etiquetado, principalmente por omisiones de palabras en los casos 16 a 20. Además, en los casos 26, 27 y 28 se citaron tres producciones que no existen exactamente en la CFG.

**¿Mejoró con Few-Shot?** No hubo diferencia en la clasificación: ambas modalidades obtuvieron 100 % de exactitud y las mismas métricas de precisión, recall y rechazo correcto. En la fidelidad de las estructuras, Few-Shot presentó resultados mixtos: redujo los errores de etiquetado de 62 a 31 y aumentó la coincidencia estructural de 64.29 % a 80.77 %, pero también produjo dos árboles mal formados y tres producciones inexistentes, frente a ninguno de esos problemas en Zero-Shot. Por tanto, no puede afirmarse que una modalidad sea superior en todos los aspectos. Los ejemplos parecen haber favorecido algunos aspectos de la estructura, aunque no garantizaron una salida formalmente correcta en todos los casos.

**Advertencia metodológica.** Las cifras aquí presentadas corresponden a las ejecuciones finales, en las que ambas modalidades utilizaron las mismas instrucciones y la única diferencia fue la inclusión de cuatro ejemplos en Few-Shot. Esto permite una comparación más controlada que la realizada con las ejecuciones preliminares del 18 de noviembre. Los resultados siguen limitados a un corpus de 40 oraciones y una ejecución final por modalidad.

## 6.1 Parser formal, modelo estadístico y LLM

| Criterio | Parser propio (CFG LL(1)) | spaCy / HuggingFace | LLM (Gemini) |
|---|---|---|---|
| **Decisión de gramaticalidad** | Explícita y exacta respecto de su gramática | No existe directamente; hubo que derivarla con los criterios C1–C4 | Explícita, pero depende de que el modelo siga las instrucciones |
| **Robustez** | Rechaza todo lo que no está en su léxico o sus reglas | Analiza cualquier oración, incluso agramatical (7 FP en HF) | Clasificó correctamente las 40 oraciones, pero presentó errores en algunas estructuras generadas |
| **Ambigüedad** | La tabla LL(1) no admite conflictos: la coordinación quedó fuera por eso | Elige el análisis más probable | Elige una derivación sin garantía de que sea la única ni de que respete exactamente la CFG |
| **Escalabilidad** | Ampliar cobertura exige escribir reglas y léxico a mano | Cubre el español general sin cambios | Basta con cambiar el prompt, pero este crece con la gramática (aproximadamente 5–6 KB por lote) |
| **Costo computacional** | 0.04 ms por oración, local | 2.8 ms (spaCy) y 35.5 ms (HF) por oración, local | Ejecución remota, con tiempos dependientes del servicio externo y posibles reintentos |
| **Aplicabilidad práctica** | Verificar un lenguaje formal cerrado | Extraer información de texto real | Prototipar o explicar decisiones; no sustituye a un verificador formal |

## 7. Conclusiones (aporte de esta sección)

1. Con la gramática explícita en el prompt, el LLM reprodujo las 40 decisiones de la CFG en ambas modalidades. Ninguna herramienta estadística logró el mismo resultado: spaCy obtuvo 80 % de exactitud y HuggingFace 82.5 %.
2. Acertar la decisión no implica seguir exactamente la derivación. Zero-Shot produjo 28 árboles reconocibles, pero solo 18 fueron idénticos al parser propio. Few-Shot produjo 26 árboles reconocibles, de los cuales 21 coincidieron; además, presentó dos árboles mal formados y tres producciones inexistentes.
3. spaCy y HuggingFace fallaron sobre todo en el nivel 3 y en la concordancia, porque analizan en lugar de validar. spaCy también rechazó oraciones válidas por errores de etiquetado.
4. Few-Shot no mejoró la clasificación, pues ambas modalidades alcanzaron 100 % de exactitud. Sí redujo los errores de etiquetado y mejoró la coincidencia estructural, aunque presentó árboles mal formados y producciones inexistentes. Esto muestra que los ejemplos pueden influir en la fidelidad de la salida, pero no garantizan el cumplimiento formal de la CFG.
5. El parser propio continúa siendo la referencia formal para este lenguaje: sus decisiones y árboles se derivan directamente de las reglas y el léxico definidos. El LLM puede seguir las instrucciones de clasificación con gran precisión, pero sus estructuras requieren validación independiente.