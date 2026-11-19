"""End-to-end bird regression through the run machinery (slow, ~5 min).

Run with:  uv run pytest -m slow
"""
from pathlib import Path

import numpy as np
import pytest

from stabilitytool_birdflight.dynamics.result import LimitCycleResult
from stabilitytool_birdflight.runs import run_bird_case

ROOT = Path(__file__).resolve().parents[1]
RTOL = 1e-8   # baseline/compare_baseline.py


def rel(a, b):
    return np.max(np.abs(np.asarray(a) - np.asarray(b))) / np.max(np.abs(np.asarray(b)))


@pytest.mark.slow
def test_bird_main_from_config_file(tmp_path):
    run_bird_case(ROOT / "examples" / "configs" / "bird_main.yaml", tmp_path / "run")
    res = LimitCycleResult.from_npz(tmp_path / "run" / "result.npz")
    ref = np.load(ROOT / "baseline" / "data" / "bird_main.npz")
    assert res.n_iterations == int(ref["n_iterations"])
    for name, ref_name in [("points", "points"), ("monodromy", "monodromy"),
                           ("multipliers", "multipliers_sorted"),
                           ("trajectory_x", "trajectory_x")]:
        assert rel(getattr(res, name), ref[ref_name]) <= RTOL, name
