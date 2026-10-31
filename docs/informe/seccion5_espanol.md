# 5. Extensión de la gramática al español

## 5.1. Reglas incorporadas

La extensión no reescribe el parser: las producciones del español se entregan al mismo motor de `parser/ll1.py` que calcula FIRST, FOLLOW y la tabla predictiva del subconjunto de C++. Cambian el léxico, el símbolo inicial `Oracion` y las reglas.

Como una CFG no tiene atributos (`genero=M`, `numero=SG`), la concordancia se copia en el nombre del no terminal. El sintagma nominal se desdobla en `SN_m_sg`, `SN_f_sg`, `SN_m_pl` y `SN_f_pl`. `Oracion` se bifurca en `Sujeto_sg SV_sg` y `Sujeto_pl SV_pl`. Los modificadores opcionales son colas anulables, como `ExprTail` y `TermTail` en la Sección 4.

Fenómenos cubiertos:

- Concordancia de género y número en el SN, con `grande`/`grandes` como adjetivo invariable (`Adj_*`).
- Concordancia de número sujeto–verbo, decidida por el primer determinante.
- Modificadores: adjetivo, `muy`, adverbio de modo y frase preposicional.
- Relativa de sujeto (`el niño que corre`) y completiva (`observa que la gata duerme`).

Reglas del masculino singular (las demás combinaciones son análogas):

```
Oracion      → Sujeto_sg SV_sg . | Sujeto_pl SV_pl .
Sujeto_sg    → SN_m_sg SubOpt_sg | SN_f_sg SubOpt_sg
SN_m_sg      → det_m_sg n_m_sg ModNom_m_sg
ModNom_m_sg  → Adj_m_sg | adv_intens Adj_m_sg | ε
Adj_m_sg     → adj_m_sg | adj_inv_sg
SubOpt_sg    → que SV_sg | ε
SV_sg        → v_sg RestoSV
RestoSV      → que Clausula | AdvOpt SPOpt
Clausula     → Sujeto_sg SV_sg | Sujeto_pl SV_pl
AdvOpt       → adv_modo | ε
SPOpt        → prep SN_Prep | ε
SN_Prep      → SN_m_sg | SN_f_sg | SN_m_pl | SN_f_pl
```

48 producciones; tabla LL(1) sin conflictos (77 celdas). `FIRST(Sujeto_sg)` y `FIRST(Sujeto_pl)` son disjuntos.

## 5.2. Resultados de los intentos de extensión

| Oración | Resultado | Fenómeno |
|---|---|---|
| El gato negro duerme. | Aceptó | Género, número y sujeto–verbo |
| Los perros grandes juegan con la niña. | Aceptó | Adjetivo invariable y SP |
| La gata muy rápida corre rápidamente en el jardín. | Aceptó | Intensificador, adjetivo, adverbio y SP |
| El niño que corre juega en la casa. | Aceptó | Relativa de sujeto |
| El niño observa que la gata duerme. | Aceptó | Completiva |
| El gato negra duerme. | Rechazó | Discordancia de género |
| El gato negro duermen. | Rechazó | Discordancia sujeto–verbo |
| Los gatos que corre duermen. | Rechazó | Discordancia en la relativa |
| El niño y la niña duermen. | Rechazó | Coordinación (además, conflicto LL(1) si se añade la producción) |

Demo: `python -m espanol.parser_espanol`. El conflicto de la coordinación: `python -m espanol.parser --conflicto`.
