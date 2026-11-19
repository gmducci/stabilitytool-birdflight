"""Command-line interface.

    stabilitytool-birdflight run CASE.yaml --output DIR [--overwrite] [--verbose]
    stabilitytool-birdflight validate CASE.yaml [--print]
    stabilitytool-birdflight show DIR

(also ``python -m stabilitytool_birdflight ...``)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

__all__ = ["main"]


def _cmd_run(args):
    from .runs import run_bird_case
    result = run_bird_case(args.case, args.output, overwrite=args.overwrite,
                           verbose=args.verbose)
    print(result.summary())
    print(f"written to {args.output}")
    return 0 if result.converged else 2


def _cmd_validate(args):
    import yaml
    from .flight.config import BirdCaseConfig
    case = BirdCaseConfig.load(args.case)
    if args.print:
        print(yaml.safe_dump(case.to_dict(), sort_keys=False, default_flow_style=None), end="")
    else:
        print(f"{args.case}: valid ({case.solver.points} shooting points, "
              f"period {case.solver.period} s)")
    return 0


def _cmd_show(args):
    from .dynamics.result import LimitCycleResult
    out = Path(args.run_dir)
    prov = json.loads((out / "provenance.json").read_text())
    print(f"status        {prov.get('status')}")
    git = prov.get("git") or {}
    print(f"code          {prov['package']['version']}  git {git.get('describe')}"
          f"{'  (DIRTY)' if git.get('dirty') else ''}")
    print(f"started       {prov.get('started_utc')}  elapsed {prov.get('elapsed_s', float('nan')):.1f} s")
    if (out / "result.npz").exists():
        print(LimitCycleResult.from_npz(out / "result.npz").summary())
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="stabilitytool-birdflight",
                                description="Limit cycles and Floquet stability of "
                                            "bird flapping flight.")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="solve a case and write an output directory")
    r.add_argument("case", help="case file (.yaml, .yml or .json)")
    r.add_argument("--output", "-o", required=True, help="output directory")
    r.add_argument("--overwrite", action="store_true",
                   help="allow writing into a non-empty output directory")
    r.add_argument("--verbose", "-v", action="store_true",
                   help="also print the solver progress")
    r.set_defaults(func=_cmd_run)

    v = sub.add_parser("validate", help="check a case file")
    v.add_argument("case")
    v.add_argument("--print", action="store_true",
                   help="print the fully resolved configuration")
    v.set_defaults(func=_cmd_validate)

    s = sub.add_parser("show", help="summarise an output directory")
    s.add_argument("run_dir")
    s.set_defaults(func=_cmd_show)

    args = p.parse_args(argv)
    from .configio import ConfigError
    try:
        return args.func(args)
    except (ConfigError, FileExistsError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
