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

# example -> expected period (10 significant digits, as printed by summary())
CASES = {
    "rossler.py": 5.881088559,
    "redox.py": 24.95255998,
    "forced_van_der_pol.py": 10.4719755,
    "isothermal_reaction.py": 0.6849517251,
}


@pytest.mark.parametrize("name,period", CASES.items(), ids=list(CASES))
def test_example_runs(name, period, tmp_path):
    out = subprocess.run([sys.executable, str(EXAMPLES / name), "--figure",
                          str(tmp_path / "fig.png")], capture_output=True, text=True,
                         cwd=tmp_path, env={"MPLBACKEND": "Agg", "PATH": ""}, check=True)
    assert "converged" in out.stdout
    found = float(re.search(r"^period\s+(\S+)", out.stdout, re.M).group(1))
    assert found == pytest.approx(period, rel=1e-9)
    assert (tmp_path / "fig.png").stat().st_size > 0
