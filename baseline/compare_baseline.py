#!/usr/bin/env python
"""Compare a set of case outputs against the Stage 1 baseline.

Usage (from the repository root)::

    python baseline/compare_baseline.py CANDIDATE_DIR [--ref baseline/data]
                                        [--cases rossler bird_main ...]

Both directories hold ``<case>.npz`` files with the fields written by
``generate_baseline.py``. For every array field the norm-wise relative
difference ``max|a - b| / max|b|`` is reported. The fields in ``ENFORCED`` must
be within the case tolerance, and ``n_iterations`` must match exactly. Other
fields are reported for information only. Exit status is 1 if any enforced
check fails or a case is missing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]

# Relative tolerances (CLAUDE.md, Section 5, Stage 1). Bird cases started at
# 1e-6; two independent runs were bitwise identical, so they are tightened to
# 1e-8 like the toy systems (see baseline/README.md). Relax only with a reason.
# redox: relaxed to 1e-6 in Stage 2. Its result moves by 2.2e-7 under a 1e-15
# relative perturbation of x0 on the baseline environment itself (adaptive
# odeint, default rtol 1.49e-8), and by 1.8e-7 with numpy 2.5.5 + Accelerate.
TOLERANCES = {
    "rossler": 1e-8,
    "redox": 1e-6,
    "forced_vdp": 1e-8,
    "lorenz": 1e-8,
    "bird_main": 1e-8,
    "bird_study1": 1e-8,
    "bird_a42_main_numerics": 1e-8,
}
ENFORCED = ["points", "period", "monodromy", "multipliers_sorted",
            "trajectory_t", "trajectory_x"]
INFORMATIVE = ["error_history", "final_error", "points_history"]


def rel_diff(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return np.inf
    scale = np.max(np.abs(b)) if b.size else 0.0
    diff = np.max(np.abs(a - b)) if b.size else 0.0
    if scale == 0.0:
        return 0.0 if diff == 0.0 else np.inf
    return float(diff / scale)


def compare_case(name, cand_dir, ref_dir, rtol):
    ref_f, cand_f = ref_dir / f"{name}.npz", cand_dir / f"{name}.npz"
    if not ref_f.exists() or not cand_f.exists():
        missing = ref_f if not ref_f.exists() else cand_f
        print(f"[{name}] MISSING {missing}")
        return False
    ref, cand = np.load(ref_f), np.load(cand_f)
    ok = True
    print(f"[{name}] rtol = {rtol:g}")
    it_ref, it_cand = int(ref["n_iterations"]), int(cand["n_iterations"])
    it_ok = it_ref == it_cand
    ok &= it_ok
    print(f"    {'n_iterations':20s} {it_cand} vs {it_ref}  "
          f"{'ok' if it_ok else 'FAIL'}")
    for field in ENFORCED:
        d = rel_diff(cand[field], ref[field])
        passed = d <= rtol
        ok &= passed
        print(f"    {field:20s} {d:.3e}  {'ok' if passed else 'FAIL'}")
    for field in INFORMATIVE:
        d = rel_diff(cand[field], ref[field])
        print(f"    {field:20s} {d:.3e}  (info)")
    return ok


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("candidate")
    p.add_argument("--ref", default=str(REPO / "baseline" / "data"))
    p.add_argument("--cases", nargs="+", default=None)
    p.add_argument("--rtol", type=float, default=None,
                   help="override the per-case tolerance")
    args = p.parse_args(argv)
    cand_dir, ref_dir = Path(args.candidate), Path(args.ref)
    cases = args.cases or sorted(f.stem for f in ref_dir.glob("*.npz"))
    results = {c: compare_case(c, cand_dir, ref_dir,
                               args.rtol if args.rtol is not None
                               else TOLERANCES.get(c, 1e-8))
               for c in cases}
    failed = [c for c, ok in results.items() if not ok]
    print("ALL PASSED" if not failed else "FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
