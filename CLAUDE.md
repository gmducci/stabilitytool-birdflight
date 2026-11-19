# CLAUDE.md

Guidance for Claude Code when working in this repository. Read this file in full
before making any change.

## 1. What this project is

This repository is a refactoring of **multiflap** (v1.1), a Python toolbox by
Gianmarco Ducci et al. (UCLouvain, Apache 2.0). It:

- finds periodic orbits (limit cycles) of nonlinear ODE systems with a
  **multiple-shooting** scheme solved by a Levenberg–Marquardt-type solver,
- assesses their stability through the **Floquet multipliers** (eigenvalues of
  the monodromy matrix),
- includes a **bird flapping-flight model** in the longitudinal plane: prescribed
  poly-articulated wing kinematics (shoulder, elbow and wrist joints), a
  lifting-line aerodynamic model, and an optional tail surface,
- also computes the leading Lyapunov exponent, and ships toy systems (Rössler,
  Lorenz, redox oscillator, forced Van der Pol, isothermal reaction, and others).

Upstream: https://github.com/vortexlab-uclouvain/multiflap

The goal is **proper, usable research software that meets reproducibility
standards**, which the user will then extend for their own research. The
refactor is not a rewrite of the science: the numerical results must not change
unless a change is deliberate, justified and documented.

### The two papers

The user keeps the two papers in `papers/` at the repo root. This folder is
git-ignored and must never be committed (they are published, copyrighted
articles). If the folder is missing, ask the user for the PDFs.

- `papers/study_1.pdf`: Ducci, Colognesi, Vitucci, Chatelain, Ronsse,
  *Stability and Sensitivity Analysis of Bird Flapping Flight*, Journal of
  Nonlinear Science 31:47 (2021), doi:10.1007/s00332-021-09698-1. It covers the
  method, the morphing-wing model, the reference limit cycle (Section 4.1,
  Table 1, Table 3), and sensitivity to shoulder amplitude and to the wing
  position relative to the centre of mass.
- `papers/study_2.pdf`: Ducci, Vitucci, Chatelain, Ronsse, *On the role of tail
  in stability and energetic cost of bird flapping flight*, Scientific Reports.
  It adds the tail-opening study, power consumption and cost of transport. Read
  it before touching `TailModels.py` or the power/energy code.

When code and paper disagree, do not silently pick one. Report the discrepancy
to the user, citing the paper section or equation and the file and line.

## 2. Ground rules (non-negotiable)

1. **The baseline comes first.** Before any refactoring, Stage 1 (below) must
   record reference outputs from the *unmodified* upstream code. Every later
   stage must reproduce them within the tolerances in Section 5.
2. **Never change numerical behaviour silently.** Any change that alters
   results (a bug fix, a different integrator, a default value) gets its own
   commit, a clear message explaining why, an entry in `CHANGELOG.md` under
   "Changes to numerical results", and an updated baseline. Ask the user first.
3. **One stage at a time, small commits.** Each commit should do one thing. Do
   not mix moving files with changing logic in the same commit, so that `git
   diff` stays reviewable.
4. **Run the tests before every commit.** The fast suite always. The slow bird
   regression test (about 5 min) at least at the end of each stage, and after
   any change touching `aero_package/`, `odes/bird_dynamics.py`, the solver or
   the integrators.
5. **Respect the licence** (Section 7).
6. **Ask, don't guess, on design decisions** listed in Section 6.

## 3. Repository history convention

- Commit 1 is the unmodified upstream code, tagged `upstream-v1.1`. Do not
  amend it. If the repo does not yet look like this, stop and ask the user.
- Then one or more commits per stage, prefixed with the stage, for example
  `stage2: move package to src/ layout`.
- Tag the end of each stage: `stage1-baseline`, `stage2-packaging`, and so on.
- Keep `CHANGELOG.md` up to date from Stage 2 onward.

## 4. Findings from the initial audit (done before this repo was created)

Tested on Linux, Python 3.12.3, numpy 1.26.4, scipy 1.17.1, matplotlib 3.11.2,
with the package installed via `pip install -e .`. Re-verify on the user's
machine during Stage 1; these are leads, not facts about the current state.

### What works

- **Rössler** (`examples/rossler_system.py` settings: a=b=0.2, c=5.7,
  x0=[0.1, 5.0, 3.6], `MultipleShootingPeriod`, M=30, period_guess=5,
  t_steps=5000, integrator='odeint'): converges in about 10 iterations to
  period **5.881088559** with Floquet multipliers **−2.40395, ≈1e-14,
  0.9999998**. This matches the published reference values (Dednam & Botha 2015).
- **Redox oscillator** (`examples/redox_oscillator.py`): the solver converges
  (final error about 9.9e-7) and computes multipliers, then crashes when saving
  (see below). Its period and multipliers were not recorded: do this in Stage 1.
- **Bird model** (`multiflap/main.py`, run from inside `multiflap/`): converges
  in 8 iterations (about 37 s each, of which about 18 s is the Jacobian; about
  5 min total). Settings: `MultipleShooting` (known period), x0 = [18, 0.5, 0.1,
  0.01], M=2, period=0.25, t_steps=70, kinematics as hard-coded in `main.py`
  (shoulder axis_z amplitude **44°**). Result:
  - multipliers **1.40110, 0.81886 ± 0.26393j, 0.19909** (moduli 1.40110,
    0.86034, 0.86034, 0.19909)
  - limit-cycle state at t0 **[18.6701, −2.1509, −0.12073, −0.11611]**

### Comparison with study_1 (Section 4.1, Table 3)

The paper's reference case gives multipliers **1.40, 0.829 ± 0.260j, 0.212**,
state at t0 **[18.24, −1.93, −0.10, −0.115]**, initial guess
x0 = [16.5, 0.5, 0.5, 0], and convergence in seven iterations. It uses the
kinematics of Table 1 with **A_s,x = 42°**.

`main.py` is therefore **not** the paper's reference case. The 44° vs 42°
shoulder amplitude is the most likely cause of the small difference, but this is
unconfirmed. In Stage 1, compare every kinematic parameter in `main.py` against
study_1 Table 1, build the paper's reference case exactly, run it, and report to
the user how close it gets to Table 3. Also check whether the paper states M and
the number of time steps.

### What is broken

- `main.py` crashes after solving: `eigenvalues` is used but never defined
  (it should be the eigenvalues of `mysol[4]`, the monodromy matrix).
- `examples/forced_van_der_pol.py`: passes a 2-element x0 but the model's
  dimension is 4 → `ValueError` in `get_initial_guess`.
- `examples/lorentz_system.py`: calls `Lorentz(a=..., b=..., c=...)` but the
  class signature is `Lorentz(sigma, r, b)` → `TypeError`.
- `examples/rossler_system.py`: the solver works, then plotting crashes on
  `fig.gca(projection='3d')`, removed in recent matplotlib.
- `examples/redox_oscillator.py` and anything using `SaveData`: the results
  path is hard-coded to the relative `'../results'`, so it depends on the
  working directory. The `make_folder` method uses bare `except:` clauses that
  swallow the real error and print "Error in trying to create data folder".
- The scripts in `multiflap/` (`main.py`, `*_main.py`) and
  `aero_package/bird_model.py` use non-package imports (`from ms_package...`,
  `from odes...`), so they only run with `multiflap/` as the working directory.
- `setup.py` pins `numpy<2.0`, its `license` field is the string `'LICENSE'`,
  and its classifiers are invalid. Python 2 is claimed but not realistic.
- There are `SyntaxWarning: invalid escape sequence '\d'` warnings in the
  docstrings of `multiple_shooting.py` and `multiple_shooting_period.py`.
- There are no tests.

### Critical: silently ignored parameters

`BirdModel.__init__` (`aero_package/bird_model.py`) defines
`frequency`, `wingframe_position`, `wingframe_position_tail`, `tail_length`,
`tail_chord` and `tail_opening` as attributes. However,
`aero_package/flapping_forces.py` and `aero_package/TailModels.py` instantiate a
module-level `SimulationsSettings()` (`aero_package/settings.py`) and read
`wingframe_position`, `wingframe_position_tail` and `tail_length` from it.
`TailModels.py` also computes a module-level Reynolds number from
`settings.tail_length` at import time, and falls back to `settings.tail_opening`
when none is passed.

Consequence: setting for example `mybird.wingframe_position = ...` has **no
effect** on the aerodynamic forces. Study_1 reports that the wing position
relative to the centre of mass strongly affects the Floquet multipliers, so a
parameter sweep done through the `BirdModel` attributes would produce silently
wrong results. Trace every parameter (including `frequency` and `mass`) to every
place it is read before fixing this, and tell the user which upstream usage
patterns would have been affected.

### Dead weight and duplicates

- `ms_package/bird_dynamics.py` and `odes/bird_dynamics.py` differ by one blank
  line; only the `odes/` version is imported (by `bird_model.py`).
- `ms_package/integrator_2.py`: check whether anything uses it.
- `docs/_build/` (committed build output, including fonts and doctrees) and the
  `docs_bak` doctrees.
- `pdfs/` holds about 5 MB of third-party papers, and `anim/` holds about 2 MB
  of mp4s. Ask the user before removing anything from the repository.
- `utils/.vscode/`, `multiflap.egg-info` if present.
- Both `utils/` and `utilities/` packages exist.

## 5. Refactoring plan

### Stage 1: lock the baseline (unmodified upstream code)

- Set up an environment that runs the upstream code as-is (Python 3.12 with
  `numpy<2` works). Write the exact versions to `baseline/ENVIRONMENT.md`.
- Write `baseline/generate_baseline.py`, which runs the cases below against the
  upstream code. Do not edit upstream source files to make it run: patch only in
  the generator script (for example compute the eigenvalues there, set the
  working directory, and avoid `SaveData`).
- Cases: Rössler (as above), redox (as in the example), the bird case from
  `main.py` as-is, and the study_1 reference case (Table 1 kinematics, x0 from
  Section 4.1). Add forced Van der Pol and Lorenz only if they can run without
  touching upstream code.
- For each case, store in `baseline/data/` (`.npz` plus a readable JSON
  summary): the converged multiple-shooting points, period, the full limit-cycle
  trajectory, the monodromy matrix, the Floquet multipliers, the number of
  iterations and the final error.
- Tolerances for later comparisons: relative 1e-8 for toy systems; for the bird
  case, start at relative 1e-6 on multipliers and states, and tighten it if
  run-to-run reproducibility allows. Check run-to-run variability first by
  running each case twice.
- Report to the user how the study_1 reference case compares with Table 3.

### Stage 2: packaging and environment

- `pyproject.toml` (setuptools or hatchling), `src/` layout, package-relative
  imports, no `sys.path` tricks.
- Support numpy 2. Run the baseline comparison on both numpy 1.26 and 2.x.
- Declare the Python version range. Provide a lockfile (ask the user for their
  preference: `uv`, `pip-tools` or conda `environment.yml`).
- Fix the `\d` escape warnings.

Stages 3 and 4 were swapped on 2026-11-19 after the scope decision (Section
6): the module split comes first, configuration second.

### Target architecture (decided 2026-11-19)

A toolbox of independent, model-agnostic modules plus one coupling layer:

- `dynamics`: nonlinear-dynamics methods (multiple shooting with known and
  unknown period, Levenberg–Marquardt solver, Floquet multipliers, Lyapunov
  exponent, integrators). Depends only on numpy/scipy. Toy systems live here
  as examples.
- `kinematics`: biomechanics. Joints and gaits, skeleton, feathers, forward
  kinematics producing the wing geometry and its velocity at time t (lifting
  line, chords, tip path, span, sweep). No aerodynamics.
- `aerodynamics`: lifting-line solver and tail model. Input: a wing geometry,
  its velocity, the free stream and angular velocity. Output: circulation,
  angle of attack, forces, moments. Knows nothing about birds or flight
  states.
- `flight`: flight mechanics (longitudinal rigid-body equations, mass,
  inertia). The only module that imports the others; it couples kinematics
  and aerodynamics into a model the `dynamics` module can solve.

Rule: `kinematics`, `aerodynamics` and `dynamics` never import each other.
The user must be able to extract bird kinematics without flight mechanics.

### Stage 3: module split with explicit parameters

- Create the four modules above and move the code into them (moves in their
  own commits, separate from logic changes).
- Cut the coupling: `flapping_forces` takes a free-stream vector and angular
  velocity instead of the flight state (u, w, q, θ); the wing velocity
  (currently finite differences in `bird_dynamics.py`) is provided by
  `kinematics`; `frequency` becomes a gait parameter instead of a module
  constant in `bird.py`.
- Remove the module-level `SimulationsSettings` and import-time computations.
  Every function receives its parameters explicitly.
- Keep the default values identical to upstream so the baseline still passes.
- Add a test that changing each parameter actually changes the forces it should
  affect (this guards against the bug in Section 4 coming back).

### Stage 4: configuration, model interface and results

- One validated configuration object per module (kinematics, aerodynamics,
  flight, solver), composed for a bird case (dataclasses, or pydantic if the
  user agrees). Loadable from and saveable to a file: YAML as the main format
  (comments allowed), JSON also accepted; confirm with the user at the start of
  the stage. The bird case must be fully specified by its config file.
- A clear model interface for `dynamics` (for example a `Protocol` with
  `dynamics(x, t)`, `dimension`, optional `jacobian(x, t)`), replacing the
  current `dynamics`/`get_stability_matrix` naming convention if the user
  agrees. The bird model and toy systems implement it.
- Return a structured result object (period, trajectory, monodromy matrix,
  multipliers, eigenvectors, convergence history) instead of the current tuple
  indexed by position (`mysol[3]`, `mysol[4]`).

### Stage 5: run provenance

- Each run writes to a user-chosen output directory: the results, the full
  resolved config, the package version and git commit (plus a dirty-tree flag),
  the versions of Python and key dependencies, timestamps, and solver
  diagnostics (iterations, error history, timing).
- No hard-coded paths. No bare `except:`.

### Stage 6: tests and continuous integration

- pytest. Fast suite: toy-system regression against the baseline, solver unit
  tests, analytical vs numerical Jacobian checks for every model that provides
  an analytical Jacobian, config round-trip, and the parameter-sensitivity test
  from Stage 3.
- Slow suite (marked, for example `@pytest.mark.slow`): the bird regression
  cases.
- GitHub Actions workflow running the fast suite on Linux for the supported
  Python versions. The slow suite on demand or nightly.

### Stage 7: cleanup, documentation and citation

- Remove duplicates and dead code (Section 4), after confirming with the user.
- Logging instead of `print`, type hints, numpy-style docstrings.
- Working examples, an updated README and docs (rebuild the docs from source,
  don't commit build output).
- `CITATION.cff` crediting the original authors and paper, plus this fork.
- Optional, if the user wants it: performance profiling of the bird model (about
  37 s per solver iteration currently). Any optimisation must pass the baseline.

## 6. Decisions to ask the user about (do not decide alone)

Decided:

- **Scope** (2026-11-19): a toolbox aggregating aerodynamics, biomechanics
  (kinematics) and nonlinear-dynamics methods, each module independent and
  agnostic, with flight mechanics as the coupling layer. See "Target
  architecture" in Section 5.
- **Project name** (Stage 2): distribution `stabilitytool-birdflight`, import
  package `stabilitytool_birdflight`.
- **Environment** (Stage 2): uv with `uv.lock`; Python >= 3.11.
- **Config format** (tentative, confirm in Stage 4): YAML, JSON also accepted.

Still open:

- Whether to keep `pdfs/`, `anim/` and the toy systems in the repository.
- Any change to numerical results, including bug fixes (ground rule 2).
- Whether to report the silently-ignored-parameter issue upstream.

## 7. Licence and attribution

The upstream code is Apache License 2.0 (see `LICENSE` and `NOTICE`). Therefore:

- Keep `LICENSE` and `NOTICE`. Add to `NOTICE` a line stating that this project
  is a modified version of multiflap and who made the modifications.
- Keep the copyright headers in the upstream source files. In modified files,
  add a prominent notice that the file was changed (for example a line in the
  header, "Modified by <user/project>, <year>").
- Give the project its own name or describe it clearly as a fork of multiflap.
- Cite study_1 (as upstream requests) in the README and `CITATION.cff`.

## 8. Practical notes

- The bird case takes about 5 minutes. Run it in the background and keep
  working, rather than blocking on it.
- Use a non-interactive matplotlib backend (`MPLBACKEND=Agg`) when running
  examples or tests, so `plt.show()` does not block.
- Toy systems take seconds. Use them for quick feedback on solver changes.
- Environments: `.venv` is the uv project environment (numpy 2, `uv run ...`);
  `.venv-baseline` is numpy 1.26 (upstream baseline and numpy-1.26 checks).
  Regression check: `baseline/README.md`.
