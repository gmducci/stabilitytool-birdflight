"""End-to-end bird regression through the run machinery (slow, ~5 min per case).

Every bird case of the Stage 1 baseline is run from its config file with
``run_bird_case`` and compared with ``baseline/data``.

Run with:  uv run pytest -m slow
"""
from pathlib import Path

import numpy as np
import pytest

from stabilitytool_birdflight.dynamics.result import LimitCycleResult
from stabilitytool_birdflight.runs import run_bird_case

ROOT = Path(__file__).resolve().parents[1]
RTOL = 1e-8   # baseline/compare_baseline.py

# (config file in examples/configs, baseline case in baseline/data)
CASES = [
    ("bird_main.yaml", "bird_main"),
    ("bird_study1_reference.yaml", "bird_study1"),
    ("bird_a42_main_numerics.yaml", "bird_a42_main_numerics"),
]


def rel(a, b):
    return np.max(np.abs(np.asarray(a) - np.asarray(b))) / np.max(np.abs(np.asarray(b)))


@pytest.mark.slow
@pytest.mark.parametrize("config,baseline", CASES, ids=[c[1] for c in CASES])
def test_bird_case_from_config_file(tmp_path, config, baseline):
    run_bird_case(ROOT / "examples" / "configs" / config, tmp_path / "run")
    res = LimitCycleResult.from_npz(tmp_path / "run" / "result.npz")
    ref = np.load(ROOT / "baseline" / "data" / f"{baseline}.npz")
    assert res.converged
    assert res.n_iterations == int(ref["n_iterations"])
    assert res.period == pytest.approx(float(ref["period"]), rel=RTOL)
    for name, ref_name in [("points", "points"), ("monodromy", "monodromy"),
                           ("multipliers", "multipliers_sorted"),
                           ("trajectory_t", "trajectory_t"),
                           ("trajectory_x", "trajectory_x")]:
        assert rel(getattr(res, name), ref[ref_name]) <= RTOL, name
