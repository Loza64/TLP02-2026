"""Ejecuta los ejemplos de examples/ y muestra, para cada uno, si el parser acepta o rechaza.

    python run_examples.py

Cada línea de examples/valid_examples.txt debe ser aceptada y cada línea de
examples/invalid_examples.txt debe ser rechazada. Termina con código 1 si algo no se cumple.
"""
import sys
from pathlib import Path

from parser.lexer import LanguageError
from parser.parser import parse

ROOT = Path(__file__).parent


def casos(nombre: str) -> list[str]:
    texto = (ROOT / "examples" / nombre).read_text(encoding="utf-8")
    return [l.strip() for l in texto.splitlines() if l.strip() and not l.startswith("//")]


def evaluar(src: str) -> tuple[bool, str]:
    try:
        parse(src)
        return True, ""
    except LanguageError as err:
        return False, str(err)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fallos = 0
    for archivo, esperado in (("valid_examples.txt", True), ("invalid_examples.txt", False)):
        print(f"\n== {archivo} (se espera: {'ACEPTAR' if esperado else 'RECHAZAR'}) ==")
        for src in casos(archivo):
            aceptado, motivo = evaluar(src)
            ok = aceptado == esperado
            fallos += not ok
            marca = "✓ acepta " if aceptado else "✗ rechaza"
            detalle = f"   -> {motivo}" if motivo else ""
            print(f"  {marca} | {src:<28}{'' if ok else '  ¡RESULTADO INESPERADO!'}{detalle}")
    print(f"\n{'Todos los casos de C++ se comportan como se esperaba.' if not fallos else f'{fallos} caso(s) inesperados.'}")

    from espanol.parser import run_demo
    print("\n---- Extensión al español ----")
    return 1 if fallos or run_demo() else 0


if __name__ == "__main__":
    sys.exit(main())
