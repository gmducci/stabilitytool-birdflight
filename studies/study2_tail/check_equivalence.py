"""Check that forces.py with every switch off equals the package bitwise (seconds).

Evaluates forces, dynamics and Jacobian of the study_2 bird along the stored
study_1 limit cycle, closed and open tail, with ``Study2Bird`` (variant
"package") and with the package ``BirdModel``. Exit code 1 on any difference.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from model import REPO, TABLE1, build_bird, study2_case  # noqa: E402


def main():
    d = np.load(REPO / "baseline" / "data" / "bird_study1.npz")
    ts, xs = d["trajectory_t"][::9], d["trajectory_x"][::9]
    ok = True
    for label in ("a", "b"):
        p = TABLE1[label]
        case = study2_case(p["beta"], p["psi"], p["amplitude"], p["q_wy"])
        mine, ref = build_bird(case, "package"), case.build_model()
        for name in ("forces", "dynamics", "jacobian"):
            a = np.array([np.asarray(getattr(mine, name)(x, t), float) for x, t in zip(xs, ts)])
            b = np.array([np.asarray(getattr(ref, name)(x, t), float) for x, t in zip(xs, ts)])
            same = np.array_equal(a, b)
            ok &= same
            print(f"case {label} (tail {p['beta']:g} deg) {name:9s} {'identical' if same else 'DIFFERENT'}")
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
