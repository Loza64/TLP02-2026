# 6. Análisis de las limitaciones de la CFG

## 6.1. Identificación de los puntos de fallo

| Oración | Esperado / obtenido | Regla | Fenómeno |
|---|---|---|---|
| El gato negra duerme. | Rechazar / Rechazó | `ModNom_m_sg` | Concordancia local de género |
| El gato negro duermen. | Rechazar / Rechazó | `Oracion → Sujeto_sg SV_sg` | Concordancia sujeto–verbo |
| Los gatos que corre duermen. | Rechazar / Rechazó | `SubOpt_pl → que SV_pl` | Concordancia en la subordinada |
| El niño y la niña duermen. | Aceptar en español / Rechazó; conflicto LL(1) al añadir la producción | `M[Oracion, det_*]` | Coordinación que cambia el número |
| El gato duerme en el jardín (el SP también podría modificar a *gato*) | Dos análisis / un solo árbol | `SPOpt` solo bajo `RestoSV` | Ambigüedad de adjunción |

Las tres primeras oraciones violan reglas que sí son CFG: el rechazo es correcto. Los dos últimos casos marcan fronteras distintas.

## 6.2. Explicación formal

1. **Rasgos finitos.** Género y número en tercera persona son un conjunto finito. El lenguaje bien concordado de este subconjunto **sí** es libre de contexto. La explosión de no terminales es un problema de escala, no una prueba de que el fenómeno sea de Tipo 1.

2. **Un token de anticipación.** *El niño duerme* y *el niño y la niña duermen* comparten `det_m_sg`. Añadir `Sujeto_pl → SN_m_sg conj SN_Coord` choca en `M[Oracion, det_f_sg]`. Una CFG puede generar esa coordinación; un parser LL(1) no puede decidir el número del verbo con un solo símbolo.

3. **Ambigüedad.** La CFG podría dar dos árboles para la adjunción del SP; LL(1) obliga a elegir uno (aquí, al verbo).

4. **Lo que sí queda fuera de las CFG.** Dependencias cruzadas y lenguajes de copia `{ww}` no son libres de contexto. Este subconjunto no implementa un fenómeno de esa clase. Un conflicto LL(1) o un léxico cerrado no bastan para afirmar que «la CFG no puede el español».
