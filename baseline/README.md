# Stage 1 baseline

Reference outputs of the **unmodified upstream multiflap v1.1** (tag
`upstream-v1.1`). Every later refactoring stage must reproduce them within the
tolerances below (CLAUDE.md, ground rule 1).

- `generate_baseline.py`: runs the cases against the upstream code. No upstream
  file is edited; all workarounds are in this script and listed per case in the
  JSON summaries.
- `compare_baseline.py`: compares a candidate output directory with `data/`.
- `ENVIRONMENT.md`, `requirements-baseline.txt`: the exact environment.
- `data/`: one `<case>.npz` (arrays), `<case>.json` (readable summary with
  settings and provenance) and `<case>.log` (upstream console output) per case.

```bash
.venv/bin/python baseline/generate_baseline.py --out /tmp/candidate --jobs 6
.venv/bin/python baseline/compare_baseline.py /tmp/candidate
```

## Stored fields (`<case>.npz`)

| Field | Meaning |
|---|---|
| `points` | converged multiple-shooting points, shape (M, n) |
| `points_history` | MS points at each stage of the solve (upstream `ptlist`) |
| `error_history` | max\|E\| at each evaluation of the MS scheme |
| `n_iterations` | number of Levenberg–Marquardt updates (= `len(error_history) - 1`) |
| `final_error` | last entry of `error_history` |
| `period` | last time of the limit-cycle trajectory |
| `trajectory_t`, `trajectory_x` | full limit-cycle trajectory (upstream `mysol[3]`) |
| `monodromy` | monodromy matrix (upstream `mysol[4]`) |
| `multipliers`, `eigenvectors` | `np.linalg.eig(monodromy)`, in eig order |
| `multipliers_sorted`, `eigenvectors_sorted` | sorted by descending modulus, then descending imaginary part |
| `elapsed_s`, `converged` | wall time of the solve, final error below tolerance |

Iteration counting: upstream prints one "Iteration i" line per evaluation, so
the bird case of `main.py` shows 8 iterations (i = 0..7); this is 7 LM updates.
The baseline stores the number of updates.

## Cases

| Case | Source | Notes |
|---|---|---|
| `rossler` | `examples/rossler_system.py` | plotting skipped |
| `redox` | `examples/redox_oscillator.py` | SaveData and plotting skipped |
| `forced_vdp` | `examples/forced_van_der_pol.py` | `ms_obj.dim` overridden to 2 (upstream hard-codes `self.dim = 4`, `ms_package/multiple_shooting.py:11`) |
| `bird_main` | `multiflap/main.py` as-is | A_s,x = 44°, x0 = [18, 0.5, 0.1, 0.01], M = 2, t_steps = 70; eigenvalues computed in the generator |
| `bird_study1` | study_1 Sect. 4.1, Tables 1–2 | A_s,x = 42°, x0 = [16.5, 0.5, 0.5, 0], M = 5, t_steps = 38 (see below) |
| `bird_a42_main_numerics` | diagnostic | main.py numerics (M = 2, t_steps = 70) with A_s,x = 42° and the paper's x0 |

Not included: `lorenz` (`examples/lorentz_system.py`). Even after fixing the
constructor call and the `lma(5.)` call in the generator, the solver does not
converge within 100 iterations with the example's settings and then raises
`UnboundLocalError` on `jac_sg`. It can still be run with `--cases lorenz`.

## Results

| Case | Iter. | Final error | Period | Floquet multipliers |
|---|---|---|---|---|
| `rossler` | 10 | 1.3e-08 | 5.8810885588 | −2.4039543, 0.99999982, −1.27e-14 |
| `redox` | 5 | 9.8e-07 | 24.9525623110 | 0.99999752, 0.2777898, 4.96e-08, −5.2e-18 |
| `forced_vdp` | 5 | 7.0e-08 | 10.4719755 (fixed) | 0.39864701, 1.4241676e-05 |
| `bird_main` | 7 | 3.7e-06 | 0.25 (fixed) | 1.40110, 0.81886 ± 0.26393j, 0.19909 |
| `bird_study1` | 9 | 3.6e-06 | 0.25 (fixed) | 1.40955, 0.82440 ± 0.26237j, 0.19829 |
| `bird_a42_main_numerics` | 7 | 3.6e-06 | 0.25 (fixed) | 1.40876, 0.82330 ± 0.26285j, 0.19900 |

Rössler agrees with the published reference (Dednam & Botha 2015) and with the
audit in CLAUDE.md. `bird_main` reproduces the audit values exactly
(multipliers and limit-cycle state [18.6701, −2.15092, −0.120731, −0.116113]).

## Reproducibility and tolerances

Every case was run twice in independent processes (`baseline/runs/run1`,
`run2`, not committed), and `data/` is a third run from the committed
generator. All runs are **bitwise identical** for every stored array except
`elapsed_s`. Tolerances in `compare_baseline.py`:

- toy systems: relative 1e-8 (as planned);
- bird cases: started at 1e-6, tightened to **1e-8** given bitwise
  run-to-run reproducibility. Different platforms or numpy 2 (Stage 2) may
  need this relaxed; if so, record the measured difference here.

Provenance note: the JSON files in `data/` record commit `92065b1` with
`repo_dirty: true`. At generation time no tracked file was modified; the flag
was set only by untracked files (`multiflap-master.zip`, this README draft and
`data/` itself). The generator was changed afterwards to ignore untracked
files. `upstream_code_unmodified_vs_tag` is `true` for every case.

`n_iterations` must match exactly. Comparisons are norm-wise relative:
`max|a − b| / max|b|` per array.

## study_1 reference case vs the paper

### Parameters

Table 1(b) of study_1 against the joints hard-coded in `main.py`. The paper
and the code use different reference systems for the joint angles. The paper's
frame (Fig. 2) is x forward, y right (spanwise), z down. The code's wing frame
is x spanwise (right wing), y up, z backward. This follows from
`U = [0, w, u]` and `ang_velocity = [q, 0, 0]` in
`aero_package/flapping_forces.py`, the force signs in `odes/bird_dynamics.py`,
and `wingframe_position = [0, 0, -0.05]` (5 cm ahead of the centre of mass).
Matching rows by value gives:

| Paper row (q0, A, φ) [deg] | Code joint (`Joint(offset, amplitude, phase)`) | Match |
|---|---|---|
| Shoulder y (11.5, 0.8, −90) | `shoulder.axis_x` (0.2 rad = 11.46°, 0.014 rad = 0.80°, −90°) | yes (rounding) |
| Shoulder x (0, A_s,x, 180) | `shoulder.axis_z` (0, 44°, 180°) | amplitude: 44° in code, 42° in paper |
| Shoulder z (19, 20, 90) | `shoulder.axis_y` (−19°, 20°, 90°) | yes: same backward sweep, opposite sign because the axes differ (paper z down, code y up) |
| Elbow x (30, 30, −90) | `elbow.axis_y` (30°, 30°, −90°) | yes |
| Wrist z (−30, 30, 90) | `wrist.axis_y` (−30°, 30°, 90°) | yes |
| Wrist y (0, 30, −90) | `elbow.axis_x` (0, 30°, −90°) | values yes, but the joint is labelled differently (wrist in paper, elbow in code); not checked physically |
| — | `wrist.axis_z` (0, 0, 0) | inactive in code, absent from paper |

Check of the shoulder kinematics: the right-wing lifting-line tip computed
from the code as-is, in the paper's body frame relative to G, spans
x′ ∈ [−0.19, +0.08] m and z′ ∈ [−0.39, +0.42] m. At t = 0 it sits at
x′ = +0.05 m, z′ ≈ 0 and moves down. This matches Fig. 9 (tip path) and the
statement that t = 0 is mid-downstroke (Sect. 4.1, Fig. 8). With the offset
set to +19° in the code instead, the wing sweeps forward (x′ up to +0.45 m),
which contradicts Fig. 9. So the code's −19° is the paper's +19°.

Other parameters:

| Parameter | Paper | Code | Match |
|---|---|---|---|
| Mass | 1.2 kg | `BirdModel.mass = 1.2` | yes |
| I_y | 0.1 kg m² | `0.1` hard-coded, `odes/bird_dynamics.py:52` | yes |
| Bone lengths l_a, l_f, l_h | 0.134, 0.162, 0.084 m | same (`bird_model.py`) | yes |
| Primary feathers | 0.25, 0.275, 0.25 m | 0.25, 0.225, 0.2 m (`aero_package/Plumes.py:27-29`) | **no** |
| Secondary feathers | 0.225, 0.2, 0.175, 0.15 m | 0.175, 0.15, 0.125, 0.1 m (`Plumes.py:30-33`) | **no** |
| Frequency | 4 Hz | 4 (module constant, `aero_package/bird.py:27`) | yes |
| Wing frame ahead of CoM | 5 cm | `wingframe_position = [0, 0, −0.05]` | yes |
| M (Table 2) | 5 | `main.py`: 2; `bird_study1`: 5 | |
| Time steps per period (Table 2) | 150 | `main.py`: 69; `bird_study1`: 148 | see below |
| Integrator (Sect. 3.4, Table 2) | RK4 | RK4 for the trajectory, but the variational equations giving the monodromy matrix use **RK2 with 30 points per interval**, hard-coded (`ms_package/multiple_shooting.py:155,164`) | partly |
| Tolerance | 1e-5 | 1e-5 | yes |

Time steps: each of the M − 1 shooting intervals is integrated on
`linspace(t, t + tau, t_steps)`, i.e. `t_steps − 1` steps per interval. With
M = 5 (4 intervals), exactly 150 steps per period is impossible; `t_steps = 38`
gives 148 (39 would give 152).

### Results

| Quantity | Paper (Sect. 4.1, Table 3) | `bird_study1` | `bird_a42_main_numerics` | `bird_main` (44°) |
|---|---|---|---|---|
| Λ1 | 1.40 | 1.40955 | 1.40876 | 1.40110 |
| Λ2,3 | 0.829 ± 0.260j | 0.82440 ± 0.26237j | 0.82330 ± 0.26285j | 0.81886 ± 0.26393j |
| Λ4 | 0.212 | 0.19829 | 0.19900 | 0.19909 |
| u(t0) | 18.24 | 18.0675 | 18.0695 | 18.6701 |
| w(t0) | −1.93 | −1.9976 | −1.99785 | −2.15092 |
| q(t0) | −0.10 | −0.11246 | −0.11243 | −0.12073 |
| θ(t0) | −0.115 | −0.11715 | −0.11717 | −0.11611 |
| e1 (unit norm) | [−0.69, 0.68, 0.12, 0.16] | [−0.698, 0.685, 0.130, 0.163] | [−0.699, 0.684, 0.130, 0.163] | [−0.699, 0.686, 0.120, 0.162] |
| λ1 = ln(Λ1)/T | 1.34 s⁻¹ | 1.373 s⁻¹ | 1.371 s⁻¹ | 1.349 s⁻¹ |
| LM updates | 7 | 9 | 7 | 7 |

Observations:

1. Going from 44° to 42° moves the result towards the paper in w(t0), q(t0),
   Λ2,3 and e1, but u(t0) moves past the paper value (18.67 → 18.07 vs
   18.24), and Λ4 barely changes (0.199 vs 0.212, about 7% off).
2. The discretisation (M = 2 / 69 steps vs M = 5 / 148 steps) changes the
   result only at the 1e-3 level, so it does not explain the gap.
3. The leading eigenvector agrees with the paper to about 0.01.
4. So the remaining differences come from something else. Candidates, none
   tested yet: the feather lengths, the RK2 monodromy integration, or
   upstream code changes after publication. (The shoulder-z offset is not a
   candidate: it is the same in code and paper, see above.)
