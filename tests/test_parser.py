"""Pruebas del parser LL(1).

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -t . -v
"""
import unittest
from pathlib import Path

from parser.grammar import FIRST, FOLLOW, EPSILON, END, NONTERMINALS, TABLE
from parser.lexer import LexError, tokenize
from parser.parser import ParseError, accepts, parse
from parser.tree import build_ast, format_ast, format_expr

TESTS_DIR = Path(__file__).parent


def _files(folder: str):
    return sorted((TESTS_DIR / folder).glob("*.cpp"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class GrammarTests(unittest.TestCase):
    """La gramática debe ser LL(1) y coincidir con el documento de diseño."""

    def test_first_sets(self):
        esperado = {
            "Program": {"int", "id", "cout"},
            "StmtList": {"int", "id", "cout", EPSILON},
            "Stmt": {"int", "id", "cout"},
            "DeclTail": {";", "="},
            "Expr": {"id", "num", "("},
            "ExprTail": {"+", "-", EPSILON},
            "Term": {"id", "num", "("},
            "TermTail": {"*", "/", EPSILON},
            "Factor": {"id", "num", "("},
        }
        self.assertEqual(FIRST, esperado)

    def test_follow_sets(self):
        esperado = {
            "Program": {END},
            "StmtList": {END},
            "Stmt": {"int", "id", "cout", END},
            "DeclTail": {"int", "id", "cout", END},
            "Expr": {";", ")"},
            "ExprTail": {";", ")"},
            "Term": {"+", "-", ";", ")"},
            "TermTail": {"+", "-", ";", ")"},
            "Factor": {"*", "/", "+", "-", ";", ")"},
        }
        self.assertEqual(FOLLOW, esperado)

    def test_table_has_no_conflicts_and_covers_all_nonterminals(self):
        # build_table() lanza GrammarError al importar si hubiera un conflicto.
        self.assertEqual(set(TABLE), set(NONTERMINALS))
        self.assertTrue(all(row for row in TABLE.values()))


class LexerTests(unittest.TestCase):
    def types(self, src):
        return [t.type for t in tokenize(src)]

    def test_shift_is_a_single_token(self):
        self.assertEqual(self.types("cout << x;"), ["cout", "<<", "id", ";", "$"])

    def test_keywords_vs_identifiers(self):
        self.assertEqual(self.types("int integer;"), ["int", "id", ";", "$"])
        self.assertEqual(self.types("coutx"), ["id", "$"])

    def test_numbers_and_operators(self):
        self.assertEqual(self.types("1+2*(3-4)/5"),
                         ["num", "+", "num", "*", "(", "num", "-", "num", ")", "/", "num", "$"])

    def test_positions(self):
        toks = tokenize("int a;\n  b = 1;")
        b = next(t for t in toks if t.value == "b")
        self.assertEqual((b.line, b.col), (2, 3))

    def test_invalid_characters(self):
        for src in ("x = 3 @ 4;", "cout < 3;", "x = 3abc;"):
            with self.subTest(src=src):
                with self.assertRaises(LexError):
                    tokenize(src)


class AcceptRejectTests(unittest.TestCase):
    """Entrada válida -> acepta ✓ ; entrada inválida -> rechaza ✗."""

    def test_valid_files_are_accepted(self):
        archivos = _files("valid")
        self.assertGreater(len(archivos), 0)
        for path in archivos:
            with self.subTest(archivo=path.name):
                parse(_read(path))  # no debe lanzar excepción

    def test_invalid_files_are_rejected(self):
        archivos = _files("invalid")
        self.assertGreater(len(archivos), 0)
        for path in archivos:
            with self.subTest(archivo=path.name):
                self.assertFalse(accepts(_read(path)))

    def test_cases_from_design_document(self):
        validos = ["int edad;", "int edad = 20;", "int total = 3 + 4 * 2;",
                   "total = (3 + 4) * 2;", "cout << total;", "cout << 3 + 4;"]
        invalidos = ["int edad = ;", "total = 5", "total = 3 + * 2;", "cout << (3 + 4;"]
        for src in validos:
            with self.subTest(src=src):
                self.assertTrue(accepts(src))
        for src in invalidos:
            with self.subTest(src=src):
                self.assertFalse(accepts(src))


class ErrorReportingTests(unittest.TestCase):
    def error(self, src) -> ParseError:
        with self.assertRaises(ParseError) as ctx:
            parse(src)
        return ctx.exception

    def test_missing_semicolon_reported_at_end_of_input(self):
        err = self.error("total = 5")
        self.assertIn("fin de la entrada", err.message)
        self.assertIn("';'", err.message)

    def test_unclosed_parenthesis(self):
        err = self.error("cout << (3 + 4;")
        self.assertIn("')'", err.message)
        self.assertEqual((err.line, err.col), (1, 15))

    def test_error_on_second_line(self):
        err = self.error("int a;\nint = 3;")
        self.assertEqual(err.line, 2)

    def test_trace_records_steps(self):
        pasos = []
        parse("int x;", trace=pasos)
        self.assertEqual(pasos[0][3], "Expandir Program → Stmt StmtList")
        self.assertEqual(pasos[-1][3], "Aceptar")


class TreeTests(unittest.TestCase):
    def ast_expr(self, src):
        return format_expr(build_ast(parse(f"x = {src};"))[1][0][2])

    def test_precedence(self):
        self.assertEqual(self.ast_expr("1 + 2 * 3"), "(+ 1 (* 2 3))")
        self.assertEqual(self.ast_expr("(1 + 2) * 3"), "(* (+ 1 2) 3)")

    def test_left_associativity(self):
        self.assertEqual(self.ast_expr("10 - 3 - 2"), "(- (- 10 3) 2)")
        self.assertEqual(self.ast_expr("8 / 4 / 2"), "(/ (/ 8 4) 2)")

    def test_parse_tree_shape(self):
        root = parse("int edad;")
        self.assertEqual(root.symbol, "Program")
        stmt = root.children[0]
        self.assertEqual([c.symbol for c in stmt.children], ["int", "id", "DeclTail"])
        self.assertEqual(stmt.children[1].token.value, "edad")

    def test_full_program_ast(self):
        ast = build_ast(parse(_read(TESTS_DIR / "valid" / "07_programa_completo.cpp")))
        self.assertEqual(format_ast(ast).splitlines(), [
            "decl   edad = 20",
            "decl   resultado = (+ edad (* 5 2))",
            "assign resultado = (/ (- resultado 3) 2)",
            "print  resultado",
        ])


if __name__ == "__main__":
    unittest.main()
