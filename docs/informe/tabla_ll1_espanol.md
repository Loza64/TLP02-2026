### Producciones

1. `Oracion → Sujeto_sg SV_sg .`
2. `Oracion → Sujeto_pl SV_pl .`
3. `Sujeto_sg → SN_m_sg SubOpt_sg`
4. `Sujeto_sg → SN_f_sg SubOpt_sg`
5. `Sujeto_pl → SN_m_pl SubOpt_pl`
6. `Sujeto_pl → SN_f_pl SubOpt_pl`
7. `SN_m_sg → det_m_sg n_m_sg ModNom_m_sg`
8. `SN_f_sg → det_f_sg n_f_sg ModNom_f_sg`
9. `SN_m_pl → det_m_pl n_m_pl ModNom_m_pl`
10. `SN_f_pl → det_f_pl n_f_pl ModNom_f_pl`
11. `ModNom_m_sg → Adj_m_sg`
12. `ModNom_m_sg → adv_intens Adj_m_sg`
13. `ModNom_m_sg → ε`
14. `Adj_m_sg → adj_m_sg`
15. `Adj_m_sg → adj_inv_sg`
16. `ModNom_f_sg → Adj_f_sg`
17. `ModNom_f_sg → adv_intens Adj_f_sg`
18. `ModNom_f_sg → ε`
19. `Adj_f_sg → adj_f_sg`
20. `Adj_f_sg → adj_inv_sg`
21. `ModNom_m_pl → Adj_m_pl`
22. `ModNom_m_pl → adv_intens Adj_m_pl`
23. `ModNom_m_pl → ε`
24. `Adj_m_pl → adj_m_pl`
25. `Adj_m_pl → adj_inv_pl`
26. `ModNom_f_pl → Adj_f_pl`
27. `ModNom_f_pl → adv_intens Adj_f_pl`
28. `ModNom_f_pl → ε`
29. `Adj_f_pl → adj_f_pl`
30. `Adj_f_pl → adj_inv_pl`
31. `SubOpt_sg → que SV_sg`
32. `SubOpt_sg → ε`
33. `SubOpt_pl → que SV_pl`
34. `SubOpt_pl → ε`
35. `SV_sg → v_sg RestoSV`
36. `SV_pl → v_pl RestoSV`
37. `RestoSV → que Clausula`
38. `RestoSV → AdvOpt SPOpt`
39. `Clausula → Sujeto_sg SV_sg`
40. `Clausula → Sujeto_pl SV_pl`
41. `AdvOpt → adv_modo`
42. `AdvOpt → ε`
43. `SPOpt → prep SN_Prep`
44. `SPOpt → ε`
45. `SN_Prep → SN_m_sg`
46. `SN_Prep → SN_f_sg`
47. `SN_Prep → SN_m_pl`
48. `SN_Prep → SN_f_pl`

### Conjuntos FIRST y FOLLOW

| No terminal | FIRST | FOLLOW |
|---|---|---|
| `Oracion` | `{ det_m_sg, det_f_sg, det_m_pl, det_f_pl }` | `{ $ }` |
| `Sujeto_sg` | `{ det_m_sg, det_f_sg }` | `{ v_sg }` |
| `Sujeto_pl` | `{ det_m_pl, det_f_pl }` | `{ v_pl }` |
| `SN_m_sg` | `{ det_m_sg }` | `{ v_sg, v_pl, que, . }` |
| `SN_f_sg` | `{ det_f_sg }` | `{ v_sg, v_pl, que, . }` |
| `SN_m_pl` | `{ det_m_pl }` | `{ v_sg, v_pl, que, . }` |
| `SN_f_pl` | `{ det_f_pl }` | `{ v_sg, v_pl, que, . }` |
| `ModNom_m_sg` | `{ adj_m_sg, adj_inv_sg, adv_intens, ε }` | `{ v_sg, v_pl, que, . }` |
| `Adj_m_sg` | `{ adj_m_sg, adj_inv_sg }` | `{ v_sg, v_pl, que, . }` |
| `ModNom_f_sg` | `{ adj_f_sg, adj_inv_sg, adv_intens, ε }` | `{ v_sg, v_pl, que, . }` |
| `Adj_f_sg` | `{ adj_f_sg, adj_inv_sg }` | `{ v_sg, v_pl, que, . }` |
| `ModNom_m_pl` | `{ adj_m_pl, adj_inv_pl, adv_intens, ε }` | `{ v_sg, v_pl, que, . }` |
| `Adj_m_pl` | `{ adj_m_pl, adj_inv_pl }` | `{ v_sg, v_pl, que, . }` |
| `ModNom_f_pl` | `{ adj_f_pl, adj_inv_pl, adv_intens, ε }` | `{ v_sg, v_pl, que, . }` |
| `Adj_f_pl` | `{ adj_f_pl, adj_inv_pl }` | `{ v_sg, v_pl, que, . }` |
| `SubOpt_sg` | `{ que, ε }` | `{ v_sg }` |
| `SubOpt_pl` | `{ que, ε }` | `{ v_pl }` |
| `SV_sg` | `{ v_sg }` | `{ v_sg, v_pl, . }` |
| `SV_pl` | `{ v_pl }` | `{ v_sg, v_pl, . }` |
| `RestoSV` | `{ adv_modo, prep, que, ε }` | `{ v_sg, v_pl, . }` |
| `Clausula` | `{ det_m_sg, det_f_sg, det_m_pl, det_f_pl }` | `{ v_sg, v_pl, . }` |
| `AdvOpt` | `{ adv_modo, ε }` | `{ v_sg, v_pl, prep, . }` |
| `SPOpt` | `{ prep, ε }` | `{ v_sg, v_pl, . }` |
| `SN_Prep` | `{ det_m_sg, det_f_sg, det_m_pl, det_f_pl }` | `{ v_sg, v_pl, . }` |

### Tabla predictiva LL(1)

Cada fila es una celda activa `M[A, a] = producción`.

| No terminal | Anticipación | Producción |
|---|---|---|
| `Oracion` | `det_m_sg` | 1. `Oracion → Sujeto_sg SV_sg .` |
| `Oracion` | `det_f_sg` | 1. `Oracion → Sujeto_sg SV_sg .` |
| `Oracion` | `det_m_pl` | 2. `Oracion → Sujeto_pl SV_pl .` |
| `Oracion` | `det_f_pl` | 2. `Oracion → Sujeto_pl SV_pl .` |
| `Sujeto_sg` | `det_m_sg` | 3. `Sujeto_sg → SN_m_sg SubOpt_sg` |
| `Sujeto_sg` | `det_f_sg` | 4. `Sujeto_sg → SN_f_sg SubOpt_sg` |
| `Sujeto_pl` | `det_m_pl` | 5. `Sujeto_pl → SN_m_pl SubOpt_pl` |
| `Sujeto_pl` | `det_f_pl` | 6. `Sujeto_pl → SN_f_pl SubOpt_pl` |
| `SN_m_sg` | `det_m_sg` | 7. `SN_m_sg → det_m_sg n_m_sg ModNom_m_sg` |
| `SN_f_sg` | `det_f_sg` | 8. `SN_f_sg → det_f_sg n_f_sg ModNom_f_sg` |
| `SN_m_pl` | `det_m_pl` | 9. `SN_m_pl → det_m_pl n_m_pl ModNom_m_pl` |
| `SN_f_pl` | `det_f_pl` | 10. `SN_f_pl → det_f_pl n_f_pl ModNom_f_pl` |
| `ModNom_m_sg` | `adj_m_sg` | 11. `ModNom_m_sg → Adj_m_sg` |
| `ModNom_m_sg` | `adj_inv_sg` | 11. `ModNom_m_sg → Adj_m_sg` |
| `ModNom_m_sg` | `v_sg` | 13. `ModNom_m_sg → ε` |
| `ModNom_m_sg` | `v_pl` | 13. `ModNom_m_sg → ε` |
| `ModNom_m_sg` | `adv_intens` | 12. `ModNom_m_sg → adv_intens Adj_m_sg` |
| `ModNom_m_sg` | `que` | 13. `ModNom_m_sg → ε` |
| `ModNom_m_sg` | `.` | 13. `ModNom_m_sg → ε` |
| `Adj_m_sg` | `adj_m_sg` | 14. `Adj_m_sg → adj_m_sg` |
| `Adj_m_sg` | `adj_inv_sg` | 15. `Adj_m_sg → adj_inv_sg` |
| `ModNom_f_sg` | `adj_f_sg` | 16. `ModNom_f_sg → Adj_f_sg` |
| `ModNom_f_sg` | `adj_inv_sg` | 16. `ModNom_f_sg → Adj_f_sg` |
| `ModNom_f_sg` | `v_sg` | 18. `ModNom_f_sg → ε` |
| `ModNom_f_sg` | `v_pl` | 18. `ModNom_f_sg → ε` |
| `ModNom_f_sg` | `adv_intens` | 17. `ModNom_f_sg → adv_intens Adj_f_sg` |
| `ModNom_f_sg` | `que` | 18. `ModNom_f_sg → ε` |
| `ModNom_f_sg` | `.` | 18. `ModNom_f_sg → ε` |
| `Adj_f_sg` | `adj_f_sg` | 19. `Adj_f_sg → adj_f_sg` |
| `Adj_f_sg` | `adj_inv_sg` | 20. `Adj_f_sg → adj_inv_sg` |
| `ModNom_m_pl` | `adj_m_pl` | 21. `ModNom_m_pl → Adj_m_pl` |
| `ModNom_m_pl` | `adj_inv_pl` | 21. `ModNom_m_pl → Adj_m_pl` |
| `ModNom_m_pl` | `v_sg` | 23. `ModNom_m_pl → ε` |
| `ModNom_m_pl` | `v_pl` | 23. `ModNom_m_pl → ε` |
| `ModNom_m_pl` | `adv_intens` | 22. `ModNom_m_pl → adv_intens Adj_m_pl` |
| `ModNom_m_pl` | `que` | 23. `ModNom_m_pl → ε` |
| `ModNom_m_pl` | `.` | 23. `ModNom_m_pl → ε` |
| `Adj_m_pl` | `adj_m_pl` | 24. `Adj_m_pl → adj_m_pl` |
| `Adj_m_pl` | `adj_inv_pl` | 25. `Adj_m_pl → adj_inv_pl` |
| `ModNom_f_pl` | `adj_f_pl` | 26. `ModNom_f_pl → Adj_f_pl` |
| `ModNom_f_pl` | `adj_inv_pl` | 26. `ModNom_f_pl → Adj_f_pl` |
| `ModNom_f_pl` | `v_sg` | 28. `ModNom_f_pl → ε` |
| `ModNom_f_pl` | `v_pl` | 28. `ModNom_f_pl → ε` |
| `ModNom_f_pl` | `adv_intens` | 27. `ModNom_f_pl → adv_intens Adj_f_pl` |
| `ModNom_f_pl` | `que` | 28. `ModNom_f_pl → ε` |
| `ModNom_f_pl` | `.` | 28. `ModNom_f_pl → ε` |
| `Adj_f_pl` | `adj_f_pl` | 29. `Adj_f_pl → adj_f_pl` |
| `Adj_f_pl` | `adj_inv_pl` | 30. `Adj_f_pl → adj_inv_pl` |
| `SubOpt_sg` | `v_sg` | 32. `SubOpt_sg → ε` |
| `SubOpt_sg` | `que` | 31. `SubOpt_sg → que SV_sg` |
| `SubOpt_pl` | `v_pl` | 34. `SubOpt_pl → ε` |
| `SubOpt_pl` | `que` | 33. `SubOpt_pl → que SV_pl` |
| `SV_sg` | `v_sg` | 35. `SV_sg → v_sg RestoSV` |
| `SV_pl` | `v_pl` | 36. `SV_pl → v_pl RestoSV` |
| `RestoSV` | `v_sg` | 38. `RestoSV → AdvOpt SPOpt` |
| `RestoSV` | `v_pl` | 38. `RestoSV → AdvOpt SPOpt` |
| `RestoSV` | `adv_modo` | 38. `RestoSV → AdvOpt SPOpt` |
| `RestoSV` | `prep` | 38. `RestoSV → AdvOpt SPOpt` |
| `RestoSV` | `que` | 37. `RestoSV → que Clausula` |
| `RestoSV` | `.` | 38. `RestoSV → AdvOpt SPOpt` |
| `Clausula` | `det_m_sg` | 39. `Clausula → Sujeto_sg SV_sg` |
| `Clausula` | `det_f_sg` | 39. `Clausula → Sujeto_sg SV_sg` |
| `Clausula` | `det_m_pl` | 40. `Clausula → Sujeto_pl SV_pl` |
| `Clausula` | `det_f_pl` | 40. `Clausula → Sujeto_pl SV_pl` |
| `AdvOpt` | `v_sg` | 42. `AdvOpt → ε` |
| `AdvOpt` | `v_pl` | 42. `AdvOpt → ε` |
| `AdvOpt` | `adv_modo` | 41. `AdvOpt → adv_modo` |
| `AdvOpt` | `prep` | 42. `AdvOpt → ε` |
| `AdvOpt` | `.` | 42. `AdvOpt → ε` |
| `SPOpt` | `v_sg` | 44. `SPOpt → ε` |
| `SPOpt` | `v_pl` | 44. `SPOpt → ε` |
| `SPOpt` | `prep` | 43. `SPOpt → prep SN_Prep` |
| `SPOpt` | `.` | 44. `SPOpt → ε` |
| `SN_Prep` | `det_m_sg` | 45. `SN_Prep → SN_m_sg` |
| `SN_Prep` | `det_f_sg` | 46. `SN_Prep → SN_f_sg` |
| `SN_Prep` | `det_m_pl` | 47. `SN_Prep → SN_m_pl` |
| `SN_Prep` | `det_f_pl` | 48. `SN_Prep → SN_f_pl` |
