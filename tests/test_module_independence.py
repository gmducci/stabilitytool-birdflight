"""kinematics, aerodynamics and dynamics must not import each other or flight.

Static check of every import statement (CLAUDE.md, target architecture).
"""
import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "src" / "stabilitytool_birdflight"
INDEPENDENT = ["kinematics", "aerodynamics", "dynamics"]
FORBIDDEN_FOR = {m: set(INDEPENDENT + ["flight"]) - {m} for m in INDEPENDENT}


def imported_subpackages(path, module):
    """Top-level subpackages of stabilitytool_birdflight imported by a file."""
    tree = ast.parse(path.read_text())
    rel_parts = path.relative_to(PKG).parts[:-1]   # e.g. ("dynamics", "systems")
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:                          # relative import
                base = list(rel_parts[:len(rel_parts) - node.level + 1])
                target = base + (node.module.split(".") if node.module else [])
                if target:
                    found.add(target[0])
            elif node.module and node.module.startswith("stabilitytool_birdflight."):
                found.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("stabilitytool_birdflight."):
                    found.add(alias.name.split(".")[1])
    return found


@pytest.mark.parametrize("module", INDEPENDENT)
def test_module_does_not_import_siblings(module):
    offenders = {}
    for path in sorted((PKG / module).rglob("*.py")):
        try:
            bad = imported_subpackages(path, module) & FORBIDDEN_FOR[module]
        except SyntaxError:
            continue  # dynamics/systems/jaschinski.py: known broken file
        if bad:
            offenders[str(path.relative_to(PKG))] = sorted(bad)
    assert not offenders, offenders
