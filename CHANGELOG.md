# Changelog

All notable changes to stabilitytool-birdflight, a fork of
[multiflap](https://github.com/vortexlab-uclouvain/multiflap) v1.1 (tag
`upstream-v1.1`). Numerical results are checked against the Stage 1 baseline
in `baseline/` (see `baseline/README.md`).

## Changes to numerical results

None so far: no code change has altered results. All stages reproduce the
Stage 1 baseline bitwise (relative difference 0) on numpy 1.26.4.

Environment-dependent differences (not code changes): with numpy 2.5.5 (on
macOS arm64 linked to Apple Accelerate instead of OpenBLAS) results differ by
at most 1.1e-12 relative (bird cases, Rossler, forced Van der Pol), and by
1.8e-7 for the redox oscillator, whose result is sensitive at that level to
roundoff (a 1e-15 perturbation of x0 moves it by 2.2e-7). The redox
regression tolerance was relaxed from 1e-8 to 1e-6 accordingly; see
`baseline/README.md`.

## [Unreleased]

### Stage 2: packaging and environment

- Package moved from `multiflap/` to `src/stabilitytool_birdflight/`
  (distribution name `stabilitytool-birdflight`, version `0.1.0.dev0`).
- Package-relative imports throughout. The bird model no longer requires
  `multiflap/` as the working directory or on `sys.path`. The scripts inside
  the package (`main.py`, `*_main.py`) import `stabilitytool_birdflight.*`
  and run with `python -m stabilitytool_birdflight.main`. Examples use
  `import stabilitytool_birdflight as mf`.
- `pyproject.toml` (setuptools) replaces `setup.py`: Python >= 3.11, numpy 2
  supported (`numpy>=1.26.4`, no upper bound), valid licence metadata
  (`Apache-2.0`, `LICENSE` and `NOTICE` shipped), valid classifiers.
- `uv.lock` pins the development environment; `uv sync` recreates it.
- `stabilitytool_birdflight.__version__` (from the installed metadata).
- Fixed the invalid escape sequence warnings (`\d`) in
  `ms_package/multiple_shooting.py`, `ms_package/multiple_shooting_period.py`
  (docstrings) and `utilities/tail_postprcessing.py` (plot labels) by using raw
  strings. String values are unchanged.
- Baseline tooling: `baseline/generate_baseline.py --target package` runs the
  baseline cases against the package; `--target upstream` (default) now
  extracts the `upstream-v1.1` tag with `git archive`. The baseline environment
  moved to `.venv-baseline`; `.venv` is the uv project environment. Redox
  regression tolerance relaxed to 1e-6 (see "Changes to numerical results").
- `NOTICE` states that this is a modified version of multiflap; the README
  starts with a short fork note; modified source files carry a change notice.

Known, not addressed in this stage: `odes/jaschinski.py` contains a syntax
error (unused module, cannot be imported); left for the Stage 7 cleanup.

### Stage 1: baseline

- `baseline/`: generator, comparison script, environment record, reference
  outputs of the unmodified upstream code, comparison of the study_1 reference
  case with the paper, and a kinematics realism check.
