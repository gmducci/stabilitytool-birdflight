"""Study_2 bird: kinematics, settings and force options of the study_2 production code.

Sources (see README.md): the cluster script ``main_parallel.py`` (joints,
solver settings) and the study_2 ``aero_package`` (2021-09-29: tail length,
circulation tolerance, profile drag, tail friction). Where these differ from
the paper's supplementary Table S1, the code is followed, because the code
produced the published results.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.flight.bird import BirdModel
from stabilitytool_birdflight.flight.config import BirdCaseConfig
from stabilitytool_birdflight.kinematics.config import JointConfig

from forces import lifting_line_forces

REPO = Path(__file__).resolve().parents[2]

#: study_2 Table 1: tail opening beta, shoulder sweep offset psi_sz, wingbeat
#: amplitude A_sx, forearm rotation q_wy [deg], published largest |multiplier|.
TABLE1 = {
    "a": dict(beta=0.0, psi=10.5, amplitude=39.5, q_wy=2.3, published=1.33),
    "b": dict(beta=40.0, psi=14.5, amplitude=42.0, q_wy=-5.5, published=0.96),
    "c": dict(beta=40.0, psi=13.5, amplitude=44.0, q_wy=-9.67, published=0.96),
}

#: Tail inflow / force variants (keyword switches of ``forces.lifting_line_forces``).
VARIANTS = {
    "package": {},                                   # this package as released (no study_2 terms)
    "study2": dict(study2=True),                     # study_2 production code
    "study2_fixed": dict(study2=True, fix_filaments=True, fix_rotation=True,
                         rotation_at_np=True),       # study_2 code, tail inflow as in Eq. 8
}


class Study2Bird(BirdModel):
    """``BirdModel`` whose forces come from ``forces.lifting_line_forces`` with options."""

    def __init__(self, *args, force_options=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.force_options = dict(force_options or {})

    def forces(self, x, t):
        return lifting_line_forces(
            self.wing.geometry(t),
            np.array([0, x[1], x[0]]),          # free stream [0, w, u]
            np.array([x[2], 0, 0]),             # angular velocity [q, 0, 0]
            wing_position=self.wing_position,
            tail_position=self.tail_position,
            tail_length=self.tail_length,
            tail_opening=self.tail_opening,
            **self.aerodynamics.force_parameters(),
            **self.force_options)


def study2_case(beta, psi, amplitude, q_wy, x0=(14.0, -1.5, 0.1, 0.01)):
    """Case config with the study_2 production kinematics and settings.

    Joints in the code frame, exactly as in ``main_parallel.py``: shoulder x
    (0.2 rad, 0.014 rad, -90), shoulder y (-psi, 14, 90), shoulder z
    (0, A_sx, 180), elbow x (q_wy, 30, -90), elbow y (10, 10, -90),
    wrist y (-30, 30, 90). Feathers, bones and the rest of the wing: the
    package defaults, identical to the study_2 ``aero_package``.
    """
    case = BirdCaseConfig.load(REPO / "examples" / "configs" / "bird_a42_main_numerics.yaml")
    k = case.kinematics
    k.shoulder_y = JointConfig(-psi, 14, 90)
    k.shoulder_z = JointConfig(0, amplitude, 180)
    k.elbow_x = JointConfig(q_wy, 30, -90)
    k.elbow_y = JointConfig(10, 10, -90)
    k.wrist_y = JointConfig(-30, 30, 90)
    case.flight.tail.opening = beta
    case.flight.tail.length = 0.30             # study_2 settings.py (Table S1 says 0.25)
    case.aerodynamics.circulation_tol = 0.005  # study_2 flapping_forces.py
    case.solver = SolverConfig(x0=tuple(x0), method="known_period", points=2,
                               period=1/k.frequency, t_steps=90, tolerance=5e-4,
                               max_iterations=40)   # main_parallel.py (it used 25)
    return case


def build_bird(case, variant):
    """``Study2Bird`` for a case config and a variant name of ``VARIANTS``."""
    k, a, f = case.kinematics, case.aerodynamics, case.flight
    return Study2Bird(k.build(), a, mass=f.mass, g=f.g, inertia_yy=f.inertia_yy,
                      wing_position=f.wing_position, tail_position=f.tail.position,
                      tail_length=f.tail.length, tail_opening=np.deg2rad(f.tail.opening),
                      stability_fd_step=f.stability_fd_step,
                      force_options=VARIANTS[variant])
