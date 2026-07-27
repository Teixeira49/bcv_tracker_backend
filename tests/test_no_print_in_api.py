"""Guardrail de logging (issue #26).

El proyecto usa logging estructurado (``api/core/logging/logger.py``), no
``print()``. Este test recorre todo el paquete ``api/`` y falla si aparece una
llamada a ``print(...)``, para que ninguna implementación nueva reintroduzca el
patrón. Se apoya en el AST (no en un grep textual), así que no se confunde con
la palabra ``print`` dentro de strings/comentarios ni con ``traceback.print_exc``
(que es un atributo, no la builtin ``print``).

Ver la convención en ``.agents/rules/logging-convention.md``.
"""
import ast
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent / "api"


def _print_calls(tree):
    """Devuelve las líneas donde se llama a la builtin ``print(...)``."""
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            lines.append(node.lineno)
    return lines


def test_no_print_calls_in_api():
    offenders = []
    for path in API_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line in _print_calls(tree):
            offenders.append(f"{path.relative_to(API_ROOT.parent)}:{line}")

    assert not offenders, (
        "Usa logging estructurado (api/core/logging/logger.py), no print(). "
        "Ocurrencias encontradas: " + ", ".join(offenders)
    )
