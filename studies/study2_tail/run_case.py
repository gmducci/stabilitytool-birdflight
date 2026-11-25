"""Run a study_2 Table 1 case and write its limit cycle and multipliers.

Usage (from the repository root, about 2-5 min per case)::

    uv run python studies/study2_tail/run_case.py b study2
    uv run python studies/study2_tail/run_case.py b study2_fixed --output DIR

Writes ``<output>/<case>_<variant>.json`` (summary) and ``.npz`` (all arrays).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle  # noqa: E402
from stabilitytool_birdflight.provenance import collect_provenance  # noqa: E402

from model import TABLE1, VARIANTS, build_bird, study2_case  # noqa: E402


def run(label, variant, output, log_stream=None):
    p = TABLE1[label]
    case = study2_case(p["beta"], p["psi"], p["amplitude"], p["q_wy"])
    t0 = time.time()
    r = find_limit_cycle(build_bird(case, variant), case.solver, log_stream=log_stream)
    x = r.trajectory_x
    summary = dict(
        case=label, variant=variant, table1=p, converged=r.converged,
        iterations=r.n_iterations, final_error=r.final_error,
        state_at_t0=r.state_at_t0.tolist(),
        mean_u=float(x[:, 0].mean()),
        mean_pitch_deg=float(np.degrees(x[:, 3].mean())),
        # study_2 Eq. 16: mean vertical velocity in the inertial frame (0 = level)
        W_ff=float(np.mean(x[:, 0]*np.sin(x[:, 3]) - x[:, 1]*np.cos(x[:, 3]))),
        multipliers=[[m.real, m.imag] for m in r.multipliers],
        moduli=np.abs(r.multipliers).tolist(),
        minutes=(time.time() - t0)/60,
        case_config=case.to_dict(),
        provenance=collect_provenance())
    output.mkdir(parents=True, exist_ok=True)
    stem = output / f"{label}_{variant}"
    stem.with_suffix(".json").write_text(json.dumps(summary, indent=2, default=str))
    np.savez(stem.with_suffix(".npz"), **r.to_arrays())
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", choices=sorted(TABLE1))
    ap.add_argument("variant", choices=sorted(VARIANTS))
    ap.add_argument("--output", type=Path, default=HERE / "results",
                    help="output directory (default: results/ next to this script)")
    args = ap.parse_args()
    s = run(args.case, args.variant, args.output, log_stream=sys.stdout)
    print(f"\ncase {s['case']} / {s['variant']}: u = {s['mean_u']:.2f} m/s, "
          f"pitch = {s['mean_pitch_deg']:.2f} deg, W_ff = {s['W_ff']:.3f} m/s, "
          f"|multipliers| = {np.round(s['moduli'], 4).tolist()} "
          f"(published max {s['table1']['published']})")


if __name__ == "__main__":
    main()
