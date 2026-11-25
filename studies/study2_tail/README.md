# Study_2 reconstruction: tail opening, stability, and the tail pitch-rate sign

This folder reconstructs the setup of study_2 (Ducci, Vitucci, Chatelain,
Ronsse, *On the role of tail in stability and energetic cost of bird flapping
flight*, Scientific Reports 12:22629, 2022, doi:10.1038/s41598-022-27179-7)
on top of this package, and records a sign error in the tail model found
while doing so.

It lives on the branch `study2-reconstruction` and does **not** change the
package: everything specific to study_2 is in this folder. With every option
off, `forces.py` is bitwise identical to the package (`check_equivalence.py`).

## Sources

Study_2 cannot be reproduced from multiflap v1.1 (the base of this fork): its
force model and kinematics differ. The study_2 production code was recovered
from the first author's backups (2026-11-25); it is **not** included here.

| Source | What it gave |
|---|---|
| `main_parallel.py` (cluster script that ran the parametric sweep) | joint trajectories, solver settings, level-flight trim procedure |
| study_2 `aero_package/` (dated 2021-09-29) | force model differences vs v1.1, tail length, feathers |
| Paper and its supplementary material (Table S1, sections S1–S2) | Table 1 cases and published multipliers |

Diff of the study_2 `aero_package` against v1.1: only `flapping_forces.py`,
`TailModels.py`, `settings.py` and `bird_model.py` changed (`bird_model.py`
only in its constructor). The wing geometry, feathers (`Plumes.py`),
circulation solver and joints (`bird.py`) are identical to v1.1, hence to
this package.

Still missing: the study_2 `odes/bird_dynamics.py` (body drag
`get_body_coeff`, and whether the tail drag enters the equations of motion).
Neither is modelled here.

## Kinematics (code frame, as run in study_2)

`Joint(offset, amplitude, phase)`, angles in degrees unless stated; the
frequency is 4 Hz. From `main_parallel.py`:

| Code joint | Value | Study_2 parameter (Table S1 name) |
|---|---|---|
| `shoulder.axis_x` | (0.2 rad, 0.014 rad, −90) | Shoulder y (11.5, 0.8, −90) |
| `shoulder.axis_y` | (**−ψs,z**, 14, 90) | Shoulder z: sweep offset ψs,z, amplitude 14 |
| `shoulder.axis_z` | (0, **As,x**, 180) | Shoulder x: wingbeat amplitude As,x |
| `elbow.axis_x` | (**qw,y**, 30, −90) | Wrist y: forearm profile rotation qw,y (tuned for level flight) |
| `elbow.axis_y` | (10, 10, −90) | Elbow z |
| `wrist.axis_y` | (−30, 30, 90) | Wrist z |
| `wrist.axis_z` | (0, 0, 0) | — |

Physical checks of this mapping (code vs paper's Fig. 2 definitions): the
offset −ψ gives a mean geometric arm sweep of about ψ + 1–2°; a positive
`elbow.axis_x` offset pitches the outer wing sections nose-up and raises lift.

## Code vs paper: differences that affect results

| Topic | Paper | Study_2 code (reproduced here with `study2=True`) |
|---|---|---|
| Tail inflow, pitch-rate term (Eq. 8) | U_t = U∞ + v_ind + q ê_y′∧(G−N): rotation velocity **subtracted**, at N | `U_tail = U + V_ind + ω×(tail origin − G)`: **added**, at the tail origin. Same as v1.1 |
| Tail inflow, wake filaments (Eq. 8) | Biot–Savart of the wing's trailing filaments | only 3 of 17 filaments (`range(len(line))`), at a wrong evaluation point. Same as v1.1 |
| Lift saturation | "slope 2π that saturates at ±15°" | **not implemented** (`circulation.py` linear, `polar.py` commented out) |
| Tail chord | Table S1: 0.25 m | `tail_length = 0.30` |
| Feathers | Table S1: 0.25, 0.275, 0.25, 0.225, 0.2, 0.175, 0.15 m | `Plumes.py`: 0.25, 0.225, 0.2, 0.175, 0.15, 0.125, 0.1 m |
| Profile drag (Eq. 7) | ½ρC_d,pro Σ c\|U_r\|² ds | component-wise square of the local velocity, z part added to F_z; C_D0 = 0.02 |
| Tail friction (Eq. 10) | area S_t (triangle, b·c/2) | b·c |
| Actuation power (Eq. 18) | Σ F·(−v_kin) | Σ F·(−(ω×r + v_kin)), profile drag excluded |
| Circulation tolerance | — | 0.005 (v1.1: 0.001) |
| Solver | — | M = 2, 90 steps per interval, tolerance **5e-4**, 25 iterations max |
| Level flight | \|W_ff\| < 5 mm/s by tuning qw,y | secant (`scipy.optimize.newton`) on `elbow.axis_x` offset; warm starts interpolated from earlier runs (`interpolation_amp.npy`, not recovered) |

Not reproduced here: body drag (code not recovered) and the power/CoT
post-processing.

## The tail pitch-rate sign

The wing uses `U − ω×(P − G)` (correct: a point moving with the body meets
air coming from where it moves) and the paper uses the same sign for the tail
(Eq. 8). The code adds the term for the tail. The velocity error is small
(< 0.5 % of the inflow), but it is the tail's whole dependence on q, so the
tail's pitch damping changes sign (`tail_sign_effect.py`, study_1 wing):

| Tail opening | Tail force along the cycle | d(q̇)/dq, wing alone | with tail, code | with tail, sign fixed |
|---|---|---|---|---|
| 20° | differs by ≤ 7.3 % | −0.140 1/s | +0.050 (amplifies) | −0.331 (damps) |
| 30° | differs by ≤ 7.3 % | −0.140 1/s | +0.299 (amplifies) | −0.580 (damps) |

Since the study_2 code contains this error, the published study_2 stability
results were computed with a tail that amplifies pitch rate. In the runs
below and in a 0–20° tail continuation (study_1 wing), correcting it always
lowered the multipliers: the paper's conclusion (opening the tail stabilises
flight) holds in direction; the location of the transition (β ≈ 25°) is
expected to move. Not yet checked: the full locus with qw,y re-trimmed.

## Results: Table 1 cases

`run_case.py CASE VARIANT`. Variants: `study2` = study_2 production code;
`study2_fixed` = same, with the tail inflow as in Eq. 8 (all filaments at N,
rotation term subtracted at N). qw,y is the published value (tuned for the
`study2` model), not re-trimmed. Initial guess (14, −1.5, 0.1, 0.01).

| Case | Variant | Iter. | u [m/s] | mean pitch [°] | W_ff [m/s] | \|Λ\| (largest first) | Published |
|---|---|---|---|---|---|---|---|
| (a) β 0°, ψ 10.5°, A 39.5°, qw,y 2.3° | `study2` | 6 | 13.02 | −0.17 | 0.678 | **1.3382**, 0.7586, 0.7586, 0.4145 | 14 m/s, Λ = 1.33 (unstable) |
| (b) β 40°, ψ 14.5°, A 42°, qw,y −5.5° | `study2` | 5 | **14.00** | 1.18 | 0.346 | **0.9694**, 0.9694, 0.6059, 0.6059 | 14 m/s, pitch ≈ −0.2°, \|Λ\| ≈ 0.96 (stable) |
| (b) | `study2_fixed` | 8 | 15.89 | −4.23 | −0.672 | 0.9564, 0.9564, 0.4040, 0.4040 | |
| (c) β 40°, ψ 13.5°, A 44°, qw,y −9.67° | `study2` | 4 | **14.00** | 3.22 | 0.378 | **0.9673**, 0.9673, 0.6122, 0.6122 | 14 m/s, pitch ≈ 1.3°, \|Λ\| ≈ 0.96 (stable) |
| (c) | `study2_fixed` | 10 | 18.17 | −8.79 | −2.367 | 0.9460, 0.9460, 0.3630, 0.3630 | |

All runs: tolerance 5e-4 (as study_2), commit `8f01643`, clean tree (provenance in each `results/*.json`).

The furled-tail case (a) gives Λ = 1.338 against the published 1.33 (at
13.0 m/s instead of 14). Both open-tail cases reproduce the published speed
(14.00 m/s) and are stable, with the largest multipliers within 0.01 of the
published ≈ 0.96. That pair, 0.955 ± 0.166j in case (b), rotates by
about 0.17 rad per wingbeat: an oscillation of about 9 s, the paper's
"phugoidal mode, with period of about 8 s". Not exactly level
(W_ff 0.35–0.68 m/s against < 5 mm/s) and, in (b) and (c), pitch 1.4–1.9°
higher than published:
most likely the missing body drag, with which qw,y was tuned. With the fixed
tail, the published qw,y no longer trims the bird (faster, nose down), so
those runs show the direction of the change, not a level-flight comparison.

## Files

| File | Purpose |
|---|---|
| `forces.py` | package lifting line plus the study_2 options (`study2`, `fix_filaments`, `fix_rotation`, `rotation_at_np`) |
| `model.py` | `Study2Bird`, the study_2 case builder, Table 1, variants |
| `run_case.py` | run a Table 1 case; writes `results/<case>_<variant>.json` and `.npz` (with provenance) |
| `check_equivalence.py` | `forces.py` with all options off is bitwise equal to the package |
| `tail_sign_effect.py` | size of the sign error: forces vs pitch damping |
| `results/` | outputs of the runs in the table above |

Reproduce (from the repository root):

```bash
uv run python studies/study2_tail/check_equivalence.py
uv run python studies/study2_tail/run_case.py b study2
uv run python studies/study2_tail/tail_sign_effect.py
```

Next steps (not done): recover `odes/bird_dynamics.py` (body drag); re-trim
qw,y for level flight in both variants; re-run the study_2 locus (Fig. 3b)
with the tail inflow fixed.
