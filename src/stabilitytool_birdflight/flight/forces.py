"""Aerodynamic forces on the bird for a flight state: couples kinematics and aerodynamics.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Stage 7: moved out of upstream ``bird_dynamics.get_aeroforces``; arithmetic
unchanged.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
"""
import numpy as np

from ..aerodynamics.lifting_line import lifting_line_forces

__all__ = ["aerodynamic_forces"]


def aerodynamic_forces(wing, x, t, aerodynamics, *, wing_position, tail_position,
                       tail_length, tail_opening):
    """Wing and tail forces for the state x = [u, w, q, theta] at time t.

    Parameters
    ----------
    wing : kinematics.wing.Wing
        Provides the lifting-line geometry and its velocity at time t.
    x : (4,) array
        Flight state; the free stream is [0, w, u] and the angular velocity
        [q, 0, 0] (wing frame: x spanwise, y up, z backward).
    t : float
        Time [s].
    aerodynamics : aerodynamics.config.AerodynamicsConfig
        Air properties and lifting-line settings.
    wing_position, tail_position : (3,) arrays
        Wing and tail frame origins relative to the centre of mass [m].
    tail_length : float
        Tail length [m].
    tail_opening : float
        Tail opening angle [rad] (0: no tail surface).

    Returns
    -------
    aerodynamics.lifting_line.AeroForces
    """
    return lifting_line_forces(
        wing.geometry(t),
        np.array([0, x[1], x[0]]),          # free stream [0, w, u]
        np.array([x[2], 0, 0]),             # angular velocity [q, 0, 0]
        wing_position=wing_position,
        tail_position=tail_position,
        tail_length=tail_length,
        tail_opening=tail_opening,
        **aerodynamics.force_parameters())
