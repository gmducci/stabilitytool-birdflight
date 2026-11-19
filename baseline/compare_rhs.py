#!/usr/bin/env python
"""Fast check: bird right-hand side of the package vs the upstream tag.

Evaluates, for the upstream code (tag ``upstream-v1.1``, extracted with
``git archive``) and for the package ``stabilitytool_birdflight``, at the same
states and times:

* ``get_aeroforces(x, t)`` (all nine outputs),
* ``dynamics(x, t)``,
* ``get_stability_matrix(x, t)``,

and reports the largest absolute and relative differences. The solver is
deterministic, so bitwise-identical right-hand sides imply bitwise-identical
limit cycles: this takes seconds instead of the ~15 minutes of the full bird
regression (``generate_baseline.py --target package``), which remains the
reference check at the end of each stage.

States: points on the stored ``bird_study1`` and ``bird_main`` limit cycles
plus perturbed off-cycle states, for A_s,x = 42 and 44 deg.

Usage (from the repository root)::

    python baseline/compare_rhs.py            # exit status 1 if not identical
    python baseline/compare_rhs.py --rtol 1e-12
"""
from __future__ import annotations

import argparse
import contextlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
UPSTREAM_TAG = "upstream-v1.1"


def joints(Joint, Shoulder, Elbow, Wrist, amp_deg):
    d = np.deg2rad
    return dict(
        shoulder=Shoulder(axis_x=Joint(0.2, 0.014, -np.pi / 2),
                          axis_y=Joint(-d(19), d(20), np.pi / 2),
                          axis_z=Joint(0, d(amp_deg), np.pi)),
        elbow=Elbow(axis_x=Joint(0., np.pi / 6, -np.pi / 2),
                    axis_y=Joint(np.pi / 6, np.pi / 6, -np.pi / 2)),
        wrist=Wrist(axis_y=Joint(-np.pi / 6, np.pi / 6, np.pi / 2),
                    axis_z=Joint(0., 0., 0.)),
    )


def upstream_birds(upstream_dir):
    sys.path.insert(0, str(upstream_dir / "multiflap"))
    from aero_package.bird_model import BirdModel
    from aero_package.bird import Shoulder, Elbow, Wrist, Joint
    return {a: BirdModel(**joints(Joint, Shoulder, Elbow, Wrist, a)) for a in (42, 44)}


def package_birds():
    try:
        import stabilitytool_birdflight  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(REPO / "src"))
    from stabilitytool_birdflight.flight.bird_model import BirdModel
    from stabilitytool_birdflight.kinematics.bird import Shoulder, Elbow, Wrist, Joint
    return {a: BirdModel(**joints(Joint, Shoulder, Elbow, Wrist, a)) for a in (42, 44)}


def sample_points(n_per_cycle):
    pts = []
    for case, amp in (("bird_study1", 42), ("bird_main", 44)):
        d = np.load(REPO / "baseline" / "data" / f"{case}.npz")
        t, x = d["trajectory_t"], d["trajectory_x"]
        idx = np.linspace(0, len(t) - 1, n_per_cycle).astype(int)
        for k in idx:
            pts.append((amp, x[k].copy(), float(t[k])))
        # off-cycle states
        rng = np.random.default_rng(0)
        for k in idx[::2]:
            pts.append((amp, x[k] * (1 + 0.05 * rng.standard_normal(4)), float(t[k])))
    return pts


def evaluate(birds, pts):
    out = []
    with contextlib.redirect_stdout(io.StringIO()):
        for amp, x, t in pts:
            b = birds[amp]
            out.append(dict(
                forces=np.array(b.get_aeroforces(x, t), float),
                dynamics=np.asarray(b.dynamics(x, t), float),
                stability=np.asarray(b.get_stability_matrix(x, t), float),
            ))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rtol", type=float, default=0.0,
                   help="relative tolerance (default 0: bitwise)")
    p.add_argument("--points", type=int, default=8, help="points per cycle")
    args = p.parse_args(argv)

    pts = sample_points(args.points)
    with tempfile.TemporaryDirectory() as tmp:
        archive = subprocess.run(["git", "archive", UPSTREAM_TAG, "multiflap"],
                                 cwd=REPO, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
        ref = evaluate(upstream_birds(Path(tmp)), pts)
    cand = evaluate(package_birds(), pts)

    ok = True
    for key in ("forces", "dynamics", "stability"):
        a = np.array([c[key] for c in cand])
        b = np.array([r[key] for r in ref])
        absd = np.max(np.abs(a - b))
        reld = absd / np.max(np.abs(b))
        passed = reld <= args.rtol
        ok &= passed
        print(f"{key:10s} max abs diff {absd:.3e}  rel {reld:.3e}  "
              f"{'ok' if passed else 'FAIL'}")
    print(f"{len(pts)} evaluation points; " + ("IDENTICAL" if ok and args.rtol == 0
                                                 else "PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
