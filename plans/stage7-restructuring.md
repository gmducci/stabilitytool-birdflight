# Stage 7 plan: internal restructuring

Status: **approved 2026-11-23**; the user accepted the recommended answer to
every decision in Section 6.

## 1. Why

Stages 2 to 6 changed how the code is wired: packaging, explicit parameters,
configs, a result object, provenance and tests. They did not change how the
code itself is organised. Stage 3 moved the upstream files into the four
subpackages but kept their names, their split into files and their APIs. The
result still reads as multiflap:

- **File names** are CamelCase or unclear (`TailModels.py`, `CompMatrix.py`,
  `RotationMatrix.py`, `Plumes.py`, `lma_solver_period.py`) or have typos
  (`lorentz.py`, `tail_postprcessing.py`).
- **Function names** are hard to read or have typos (`get_flappingforces`,
  `get_kinematicvelocity`, `inucedvel_filament`, `improveline_iteration`).
- **Duplicated code:**
  - `multiple_shooting.py` and `multiple_shooting_period.py` are about 350
    lines each and nearly identical (about 100 lines differ).
  - `lma_solver.py` and `lma_solver_period.py` differ by 21 lines.
  - `ms_package/bird_dynamics.py` is a copy of `flight/bird_dynamics.py`.
- **Dead code:**
  - `integrator_2.py`, `MergeLines.py`, `polar.py` (all commented out),
    `polar.txt`, `circulation_polar` (calls the undefined
    `polar.lift_coefficient`), `improveline_new`, and the unused `WingState`
    namedtuple (its field order differs from the list actually passed around).
  - Also: `utils/`, `visualisation/`, and `utilities/` except `SaveData`.
- **Scripts inside the package:** `main.py`, `*_main.py`, `main_torus.py` and
  `main_isothermal.py`.
- **Coupling through inheritance:** `BirdModel(BirdWing)`. The flight model *is
  a* wing, and its free functions in `bird_dynamics.py` take `self` and are
  attached to the class afterwards.
- **Values instead of structures:**
  - Aerodynamic forces are returned as a 9-element list, unpacked by position
    (`[_, Fy, Fz, My, F_tail, _, _, _, _]`).
  - The wing state is a list in an unusual order.
- **Configs that do more than hold data:**
  - `SolverConfig.solve` runs the solver and redirects `stdout` to hide the
    upstream `print`s.
  - It turns an `UnboundLocalError` into a non-convergence error.
  - `BirdCaseConfig.build_model` builds a default `BirdModel` and then
    overwrites 15 attributes one by one.
- **Large functions:** `BirdWing.get_wingenvelope` is about 300 lines, and all of
  `kinematics/wing.py` is one class of nearly 600 lines.

## 2. Target layout

```
src/stabilitytool_birdflight/
  __init__.py            lazy exports (updated to the new names)
  __main__.py, cli.py    unchanged
  configio.py            unchanged
  runs.py, provenance.py unchanged

  dynamics/              nonlinear-dynamics methods; numpy/scipy only
    model.py             ODEModel protocol (unchanged)
    integrators.py       rk2, rk3, rk4
    shooting.py          multiple shooting: shared base + known/unknown period
    solver.py            one Levenberg–Marquardt solver, logging, ConvergenceError
    limit_cycle.py       find_limit_cycle(model, solver_config) -> LimitCycleResult
    result.py            LimitCycleResult (unchanged)
    lyapunov.py          largest Lyapunov exponent
    config.py            SolverConfig (data and validation only)
    systems/             toy systems (see decision D4)

  kinematics/            biomechanics; no aerodynamics
    joints.py            Joint, Shoulder, Elbow, Wrist, JointAngles (named)
    rotations.py         rotation_matrix, scaling_matrix
    feathers.py          feather geometry (was Plumes.py)
    skeleton.py          bone positions from joint angles (forward kinematics)
    envelope.py          leading/trailing edges from skeleton + feathers
    lines.py             quarter-chord line, smoothing, distances, left/right merge
    wing.py              Wing: geometry(t) -> WingGeometry, velocity(t)
    config.py            WingConfig, JointConfig

  aerodynamics/          lifting line and tail; knows nothing about birds
    lifting_line.py      lifting_line_forces(...) -> AeroForces (named fields)
    vortex.py            induced velocities of filaments and segments
    tail.py              tail geometry and forces (was TailModels.py)
    config.py            AerodynamicsConfig

  flight/                the only module importing the others
    bird.py              BirdModel: composes a Wing and the aerodynamic settings
    equations.py         longitudinal equations of motion, FD stability matrix
    forces.py            flight state -> free stream -> wing + tail -> body forces
    config.py            FlightConfig, TailConfig, BirdCaseConfig

examples/                every script (the *_main.py files move here)
```

## 3. Rename table

### Files

| Now | After | How |
|---|---|---|
| `dynamics/rk_integrator.py` | `dynamics/integrators.py` | move |
| `dynamics/multiple_shooting.py` + `multiple_shooting_period.py` | `dynamics/shooting.py` | move, then merge (logic) |
| `dynamics/lma_solver.py` + `lma_solver_period.py` | `dynamics/solver.py` | move, then merge (logic) |
| `dynamics/lyapunov_exponents.py` | `dynamics/lyapunov.py` | move |
| `dynamics/integrator_2.py` | — | delete (unused) |
| `dynamics/systems/lorentz.py` | `dynamics/systems/lorenz.py` | move |
| `dynamics/systems/forced_vdp.py` | `dynamics/systems/van_der_pol.py` | move |
| `dynamics/systems/redox_oscillation.py` | `dynamics/systems/redox.py` | move |
| `dynamics/systems/goodwin_model.py` | `dynamics/systems/goodwin.py` | move |
| `dynamics/systems/lotka.py` | `dynamics/systems/lotka_volterra.py` | move |
| `dynamics/systems/template.py` | `examples/model_template.py` | move |
| `kinematics/bird.py` | `kinematics/joints.py` | move |
| `kinematics/RotationMatrix.py` + `CompMatrix.py` | `kinematics/rotations.py` | move + join |
| `kinematics/Plumes.py` | `kinematics/feathers.py` | move |
| `kinematics/line_functions.py` + `distances_functions.py` | `kinematics/lines.py` | move + join |
| `kinematics/wing.py` | `wing.py`, `skeleton.py`, `envelope.py` | split (logic) |
| `kinematics/MergeLines.py` | — | delete (unused; `BirdWing.merge_lines` is used) |
| `aerodynamics/flapping_forces.py` | `aerodynamics/lifting_line.py` | move |
| `aerodynamics/circulation.py` | `lifting_line.py` (iteration) + `vortex.py` | split |
| `aerodynamics/TailModels.py` | `aerodynamics/tail.py` | move |
| `aerodynamics/polar.py`, `polar.txt` | — | delete (empty; only dead code used it) |
| `flight/bird_model.py` | `flight/bird.py` | move |
| `flight/bird_dynamics.py` | `flight/equations.py` + `flight/forces.py` | split (logic) |
| `ms_package/` | — | delete (duplicate) |
| `main.py`, `*_main.py`, `main_torus.py`, `main_isothermal.py` | `examples/` | move, dedupe with existing examples |
| `utilities/save_data.py` | see decision D3 | |
| `utilities/LimitCycleForces.py` | see decision D3 | |
| `utilities/tail_postprcessing.py`, `utils/mf_plots.py`, `visualisation/` | see decision D3 | |

### Names (classes and functions)

| Now | After |
|---|---|
| `MultipleShooting` / `MultipleShootingPeriod` | `KnownPeriodShooting` / `UnknownPeriodShooting` (decision D2) |
| `Solver` / `SolverPeriod`, method `lma()` | `levenberg_marquardt(shooting, tolerance, max_iterations)` |
| `SolverConfig.solve` / `.build` | `find_limit_cycle(model, config)` in `dynamics/limit_cycle.py` |
| `LyapunovExponents.get_lyapunov_exponent` | `largest_lyapunov_exponent(...)` |
| `Lorentz` | `Lorenz` |
| `lotka` (function) | `LotkaVolterra` (class, like the other systems) |
| `Joint.motion_joint(t, f)` | `Joint.angle(t, frequency)` |
| `BirdWing` | `Wing` |
| `get_wingstate` | `Wing.joint_angles(t)` → `JointAngles` (named) |
| `get_wingenvelope` | `envelope.wing_edges(...)` |
| `get_liftingline`, `merge_lines` | `lines.quarter_chord_line(...)`, `lines.merge_left_right(...)` |
| `get_lifting_line_kinematics(t)` | `Wing.geometry(t)` → `WingGeometry(line, chord_dir, up_dir, chord, velocity)` |
| `get_kinematicvelocity` | `lines.centre_point_velocity` |
| `RotationMatrix`, `CompMatrix` | `rotation_matrix`, `scaling_matrix` |
| `plumes` | `feather_geometry` |
| `quarterchord_naive`, `smooth_line`, `smooth_quarterline`, `improveline_iteration` | `quarter_chord_naive`, `smooth_line`, `smooth_quarter_chord_line`, `refine_line` |
| `distance_point2line`, `distance_line2line` | `distance_point_line`, `distance_line_line` |
| `get_flappingforces` | `lifting_line_forces(...)` → `AeroForces` (named fields) |
| `circulation` | `solve_circulation` |
| `inucedvel_filament`, `inducedvel_segment` | `induced_velocity_filament`, `induced_velocity_segment` |
| `delta_tail`, `tail_geometry` | `tail_force`, `tail_geometry` |
| `BirdModel.get_aeroforces` | `BirdModel.forces(x, t)` → `BodyForces` (named fields) |

**Kept on purpose** (decided 2026-11-19): the model protocol names
`dimension`, `dynamics(x, t)`, `jacobian(x, t)`, with `get_stability_matrix`
accepted as the upstream alias. Config file keys (YAML) do not change, so
`examples/configs/*.yaml` and saved run directories stay valid.

## 4. Structural changes (the parts that are not pure renames)

1. **One solver.** `levenberg_marquardt` replaces `Solver` and
   `SolverPeriod`. Progress is reported with `logging`, not `print`, so the
   `stdout` redirection in `SolverConfig.solve` goes away. If the solver does
   not converge it raises `ConvergenceError` (today it crashes with
   `UnboundLocalError`, which the config catches).
2. **One shooting implementation.** A shared base holds the parts that are
   now duplicated (trajectory integration, interval Jacobians, analytical and
   numerical). Two thin subclasses add the known-period and unknown-period
   differences (the unknown vector and the period column of the Jacobian).
3. **Configs hold data only.** `find_limit_cycle(model, config)` does what
   `SolverConfig.build` and `.solve` do now. `BirdCaseConfig.build_model`
   passes everything to constructors instead of overwriting attributes.
4. **Wing split.** `get_wingenvelope` (about 300 lines) becomes
   `skeleton.py` (bone and joint positions) plus `envelope.py` (feathers and
   edges). `Wing` keeps the gait (joints, frequency) and the morphology and
   returns a `WingGeometry`. The wing velocity stays a backward finite
   difference over `kinematic_dt`, as now.
5. **Named results.** `AeroForces`, `BodyForces`, `JointAngles` and
   `WingGeometry` are small dataclasses or namedtuples that replace lists
   unpacked by position.
6. **Composition in `flight`.** `BirdModel` has a `wing: Wing`, aerodynamic
   settings and body parameters (mass, inertia, g, wing and tail positions).
   It no longer inherits from the wing. `equations.py` holds the longitudinal
   equations and the finite-difference stability matrix as plain functions;
   `forces.py` maps the flight state (u, w, q, θ) to the free stream and
   angular velocity, then calls kinematics and aerodynamics.

What does **not** change: the order of floating-point operations in the
force, kinematics and solver code, every default value, and the axis
conventions (wing frame: x spanwise, y up, z backward). Renaming the axes is
outside this stage.

## 5. Commit order and checks

Ground rule 3: moves and logic changes never share a commit.

| Step | Commits | Check before each commit |
|---|---|---|
| A. Delete dead code (after the user agrees, D3) | one per item | fast suite, `compare_rhs.py` |
| B. File moves (`git mv` + import fixes) | one per subpackage | fast suite, `compare_rhs.py` bitwise |
| C. Name changes | one per subpackage | fast suite, `compare_rhs.py` bitwise |
| D1. One solver + logging + `ConvergenceError` | 1–2 | fast suite (toy baseline 1e-8), slow suite |
| D2. Shooting base class | 1 | fast suite, slow suite |
| D3. `find_limit_cycle`, configs data-only | 1 | fast suite, `compare_rhs.py` |
| D4. Wing split + `WingGeometry`, `JointAngles` | 2 | `compare_rhs.py` bitwise, kinematics tests |
| D5. `AeroForces`, `BodyForces` | 1 | `compare_rhs.py` bitwise |
| D6. `BirdModel` composition, `equations.py`, `forces.py` | 2 | `compare_rhs.py` bitwise, slow suite |
| E. Scripts → `examples/`, dedupe, update `__init__` exports | 2–3 | run every example with `MPLBACKEND=Agg` |
| F. Tests, `baseline/` tools, README, CHANGELOG, CLAUDE.md, docs | 2–3 | fast + slow suite; tag `stage7-restructuring` |

- **Target: bitwise-identical results.** Every step above should reproduce
  `compare_rhs.py` bitwise and the stored baseline within the Section 5
  tolerances. If a step cannot do this (most likely D1/D2), stop and report it
  to the user before going on (ground rule 2).
- `baseline/generate_baseline.py --target upstream` still runs the upstream
  tag; only its package path changes.
- The independence test (`tests/test_module_independence.py`) keeps
  guarding the rule that kinematics, aerodynamics and dynamics do not import
  each other.
- The CHANGELOG gets a full table of old and new names under "Changed
  (API)", with no entry under "Changes to numerical results".

## 6. Decisions for the user

- **D1. Old import paths.** Option (a), no compatibility shims: old imports
  break, and the CHANGELOG table says what replaces them (recommended: the
  fork has no external users yet and is not on PyPI). Option (b), keep
  deprecated aliases for one release.
- **D2. Class names.** Should the solver-side names follow the table above
  (`KnownPeriodShooting`, `levenberg_marquardt`, `Wing`, …)? Or should some
  upstream names stay for continuity with the multiflap paper and docs
  (e.g. `MultipleShooting`)?
- **D3. Unused research code.** Keep and port, move to `examples/`, or delete,
  item by item:
  - `utilities/LimitCycleForces.py` (aerodynamics re-run along the limit
    cycle; likely needed for the power and cost-of-transport results of
    study_2): suggest porting it to `flight/postprocessing.py`.
  - `utilities/tail_postprcessing.py` (hard-coded glob over result folders):
    suggest deleting it.
  - `visualisation/phase_animation_*.py`, `utils/mf_plots.py`: suggest moving
    them to `examples/plotting/`.
  - `utilities/save_data.py` (`SaveData`, superseded by `runs.py`): suggest
    deleting it, together with its lazy export.
- **D4. Toy systems** (still open from Section 6 of CLAUDE.md): suggest
  keeping Rössler, redox, forced Van der Pol and Lorenz in
  `dynamics/systems/` (the fast suite uses them). Goodwin, Jaschinski, torus,
  Lotka–Volterra and isothermal reaction would go to `examples/systems/` or
  stay.
- **D5. Stage numbering.** This becomes Stage 7. The current Stage 7 (logging,
  type hints, docstrings, docs, `CITATION.cff`) becomes Stage 8, minus the
  duplicate removal and `print` → `logging` work done here.
