"""The quick examples run and reach the expected limit cycle (a few seconds each).

The bird example (about 5 minutes) is covered by the slow regression suite
through the same API (BirdCaseConfig, find_limit_cycle).
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

# example -> (expected period as printed by summary(), relative tolerance).
# Redox is sensitive to roundoff across numpy/BLAS builds (about 1e-7, see
# baseline/README.md), hence the same 1e-6 as its regression tolerance.
CASES = {
    "rossler.py": (5.881088559, 1e-9),
    "redox.py": (24.95255998, 1e-6),
    "forced_van_der_pol.py": (10.4719755, 1e-9),
    "isothermal_reaction.py": (0.6849517251, 1e-9),
}


@pytest.mark.parametrize("name,expected", CASES.items(), ids=list(CASES))
def test_example_runs(name, expected, tmp_path):
    period, rtol = expected
    out = subprocess.run([sys.executable, str(EXAMPLES / name), "--figure",
                          str(tmp_path / "fig.png")], capture_output=True, text=True,
                         cwd=tmp_path, env={"MPLBACKEND": "Agg", "PATH": ""}, check=True)
    assert "converged" in out.stdout
    found = float(re.search(r"^period\s+(\S+)", out.stdout, re.M).group(1))
    assert found == pytest.approx(period, rel=rtol)
    assert (tmp_path / "fig.png").stat().st_size > 0
