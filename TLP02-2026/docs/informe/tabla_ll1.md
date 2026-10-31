### Producciones

1. `Program → Stmt StmtList`
2. `StmtList → Stmt StmtList`
3. `StmtList → ε`
4. `Stmt → int id DeclTail`
5. `Stmt → id = Expr ;`
6. `Stmt → cout << Expr ;`
7. `DeclTail → ;`
8. `DeclTail → = Expr ;`
9. `Expr → Term ExprTail`
10. `ExprTail → + Term ExprTail`
11. `ExprTail → - Term ExprTail`
12. `ExprTail → ε`
13. `Term → Factor TermTail`
14. `TermTail → * Factor TermTail`
15. `TermTail → / Factor TermTail`
16. `TermTail → ε`
17. `Factor → id`
18. `Factor → num`
19. `Factor → ( Expr )`

### Conjuntos FIRST y FOLLOW

| No terminal | FIRST | FOLLOW |
|---|---|---|
| `Program` | `{ int, id, cout }` | `{ $ }` |
| `StmtList` | `{ int, id, cout, ε }` | `{ $ }` |
| `Stmt` | `{ int, id, cout }` | `{ int, id, cout, $ }` |
| `DeclTail` | `{ =, ; }` | `{ int, id, cout, $ }` |
| `Expr` | `{ id, num, ( }` | `{ ;, ) }` |
| `ExprTail` | `{ +, -, ε }` | `{ ;, ) }` |
| `Term` | `{ id, num, ( }` | `{ ;, +, -, ) }` |
| `TermTail` | `{ *, /, ε }` | `{ ;, +, -, ) }` |
| `Factor` | `{ id, num, ( }` | `{ ;, +, -, *, /, ) }` |

### Tabla predictiva LL(1)

Cada celda contiene el número de la producción a aplicar; vacío = error sintáctico.

| | `int` | `id` | `num` | `cout` | `<<` | `=` | `;` | `+` | `-` | `*` | `/` | `(` | `)` | `$` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Program** | 1 | 1 |  | 1 |  |  |  |  |  |  |  |  |  |  |
| **StmtList** | 2 | 2 |  | 2 |  |  |  |  |  |  |  |  |  | 3 |
| **Stmt** | 4 | 5 |  | 6 |  |  |  |  |  |  |  |  |  |  |
| **DeclTail** |  |  |  |  |  | 8 | 7 |  |  |  |  |  |  |  |
| **Expr** |  | 9 | 9 |  |  |  |  |  |  |  |  | 9 |  |  |
| **ExprTail** |  |  |  |  |  |  | 12 | 10 | 11 |  |  |  | 12 |  |
| **Term** |  | 13 | 13 |  |  |  |  |  |  |  |  | 13 |  |  |
| **TermTail** |  |  |  |  |  |  | 16 | 16 | 16 | 14 | 15 |  | 16 |  |
| **Factor** |  | 17 | 18 |  |  |  |  |  |  |  |  | 19 |  |  |
