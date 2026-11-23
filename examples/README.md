# Examples

Run from the repository root with the package installed (`uv run python
examples/<name>.py`). Each script prints the limit cycle (period, iterations,
state at t0, Floquet multipliers); `--figure FILE` also saves a plot.

| Script | System | Notes |
|---|---|---|
| `bird_limit_cycle.py` | flapping bird, built in Python (`Wing` + `BirdModel`) | about 5 min; `--output result.npz` |
| `configs/*.yaml` | the bird cases as config files | `stabilitytool-birdflight run CASE.yaml --output DIR` |
| `rossler.py` | Rössler, unknown period | reference: Dednam & Botha (2015) |
| `redox.py` | redox oscillator, unknown period | |
| `forced_van_der_pol.py` | forced Van der Pol, known period | |
| `lorenz.py` | Lorenz: unstable periodic orbit (r < 24.74), Lyapunov exponent (r = 28) | |
| `isothermal_reaction.py` | isothermal autocatalytic reaction | model in `systems/` |
| `goodwin.py` | Goodwin oscillator and its response to a pulse | model in `systems/` |
| `model_template.py` | template for a new model | see `stabilitytool_birdflight.dynamics.model` |

`tests/test_examples.py` runs the quick examples (all but the bird and
Lorenz) and checks their periods.

## `systems/`

Toy models moved out of the package in Stage 7 (decision D4). They follow the
model interface (`dimension`, `dynamics(x, t)`, `jacobian` or
`get_stability_matrix`).

| Model | Status |
|---|---|
| `goodwin.py`, `isothermal_reaction.py` | used by the examples above; analytical Jacobians tested |
| `torus.py` | `get_stability_matrix` unfinished upstream (returns `None`; strict `xfail` in the tests); no example (the upstream script never ran the solver) |
| `lotka_volterra.py` | untested; the upstream script did not run |
| `jaschinski.py` | **does not parse** (syntax errors already upstream); kept for reference |

## `plotting/`

Upstream plotting helpers, unchanged: `plots.py` (class `Plot`, quick
figures of limit cycles and multipliers) and `phase_animation_2d.py`,
`phase_animation_3d.py` (Lorenz animations). They are not tested.
