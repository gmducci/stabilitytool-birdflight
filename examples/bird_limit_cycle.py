"""Limit cycle and Floquet stability of the flapping bird (about 5 minutes).

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``multiflap/main.py`` (Gianmarco Ducci,
Copyright © UCLouvain 2020, Apache License 2.0).

The bird is built in Python here, to show the API: a ``Wing`` (kinematics)
inside a ``BirdModel`` (flight mechanics). The same case is
``examples/configs/bird_main.yaml``; for a run with provenance use::

    stabilitytool-birdflight run examples/configs/bird_main.yaml --output DIR

Usage::

    python examples/bird_limit_cycle.py [--output result.npz]
"""
import argparse

import numpy as np

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle
from stabilitytool_birdflight.flight.bird import BirdModel
from stabilitytool_birdflight.kinematics.joints import Elbow, Joint, Shoulder, Wrist
from stabilitytool_birdflight.kinematics.wing import Wing


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", help="save the result arrays to this .npz file")
    args = parser.parse_args()

    # Joint(offset, amplitude, phase) [rad]; the case of upstream main.py
    wing = Wing(shoulder=Shoulder(axis_x=Joint(0.2, 0.014, -np.pi/2),
                                  axis_y=Joint(-np.deg2rad(19), np.deg2rad(20), np.pi/2),
                                  axis_z=Joint(0, np.deg2rad(44), np.pi)),
                elbow=Elbow(axis_x=Joint(0., np.pi/6, -np.pi/2),
                            axis_y=Joint(np.pi/6, np.pi/6, -np.pi/2)),
                wrist=Wrist(axis_y=Joint(-np.pi/6, np.pi/6, np.pi/2),
                            axis_z=Joint(0., 0., 0.)),
                frequency=4)
    bird = BirdModel(wing, mass=1.2)

    # the motion is forced by the wing: the period is known (1/frequency)
    solver = SolverConfig(x0=(18., 0.5, 0.1, 0.01), method="known_period",
                          points=2, period=1/wing.frequency, t_steps=70)
    result = find_limit_cycle(bird, solver, verbose=True)
    print(result.summary())
    if args.output:
        np.savez(args.output, **result.to_arrays())


if __name__ == "__main__":
    main()
