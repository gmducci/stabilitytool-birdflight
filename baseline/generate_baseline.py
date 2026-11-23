#!/usr/bin/env python
"""Run the baseline cases against the upstream code or against the package.

``--target upstream`` (default) records the Stage 1 reference outputs from the
UNMODIFIED upstream multiflap code: the tag ``upstream-v1.1`` is extracted with
``git archive`` into a temporary directory and imported from there, so the
working tree does not matter. ``--target package`` runs the same cases against
the refactored ``stabilitytool_birdflight`` package (as installed, or from
``src/``) and writes the same file format, for comparison with
``compare_baseline.py``.

This script never edits upstream source files. Everything needed to make the
upstream code run (computing eigenvalues that ``main.py`` forgets to compute,
choosing the import path, skipping ``SaveData`` and plotting) is done here.

Each case runs in its own fresh Python subprocess, so that module-level state in
the upstream code (``SimulationsSettings`` instances, the Reynolds number computed
at import time in ``TailModels.py``) cannot leak between cases.

Usage (from the repository root)::

    python baseline/generate_baseline.py                       # all default cases
    python baseline/generate_baseline.py --cases rossler redox
    python baseline/generate_baseline.py --out some/dir --jobs 4
    python baseline/generate_baseline.py --target package --jobs 6

For each case ``<name>`` the output directory receives:

* ``<name>.npz``  compressed arrays (see ``_collect`` for the field list),
* ``<name>.json`` readable summary (settings, period, multipliers, ...),
* ``<name>.log``  everything the upstream code printed.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = {"upstream": REPO / "baseline" / "data",
               "package": REPO / "baseline" / "runs" / "candidate"}
PACKAGE = "stabilitytool_birdflight"
# Set by the driver for worker subprocesses.
ENV_TARGET = "BASELINE_TARGET"
ENV_UPSTREAM_DIR = "BASELINE_UPSTREAM_DIR"
UPSTREAM_TAG = "upstream-v1.1"
UPSTREAM_COMMIT = "67a29ecd78884cabfef1a0487dc418b599ef2e42"


# ---------------------------------------------------------------------------
# Case definitions
#
# Each case function runs inside a worker subprocess and returns
# (solver_output_tuple, metadata_dict). The solver output is the raw tuple
# returned by upstream ``Solver.lma()`` / ``SolverPeriod.lma()``:
#     (x, ptlist, error, complete_solution, jac_sg)
# ---------------------------------------------------------------------------

def _target():
    return os.environ.get(ENV_TARGET, "upstream")


def _upstream_dir():
    return Path(os.environ[ENV_UPSTREAM_DIR])


def _ensure_package_importable():
    try:
        import stabilitytool_birdflight  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(REPO / "src"))


def _toy_import():
    """Toy systems: ``import multiflap as mf`` (upstream) or the package."""
    if _target() == "package":
        _ensure_package_importable()
        import stabilitytool_birdflight as mf
        return mf
    sys.path.insert(0, str(_upstream_dir()))
    import multiflap as mf
    return mf


def _bird_import():
    """Import the bird code the way ``multiflap/main.py`` does.

    ``main.py`` and ``aero_package/bird_model.py`` use non-package imports
    (``from ms_package...``, ``from odes...``), so ``multiflap/`` must be on
    ``sys.path``. We also chdir there to mimic running ``python main.py``.
    """
    import numpy as np
    if _target() == "package":
        _ensure_package_importable()
        from stabilitytool_birdflight.dynamics.multiple_shooting import MultipleShooting
        from stabilitytool_birdflight.dynamics.lma_solver import Solver
        from stabilitytool_birdflight.flight.bird import BirdModel
        from stabilitytool_birdflight.kinematics.joints import Shoulder, Elbow, Wrist, Joint
        return np, MultipleShooting, Solver, BirdModel, Shoulder, Elbow, Wrist, Joint
    upstream_pkg = _upstream_dir() / "multiflap"
    sys.path.insert(0, str(upstream_pkg))
    os.chdir(upstream_pkg)
    from ms_package.multiple_shooting import MultipleShooting
    from ms_package.lma_solver import Solver
    from aero_package.bird_model import BirdModel
    from aero_package.bird import Shoulder, Elbow, Wrist, Joint
    return np, MultipleShooting, Solver, BirdModel, Shoulder, Elbow, Wrist, Joint


def _package_solve(model, **solver):
    """Package target: solve through SolverConfig -> LimitCycleResult."""
    from stabilitytool_birdflight.dynamics.config import SolverConfig
    return SolverConfig(**solver).solve(model, verbose=True)


def case_rossler():
    """``examples/rossler_system.py`` up to the solve (plotting skipped)."""
    mf = _toy_import()
    x = [.1, 5., 3.6]
    model = mf.Rossler(a=0.2, b=0.2, c=5.7)
    if _target() == "package":
        sol = _package_solve(model, x0=x, method="unknown_period", points=30,
                             period_guess=5., t_steps=5000, integrator="odeint")
    else:
        ms_obj = mf.MultipleShootingPeriod(x, M=30, period_guess=5., t_steps=5000,
                                           model=model, integrator='odeint')
        sol = mf.SolverPeriod(ms_obj=ms_obj).lma()
    meta = dict(
        source="examples/rossler_system.py",
        solver="SolverPeriod (unknown period)",
        settings=dict(model="Rossler", a=0.2, b=0.2, c=5.7, x0=x, M=30,
                      period_guess=5.0, t_steps=5000, integrator="odeint",
                      option_jacobian="analytical", tolerance=1e-5,
                      max_iterations=100),
        workarounds=["plotting skipped (fig.gca(projection='3d') fails on "
                     "current matplotlib)"],
    )
    return sol, meta


def case_redox():
    """``examples/redox_oscillator.py`` up to the solve (SaveData/plots skipped)."""
    mf = _toy_import()
    x = [0.5, 0.5, 0.6, 0.2]
    model = mf.RedoxModel()
    if _target() == "package":
        sol = _package_solve(model, x0=x, method="unknown_period", points=2,
                             period_guess=23., t_steps=90000, integrator="odeint")
    else:
        ms_obj = mf.MultipleShootingPeriod(x, M=2, period_guess=23., t_steps=90000,
                                           model=model, integrator='odeint')
        sol = mf.SolverPeriod(ms_obj=ms_obj).lma()
    meta = dict(
        source="examples/redox_oscillator.py",
        solver="SolverPeriod (unknown period)",
        settings=dict(model="RedoxModel", model_params="defaults "
                      "(a=1000, b=2, c=10000, d=0.2, e=0.1, q=0.1, p=1)",
                      x0=x, M=2, period_guess=23.0, t_steps=90000,
                      integrator="odeint", option_jacobian="analytical",
                      tolerance=1e-5, max_iterations=100),
        workarounds=["SaveData and plotting skipped (hard-coded relative "
                     "results path)"],
    )
    return sol, meta


def case_forced_vdp():
    """``examples/forced_van_der_pol.py`` with the hard-coded dim=4 overridden."""
    mf = _toy_import()
    x = [1., 1.]
    model = mf.ForcedVanDerPol(lam=1.8)
    if _target() == "package":   # dim taken from the model since Stage 4
        sol = _package_solve(model, x0=x, method="known_period", points=2,
                             period=10.4719755, t_steps=4000,
                             jacobian="numerical", tolerance=1e-6)
    else:
        ms_obj = mf.MultipleShooting(x, M=2, period=10.4719755, t_steps=4000,
                                     model=model, option_jacobian='numerical')
        # Upstream MultipleShooting.__init__ hard-codes self.dim = 4.
        ms_obj.dim = model.dimension
        sol = mf.Solver(tolerance=1e-6, ms_obj=ms_obj).lma()
    meta = dict(
        source="examples/forced_van_der_pol.py",
        solver="Solver (known period)",
        settings=dict(model="ForcedVanDerPol", lam=1.8, gamma=0.5, delta=4,
                      x0=x, M=2, period=10.4719755, t_steps=4000,
                      integrator="rk4", option_jacobian="numerical",
                      tolerance=1e-6, max_iterations=100),
        workarounds=["ms_obj.dim set to model.dimension (=2) after "
                     "construction: MultipleShooting hard-codes dim=4"],
    )
    return sol, meta


def case_lorenz():
    """``examples/lorentz_system.py`` with the constructor and lma() call fixed."""
    mf = _toy_import()
    x = [10., 10., 3.6]
    # Example calls Lorentz(a=10, b=28, c=8/3); the class takes (sigma, r, b).
    # The class is Lorentz upstream, Lorenz in the package (Stage 7).
    lorenz = mf.Lorenz if _target() == "package" else mf.Lorentz
    model = lorenz(sigma=10, r=28, b=8 / 3)
    ms_obj = mf.MultipleShootingPeriod(x, M=2, period_guess=10., t_steps=50000,
                                       model=model, option_jacobian='numerical')
    # Example calls .lma(5.); SolverPeriod.lma() takes no argument.
    sol = mf.SolverPeriod(ms_obj=ms_obj).lma()
    meta = dict(
        source="examples/lorentz_system.py",
        solver="SolverPeriod (unknown period)",
        settings=dict(model="Lorentz", sigma=10, r=28, b=8 / 3, x0=x, M=2,
                      period_guess=10.0, t_steps=50000, integrator="rk",
                      option_jacobian="numerical", tolerance=1e-5,
                      max_iterations=100),
        workarounds=["Lorentz(sigma=10, r=28, b=8/3) instead of the example's "
                     "invalid Lorentz(a=..., b=..., c=...)",
                     "SolverPeriod.lma() called without the example's "
                     "invalid argument 5."],
    )
    return sol, meta


def _bird_case(shoulder_x_amp_deg, x0, M, t_steps, source, extra_note=None,
               config_file=None):
    """Bird model with the joint values hard-coded in ``multiflap/main.py``.

    Only the amplitude of ``shoulder.axis_z`` (the paper's A_s,x), x0, M and
    t_steps vary between bird cases. Period 0.25 s = 1 / (4 Hz).
    """
    np, MultipleShooting, Solver, BirdModel, Shoulder, Elbow, Wrist, Joint = _bird_import()
    if _target() == "package":
        # Package target: the case is specified only by its YAML file.
        from stabilitytool_birdflight.flight.config import BirdCaseConfig
        sol = BirdCaseConfig.load(REPO / "examples" / "configs" / config_file).solve(verbose=True)
        return sol, dict(source=source, solver="BirdCaseConfig.solve",
                         config_file=f"examples/configs/{config_file}",
                         settings=dict(tolerance=1e-5), workarounds=[])
    shoulder = Shoulder(axis_x=Joint(0.2, 0.014, -np.pi / 2),
                        axis_y=Joint(-np.deg2rad(19), np.deg2rad(20), np.pi / 2),
                        axis_z=Joint(0, np.deg2rad(shoulder_x_amp_deg), np.pi))
    elbow = Elbow(axis_x=Joint(0., np.pi / 6, -np.pi / 2),
                  axis_y=Joint(np.pi / 6, np.pi / 6, -np.pi / 2))
    wrist = Wrist(axis_y=Joint(-np.pi / 6, np.pi / 6, np.pi / 2),
                  axis_z=Joint(0., 0., 0.))
    bird = BirdModel(shoulder=shoulder, elbow=elbow, wrist=wrist)
    ms_obj = MultipleShooting(x0, M=M, period=0.25, t_steps=t_steps, model=bird)
    sol = Solver(ms_obj=ms_obj).lma()
    joints = {
        "shoulder.axis_x": "Joint(0.2, 0.014, -pi/2)",
        "shoulder.axis_y": "Joint(-deg2rad(19), deg2rad(20), pi/2)",
        "shoulder.axis_z": f"Joint(0, deg2rad({shoulder_x_amp_deg}), pi)",
        "elbow.axis_x": "Joint(0, pi/6, -pi/2)",
        "elbow.axis_y": "Joint(pi/6, pi/6, -pi/2)",
        "wrist.axis_y": "Joint(-pi/6, pi/6, pi/2)",
        "wrist.axis_z": "Joint(0, 0, 0)",
    }
    meta = dict(
        source=source,
        solver="Solver (known period)",
        settings=dict(model="BirdModel (defaults: mass=1.2, Iyy=0.1 hard-coded, "
                      "f=4 Hz, wingframe_position=[0,0,-0.05], tail_opening=0)",
                      joints_Joint_offset_amplitude_phase_rad=joints,
                      x0=list(x0), M=M, period=0.25, t_steps=t_steps,
                      integrator="rk4 (trajectory), rk2 with Nt=30 per "
                                 "interval (variational eq., hard-coded)",
                      option_jacobian="analytical", tolerance=1e-5,
                      max_iterations=100),
        workarounds=["eigenvalues computed here from mysol[4] (main.py uses "
                     "an undefined name `eigenvalues`)",
                     "SaveData skipped"],
    )
    if extra_note:
        meta["note"] = extra_note
    return sol, meta


def case_bird_main():
    """``multiflap/main.py`` as-is (A = 44 deg, x0 = [18, .5, .1, .01], M=2, 70 steps)."""
    return _bird_case(44, [18., 0.5, 0.1, 0.01], M=2, t_steps=70,
                      source="multiflap/main.py", config_file="bird_main.yaml")


def case_bird_study1():
    """study_1 reference case (Sect. 4.1, Tables 1-2) as closely as the code allows."""
    return _bird_case(
        42, [16.5, 0.5, 0.5, 0.], M=5, t_steps=38,
        config_file="bird_study1_reference.yaml",
        source="study_1 Sect. 4.1 / Table 1 (A_s,x = 42 deg) / Table 2 (M=5, "
               "150 time steps per period, RK4, tolerance 1e-5)",
        extra_note=("Table 2 asks for 150 time steps per period. In upstream "
                    "MultipleShooting each of the M-1 = 4 intervals is "
                    "integrated on linspace(t, t+tau, t_steps), i.e. t_steps-1 "
                    "RK4 steps, so exactly 150 is impossible; t_steps=38 gives "
                    "4*37 = 148 steps per period. Joint values other than "
                    "A_s,x are those of main.py; see baseline/README.md for "
                    "the mapping to Table 1 and the discrepancies found."))


def case_bird_a42_main_numerics():
    """Diagnostic: main.py numerics (M=2, 70 steps) with A = 42 deg and the paper's x0."""
    return _bird_case(
        42, [16.5, 0.5, 0.5, 0.], M=2, t_steps=70,
        config_file="bird_a42_main_numerics.yaml",
        source="diagnostic: main.py with A_s,x = 42 deg and study_1 x0",
        extra_note=("Isolates the effect of the shoulder amplitude (44 -> 42 "
                    "deg) from the effect of the discretisation (M, t_steps)."))


CASES = {
    "rossler": case_rossler,
    "redox": case_redox,
    "forced_vdp": case_forced_vdp,
    "lorenz": case_lorenz,
    "bird_main": case_bird_main,
    "bird_study1": case_bird_study1,
    "bird_a42_main_numerics": case_bird_a42_main_numerics,
}
# "lorenz" is not a default case: with the example's settings the upstream
# solver does not converge within 100 iterations (it then raises
# UnboundLocalError on jac_sg). It stays available via --cases lorenz.
DEFAULT_CASES = ["rossler", "redox", "forced_vdp",
                 "bird_main", "bird_study1", "bird_a42_main_numerics"]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def provenance():
    import numpy, scipy, matplotlib
    target = _target()
    if target == "package":
        import stabilitytool_birdflight as pkg
        code = dict(target="package",
                    package_version=getattr(pkg, "__version__", None),
                    package_path=str(Path(pkg.__file__).parent))
    else:
        code = dict(target="upstream",
                    upstream_source=f"git archive {UPSTREAM_TAG}")
    return dict(
        **code,
        timestamp_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        repo_commit=_git("rev-parse", "HEAD"),
        repo_dirty=bool(_git("status", "--porcelain", "--untracked-files=no")),
        upstream_tag=UPSTREAM_TAG,
        upstream_github_commit=UPSTREAM_COMMIT,
        python=sys.version,
        numpy=numpy.__version__,
        scipy=scipy.__version__,
        matplotlib=matplotlib.__version__,
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        openblas_num_threads=os.environ.get("OPENBLAS_NUM_THREADS"),
    )


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _sorted_multipliers(np, w):
    # Descending modulus; ties (complex pairs) broken by descending imag part.
    order = sorted(range(len(w)), key=lambda k: (-abs(w[k]), -w[k].imag))
    return np.asarray(w)[order], order


def _collect_result(np, res):
    """Arrays from a package LimitCycleResult (multipliers already sorted)."""
    return dict(
        points=res.points, points_history=res.points_history,
        error_history=res.error_history, trajectory_t=res.trajectory_t,
        trajectory_x=res.trajectory_x, monodromy=res.monodromy,
        multipliers=res.multipliers, eigenvectors=res.eigenvectors,
        multipliers_sorted=res.multipliers, eigenvectors_sorted=res.eigenvectors,
        period=np.float64(res.period), n_iterations=np.int64(res.n_iterations),
        final_error=np.float64(res.final_error), elapsed_s=np.float64(res.elapsed_s),
    )


def _collect(np, sol, elapsed):
    if not isinstance(sol, tuple):
        return _collect_result(np, sol)
    x, ptlist, error, complete_solution, jac_sg = sol
    eigvals, eigvecs = np.linalg.eig(jac_sg)
    msorted, order = _sorted_multipliers(np, eigvals)
    arrays = dict(
        points=np.asarray(x, float),                       # converged MS points (M x n)
        points_history=np.asarray([np.asarray(p, float) for p in ptlist]),
        error_history=np.asarray(error, float),           # max|E| at each evaluation
        trajectory_t=np.asarray(complete_solution.time, float),
        trajectory_x=np.asarray(complete_solution.space, float),
        monodromy=np.asarray(jac_sg, float),
        multipliers=np.asarray(eigvals),                  # np.linalg.eig order
        eigenvectors=np.asarray(eigvecs),                 # columns, eig order
        multipliers_sorted=msorted,
        eigenvectors_sorted=np.asarray(eigvecs)[:, order],
        period=np.float64(complete_solution.time[-1]),
        n_iterations=np.int64(len(error) - 1),             # number of LM updates
        final_error=np.float64(error[-1]),
        elapsed_s=np.float64(elapsed),
    )
    return arrays


def run_worker(name, out_dir):
    out_dir = Path(out_dir)
    log_path = out_dir / f"{name}.log"
    with open(log_path, "w") as log, contextlib.redirect_stdout(log):
        import numpy as np
        t0 = time.perf_counter()
        sol, meta = CASES[name]()
        elapsed = time.perf_counter() - t0
        arrays = _collect(np, sol, elapsed)
    # Upstream solvers only return after convergence (otherwise jac_sg is
    # undefined and they raise), but check against the case tolerance anyway.
    arrays["converged"] = np.bool_(
        arrays["final_error"] < meta["settings"]["tolerance"])

    np.savez_compressed(out_dir / f"{name}.npz", **arrays)

    ms = arrays["multipliers_sorted"]
    summary = dict(
        case=name,
        description=CASES[name].__doc__.strip(),
        **meta,
        results=dict(
            converged=bool(arrays["converged"]),
            n_iterations=int(arrays["n_iterations"]),
            final_error=float(arrays["final_error"]),
            error_history=arrays["error_history"].tolist(),
            period=float(arrays["period"]),
            state_at_t0=arrays["points"][0].tolist(),
            multipliers_sorted=[dict(real=float(m.real), imag=float(m.imag),
                                     modulus=float(abs(m))) for m in ms],
            monodromy=arrays["monodromy"].tolist(),
            elapsed_s=float(arrays["elapsed_s"]),
        ),
        provenance=provenance(),
    )
    with open(out_dir / f"{name}.json", "w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _extract_upstream(dest):
    """Extract the upstream tag into ``dest`` (only multiflap/ is needed)."""
    archive = subprocess.run(["git", "archive", UPSTREAM_TAG, "multiflap"],
                             cwd=REPO, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)


def _launch(name, out_dir, timeout, target, upstream_dir):
    env = dict(os.environ, MPLBACKEND="Agg", OPENBLAS_NUM_THREADS="1",
               OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    env[ENV_TARGET] = target
    if upstream_dir is not None:
        env[ENV_UPSTREAM_DIR] = str(upstream_dir)
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", name,
           "--out", str(out_dir)]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, env=env, cwd=REPO, capture_output=True,
                              text=True, timeout=timeout)
        status = "ok" if proc.returncode == 0 else f"failed (exit {proc.returncode})"
        err = proc.stderr
    except subprocess.TimeoutExpired as exc:
        status, err = f"timed out after {timeout} s", exc.stderr or ""
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
    dt = time.perf_counter() - t0
    if status != "ok":
        (Path(out_dir) / f"{name}.stderr").write_text(err or "")
    print(f"[{name}] {status} in {dt:.1f} s", flush=True)
    return name, status


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cases", nargs="+", default=DEFAULT_CASES,
                   choices=sorted(CASES))
    p.add_argument("--target", choices=["upstream", "package"],
                   default="upstream",
                   help="code to run: the upstream tag (default) or the package")
    p.add_argument("--out", default=None,
                   help="output directory (default: baseline/data for "
                        "upstream, baseline/runs/candidate for package)")
    p.add_argument("--jobs", type=int, default=1,
                   help="number of cases to run in parallel")
    p.add_argument("--timeout", type=float, default=None,
                   help="per-case timeout in seconds")
    p.add_argument("--worker", help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    out_dir = Path(args.out or DEFAULT_OUT[args.target]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.worker:
        run_worker(args.worker, out_dir)
        return 0

    with contextlib.ExitStack() as stack:
        upstream_dir = None
        if args.target == "upstream":
            import tempfile
            upstream_dir = Path(stack.enter_context(
                tempfile.TemporaryDirectory(prefix="upstream-v1.1-")))
            _extract_upstream(upstream_dir)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(
                lambda n: _launch(n, out_dir, args.timeout, args.target,
                                  upstream_dir), args.cases))
    failed = [n for n, s in results if s != "ok"]
    if failed:
        print("Failed cases:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
