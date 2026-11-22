# Changelog

All notable changes to stabilitytool-birdflight, a fork of
[multiflap](https://github.com/vortexlab-uclouvain/multiflap) v1.1 (tag
`upstream-v1.1`). Numerical results are checked against the Stage 1 baseline
in `baseline/` (see `baseline/README.md`).

## Changes to numerical results

With default parameters no code change has altered results: all stages
reproduce the Stage 1 baseline bitwise (relative difference 0) on numpy
1.26.4.

**Stage 3: parameters that upstream silently ignored now take effect.** In
upstream multiflap these `BirdModel` attributes were never read; the code used
module-level constants instead:

| Attribute | Upstream source of the value actually used |
|---|---|
| `wingframe_position` | `SimulationsSettings()` instance in `flapping_forces.py` |
| `wingframe_position_tail` | two separate `SimulationsSettings()` instances (`flapping_forces.py` for the tail velocity, `TailModels.py` for the tail neutral point) |
| `tail_length` | both instances, plus a Reynolds number computed once at import time in `TailModels.py` |
| `tail_opening` | `TailModels.py` instance (the lifting line never passed an opening, so the tail was closed unless `settings.py` was edited) |
| `frequency` | module constant `omega = 4*2*pi` in `bird.py` |
| `tail_chord` | unused anywhere (still unused) |

`mass` and `g` were read correctly. `I_yy = 0.1` was hard-coded (four places).

Consequences for upstream usage patterns:
- Setting any attribute in the table on a `BirdModel` (for example in a
  parameter sweep) had **no effect** on the results. With this fork it does.
- Editing `aero_package/settings.py` before running worked (and was the only
  way to open the tail or move the wing).
- Changing the settings objects at run time was inconsistent: the two
  instances had to be changed together, and the tail Reynolds number kept its
  import-time value.
- Changing `frequency` on the bird left the wing flapping at 4 Hz; with a
  period set to 1/f the shooting problem then mixed two frequencies.
- `SaveData.write_simulation_settings` wrote the `BirdModel` values of wing
  position, tail position and tail opening, which were not the values used.

Verification: with the same values given to upstream through its hidden
settings (and `omega`), the right-hand side of the package is bitwise
identical (`baseline/compare_rhs.py`, variants: wing position, open tail,
5 Hz).

Environment-dependent differences (not code changes): with numpy 2.5.5 (on
macOS arm64 linked to Apple Accelerate instead of OpenBLAS) results differ by
at most 1.1e-12 relative (bird cases, Rossler, forced Van der Pol), and by
1.8e-7 for the redox oscillator, whose result is sensitive at that level to
roundoff (a 1e-15 perturbation of x0 moves it by 2.2e-7). The redox
regression tolerance was relaxed from 1e-8 to 1e-6 accordingly; see
`baseline/README.md`.

## [Unreleased]

### Repository history rewritten before the first public push (2026-11-22)

- `pdfs/` (four third-party papers shipped by upstream) was removed from
  every commit, including the `upstream-v1.1` import; the README links now
  point to the copies in the upstream repository. Nothing else in the
  trees changed; the baseline tools use `upstream-v1.1` as before.
- Author, committer and tagger email changed to a GitHub noreply address.
- All commit hashes and tags changed accordingly (same messages and dates).

### Stage 6: tests and continuous integration

- `tests/hopf.py`: a test system (Hopf normal form plus a stable direction)
  whose limit cycle, period, Floquet multipliers and flow map are known in
  closed form.
- Fast suite (about 90 tests, seconds): analytical Jacobians of every toy
  system against central differences; order of accuracy of `rk2`, `rk3`,
  `rk4`; interval Jacobians (variational and finite-difference) against
  the exact flow map; unknown- and known-period solvers against the exact
  period and multipliers; non-convergence reporting. Tolerances record the
  accuracy of the upstream algorithms as they are.
- Slow suite (`pytest -m slow`): all three baseline bird cases end to end
  from their config files (`bird_main`, `bird_study1`,
  `bird_a42_main_numerics`), including period and trajectory times.
- GitHub Actions (`.github/workflows/tests.yml`): fast suite on Python
  3.11-3.14 with the locked dependencies and on the lowest declared
  dependencies (numpy 1.26.4, scipy 1.17.1, matplotlib 3.11.2); slow suite
  nightly and on demand.
- Found by the tests (upstream behaviour, unchanged, recorded as strict
  `xfail`): `Torus.get_stability_matrix` is unfinished and returns `None`;
  the finite-difference interval Jacobians perturb each coordinate by
  `x[j]*epsilon`, so a coordinate that is exactly zero gives NaN (and a
  very small one a step dominated by roundoff).
- Measured (upstream behaviour, unchanged): the known-period analytical
  monodromy, integrated with RK2 on 30 points per shooting interval, is
  accurate to about 3e-3 on the unit multiplier with 4 shooting points
  (1e-2 with 2), against 1e-5 for the unknown-period one (500 points).
  With 2 shooting points the known-period solver stalls near
  max|E| = 1e-7 on the test system.

### Stage 5: run provenance

- `stabilitytool-birdflight run CASE.yaml --output DIR` (also
  `python -m stabilitytool_birdflight`, or `runs.run_bird_case` from Python)
  writes a self-describing directory: `config.yaml` (fully resolved),
  `input.<ext>` (verbatim copy), `result.npz` (`LimitCycleResult.from_npz`),
  `summary.json` (results, error history, per-iteration times), 
  `provenance.json` (package version, git commit and dirty flag, uv.lock
  checksum, Python/dependency/BLAS versions, platform, threading variables,
  command line, input and config checksums, timestamps, status) and
  `solver.log`. No default location; non-empty directories are refused
  unless `--overwrite`; failed runs are recorded (status `failed`,
  `error.txt`). Host and user names are not recorded.
- `stabilitytool-birdflight validate CASE.yaml [--print]` and
  `stabilitytool-birdflight show DIR`.
- Solvers record per-iteration wall times (`LimitCycleResult.iteration_times`).
- No hard-coded paths and no bare `except:` left in the package. `SaveData`
  needs an explicit results folder; its errors are raised; the wrist offset
  and phase it writes are now correct (upstream wrote the amplitude).
  `main.py` takes the output folder as argument and no longer crashes on the
  undefined `eigenvalues`.
- Slow test suite (`pytest -m slow`, excluded by default): bird_main end to
  end from its config file.

### Stage 4: configuration files, model interface, result object

- A bird case is fully specified by one YAML (or JSON) file with sections
  `kinematics`, `aerodynamics`, `flight`, `solver`; all angles in degrees.
  `BirdCaseConfig.load(path).solve()` returns a `LimitCycleResult`;
  `case.save(path)` writes the fully resolved case. Example files:
  `examples/configs/` (the three baseline bird cases).
- Per-module config dataclasses with validation: `kinematics.config`
  (`WingConfig`, `JointConfig`), `aerodynamics.config`
  (`AerodynamicsConfig`), `flight.config` (`FlightConfig`, `TailConfig`,
  `BirdCaseConfig`), `dynamics.config` (`SolverConfig`). Shared reader and
  validator: `configio`. New dependency: PyYAML.
- The solver period of a bird case defaults to 1/frequency; an inconsistent
  period is rejected.
- `dynamics.model.ODEModel` Protocol (`dimension`, `dynamics(x, t)`,
  optional `jacobian(x, t)`; `get_stability_matrix` still accepted).
  `MultipleShooting` takes the dimension from the model (was hard-coded 4),
  so the forced Van der Pol example works.
- `dynamics.result.LimitCycleResult` replaces the positional tuple
  (`mysol[3]`, `mysol[4]`); `Solver.lma()` keeps returning the tuple.
- `BirdModel`: `dimension`, `jacobian`, and the remaining aerodynamic
  parameters (`cl_alpha`, `kin_viscosity`, `tail_reference_velocity`,
  `circulation_tol`, `circulation_max_iterations`) as attributes.
- Baseline tools: `generate_baseline.py --target package` runs every case
  through the new API (bird cases from the YAML files); `compare_rhs.py`
  builds the package birds from the YAML files.
- Tests: config round trip (YAML and JSON), validation errors, exact degree
  conversion, config-built vs hand-built bird, toy regression through
  `SolverConfig`, model Protocol (58 tests).

### Stage 3: independent modules and explicit parameters

- New layout: `dynamics/` (multiple shooting, solvers, integrators,
  Lyapunov; toy systems in `dynamics/systems/`), `kinematics/` (joints,
  feathers, wing geometry: `BirdWing`), `aerodynamics/` (lifting line, tail),
  `flight/` (`BirdModel`, longitudinal dynamics). `kinematics`,
  `aerodynamics` and `dynamics` do not import each other (tested).
- `aerodynamics.flapping_forces.get_flappingforces(freestream,
  angular_velocity, ...)` takes vectors instead of the flight state, and
  explicit keyword parameters (wing/tail position, tail length and opening,
  `rho`, `cl_alpha`, viscosity, tail reference velocity, iteration
  settings). `TailModels` functions likewise. `settings.py` removed; no
  import-time computations.
- `kinematics.BirdWing`: frequency, bone lengths, feather lengths and angles,
  body half-width, finite-difference step as parameters;
  `get_lifting_line_kinematics(t)` returns the lifting line and its velocity.
  `Joint.motion_joint(t, frequency)`.
- `flight.BirdModel`: new attributes `inertia_yy`, `stability_fd_step`,
  `rho`; extra constructor keywords go to `BirdWing`.
- Top-level names (`MultipleShooting`, `Rossler`, ...) are imported lazily.
- Tests (pytest, `uv run pytest`): parameter sensitivity (18 parameters),
  module independence, kinematics without aerodynamics/flight.
- `baseline/compare_rhs.py`: bitwise check of the bird right-hand side
  against the upstream tag (seconds instead of a full bird run).
- Found while testing (upstream behaviour, unchanged): with the upstream
  skeleton discretisation only feathers 1, 3, 5 and 7 shape the wing;
  feathers 2, 4 and 6 have zero weight.
- Not yet adapted: the unused duplicate `ms_package/bird_dynamics.py` still
  calls the old `get_flappingforces` signature (to be removed in Stage 7).

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
