#!/usr/bin/env python
"""Realism check of the bird kinematics and aerodynamics on a baseline limit cycle.

Evaluates the bird model (package ``stabilitytool_birdflight``, which must
reproduce the upstream baseline) along a converged limit cycle stored in ``baseline/data/<case>.npz`` and reports descriptors that can be
compared with bird-flight benchmarks: flight-path angle, body pitch, airspeed,
stroke amplitude, Strouhal number, wing flexion, downstroke fraction,
effective angle of attack and the split of weight support between downstroke
and upstroke. See the "Kinematics realism check" section of baseline/README.md.

No source file is edited. The only intervention is a wrapper around
``aerodynamics.lifting_line.solve_circulation`` that records the angle of attack
and circulation of the last lifting-line iteration (upstream computes them but
does not return them).

Usage (from the repository root)::

    python baseline/kinematics_check.py                 # bird_study1
    python baseline/kinematics_check.py --case bird_main --samples 40
    python baseline/kinematics_check.py --json out.json

Frames: the code's wing frame is x spanwise (right wing), y up, z backward.
Results are reported in the paper's body frame (study_1 Fig. 2): x' forward,
y' right, z' down.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]

# A_s,x (deg) of each bird baseline case; other joints as in main.py.
SHOULDER_AMPLITUDE = {"bird_study1": 42, "bird_a42_main_numerics": 42,
                      "bird_main": 44}
PERIOD, FREQUENCY, MASS, G = 0.25, 4.0, 1.2, 9.81
WINGFRAME_POSITION = np.array([0.0, 0.0, -0.05])  # upstream default, code frame


def build_bird(amplitude_deg):
    from stabilitytool_birdflight.flight.bird import BirdModel
    from stabilitytool_birdflight.kinematics.joints import Shoulder, Elbow, Wrist, Joint
    d = np.deg2rad
    shoulder = Shoulder(axis_x=Joint(0.2, 0.014, -np.pi / 2),
                        axis_y=Joint(-d(19), d(20), np.pi / 2),
                        axis_z=Joint(0, d(amplitude_deg), np.pi))
    elbow = Elbow(axis_x=Joint(0., np.pi / 6, -np.pi / 2),
                  axis_y=Joint(np.pi / 6, np.pi / 6, -np.pi / 2))
    wrist = Wrist(axis_y=Joint(-np.pi / 6, np.pi / 6, np.pi / 2),
                  axis_z=Joint(0., 0., 0.))
    return BirdModel(shoulder=shoulder, elbow=elbow, wrist=wrist)


def analyse(case, n_samples):
    try:
        import stabilitytool_birdflight  # noqa: F401
    except ImportError:  # not installed: use the source tree
        sys.path.insert(0, str(REPO / "src"))
    import stabilitytool_birdflight.aerodynamics.lifting_line as ff

    captured = {}
    original = ff.solve_circulation

    def recording_circulation(y, z, yc, zc, chord, aoa, cl_alpha, V, gamma):
        g, vs = original(y, z, yc, zc, chord, aoa, cl_alpha, V, gamma)
        captured.update(yc=np.array(yc), chord=np.array(chord),
                        aoa=np.array(aoa), V=np.array(V),
                        gamma=np.array(g).ravel())
        return g, vs

    ff.solve_circulation = recording_circulation
    bird = build_bird(SHOULDER_AMPLITUDE[case])

    data = np.load(REPO / "baseline" / "data" / f"{case}.npz")
    tt, xx = data["trajectory_t"], data["trajectory_x"]
    _, idx = np.unique(tt, return_index=True)  # drop duplicated interval ends
    tt, xx = tt[idx], xx[idx]
    ts = np.arange(n_samples) * PERIOD / n_samples
    X = np.array([np.interp(ts, tt, xx[:, k]) for k in range(4)]).T

    tip, wing_len, aeff_max, aeff_peak_loc, aeff_34, aoa_kin_max = ([] for _ in range(6))
    f_vert, f_hor = [], []
    for t, x in zip(ts, X):
        le, te = bird.wing_edges(bird.joint_angles(t))
        line = bird.quarter_chord_line(le, te)[0]
        p = line[:, np.argmax(line[0])]            # right lifting-line tip, code frame
        tip.append((-(p[2] + WINGFRAME_POSITION[2]), p[0], -p[1]))  # x' rel. to G, y', z'
        wing_len.append(np.linalg.norm(p))         # shoulder -> tip distance

        _, Fy, Fz, _, F_tail, *_ = bird.get_aeroforces(x, t)
        theta = x[3]
        Xb, Zb = -Fz, -Fy - F_tail                 # body-frame force (x' fwd, z' down)
        f_vert.append(Xb * np.sin(theta) - Zb * np.cos(theta))   # inertial, up
        f_hor.append(Xb * np.cos(theta) + Zb * np.sin(theta))    # inertial, forward

        right = captured["yc"] > 0
        yc = captured["yc"][right]
        # Effective AoA consistent with the solver: Gamma = 0.5 V c 2pi alpha_eff
        a_eff = (captured["gamma"] / (np.pi * captured["V"] * captured["chord"]))[right]
        k = np.argmax(np.abs(a_eff))
        aeff_max.append(np.rad2deg(abs(a_eff[k])))
        aeff_peak_loc.append(yc[k] / yc.max())
        aeff_34.append(np.rad2deg(a_eff[np.argmin(np.abs(yc - 0.75 * yc.max()))]))
        aoa_kin_max.append(np.rad2deg(np.max(np.abs(captured["aoa"][right]))))

    tip, wing_len = np.array(tip), np.array(wing_len)
    aeff_max, aeff_34 = np.array(aeff_max), np.array(aeff_34)
    f_vert, f_hor = np.array(f_vert), np.array(f_hor)
    u, w, q, theta = X.T
    airspeed = np.hypot(u, w)
    climb = u * np.sin(theta) - w * np.cos(theta)
    down = np.gradient(tip[:, 2], ts) > 0          # tip moving down (z' increasing)
    elevation = np.rad2deg(np.arctan2(-tip[:, 2], tip[:, 1]))
    tip_pp = tip[:, 2].max() - tip[:, 2].min()
    U = airspeed.mean()

    return dict(
        case=case,
        shoulder_amplitude_deg=SHOULDER_AMPLITUDE[case],
        samples_per_period=n_samples,
        airspeed_mean_m_s=U,
        u_mean_m_s=u.mean(), w_mean_m_s=w.mean(),
        pitch_mean_deg=np.rad2deg(theta.mean()),
        pitch_range_deg=[np.rad2deg(theta.min()), np.rad2deg(theta.max())],
        body_aoa_mean_deg=np.rad2deg(np.arctan2(w, u).mean()),
        climb_rate_mean_m_s=climb.mean(),
        flight_path_angle_deg=np.rad2deg(np.arcsin(climb.mean() / U)),
        tip_xprime_range_m=[tip[:, 0].min(), tip[:, 0].max()],
        tip_zprime_range_m=[tip[:, 2].min(), tip[:, 2].max()],
        stroke_amplitude_deg=elevation.max() - elevation.min(),
        tip_elevation_range_deg=[elevation.min(), elevation.max()],
        strouhal=FREQUENCY * tip_pp / U,
        reduced_frequency_pi_f_c_over_U=np.pi * FREQUENCY * 0.15 / U,
        max_span_m=2 * tip[:, 1].max(),
        wing_length_max_m=wing_len.max(), wing_length_min_m=wing_len.min(),
        wing_length_up_over_down=wing_len[~down].mean() / wing_len[down].mean(),
        t_over_T_max_wing_length=float(ts[np.argmax(wing_len)] / PERIOD),
        t_over_T_min_wing_length=float(ts[np.argmin(wing_len)] / PERIOD),
        downstroke_fraction=down.mean(),
        aoa_eff_peak_deg=aeff_max.max(),
        aoa_eff_peak_location_y_over_ymax=aeff_peak_loc[int(np.argmax(aeff_max))],
        aoa_eff_peak_t_over_T=float(ts[np.argmax(aeff_max)] / PERIOD),
        aoa_before_downwash_peak_deg=max(aoa_kin_max),
        aoa_eff_three_quarter_span_range_deg=[aeff_34.min(), aeff_34.max()],
        vertical_force_mean_N=f_vert.mean(), weight_N=MASS * G,
        vertical_force_downstroke_mean_N=f_vert[down].mean(),
        vertical_force_upstroke_mean_N=f_vert[~down].mean(),
        weight_support_fraction_downstroke=f_vert[down].sum() / f_vert.sum(),
        horizontal_force_mean_N=f_hor.mean(),
    )


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--case", default="bird_study1", choices=sorted(SHOULDER_AMPLITUDE))
    p.add_argument("--samples", type=int, default=40, help="samples per period")
    p.add_argument("--json", help="also write the results to this JSON file")
    args = p.parse_args(argv)
    json_path = Path(args.json).resolve() if args.json else None

    res = analyse(args.case, args.samples)
    width = max(len(k) for k in res)
    for k, v in res.items():
        if isinstance(v, float):
            v = f"{v:.4g}"
        elif isinstance(v, list):
            v = "[" + ", ".join(f"{e:.4g}" for e in v) + "]"
        print(f"{k:{width}s}  {v}")
    if json_path:
        clean = {k: (float(v) if isinstance(v, (np.floating, float)) else
                     [float(e) for e in v] if isinstance(v, list) else v)
                 for k, v in res.items()}
        json_path.write_text(json.dumps(clean, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
