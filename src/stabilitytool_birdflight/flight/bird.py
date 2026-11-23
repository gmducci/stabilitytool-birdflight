'''
file bird.py
@author Victor Colognesi, Gianmarco Ducci
@copyright Copyright © UCLouvain 2020
Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Stage 7: BirdModel holds a Wing (composition) instead of inheriting from it;
its parameters are constructor arguments.

multiflap is a Python tool for finding periodic orbits and assess their stability via the Floquet multipliers.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>

List of the contributors to the development of multiflap, Description and complete License: see LICENSE and NOTICE files.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import numpy as np

from ..aerodynamics.config import AerodynamicsConfig
from ..kinematics.wing import Wing
from .equations import longitudinal_rhs, stability_matrix
from .forces import aerodynamic_forces

__all__ = ["BirdModel"]


class BirdModel:
    """Longitudinal flight dynamics of a flapping bird, state x = [u, w, q, theta].

    Couples the wing kinematics (``wing``) with the lifting-line
    aerodynamics (``aerodynamics``) and the rigid-body equations
    (``equations.py``). Implements the ``dynamics.model.ODEModel`` protocol.
    Defaults reproduce upstream multiflap (study_1 reference bird).

    Parameters
    ----------
    wing : kinematics.wing.Wing, optional
        Gait and morphology of the wings (default: ``Wing()``).
    aerodynamics : aerodynamics.config.AerodynamicsConfig, optional
        Air properties and lifting-line settings (default: upstream values).
    mass : float
        Body mass [kg].
    g : float
        Gravitational acceleration [m/s^2].
    inertia_yy : float
        Pitch moment of inertia [kg m^2] (hard-coded 0.1 upstream).
    wing_position, tail_position : (3,) array_like
        Wing and tail frame origins relative to the centre of mass, in the
        wing frame (x spanwise, y up, z backward) [m].
    tail_length : float
        Tail length [m].
    tail_opening : float
        Tail opening angle [rad] (0: no tail surface).
    stability_fd_step : float
        Relative finite-difference step of ``jacobian``.

    All parameters are attributes read at call time: changing one changes
    the model.
    """

    dimension = 4

    def __init__(self, wing=None, aerodynamics=None, *, mass=1.2, g=9.81, inertia_yy=0.1,
                 wing_position=(0, -0.0, -0.05), tail_position=(0, -0., .3),
                 tail_length=0.25, tail_opening=0., stability_fd_step=1e-3):
        self.wing = wing if wing is not None else Wing()
        self.aerodynamics = aerodynamics if aerodynamics is not None else AerodynamicsConfig()
        self.mass = mass
        self.g = g
        self.inertia_yy = inertia_yy
        self.wing_position = np.array(wing_position, dtype=float)
        self.tail_position = np.array(tail_position, dtype=float)
        self.tail_length = tail_length
        self.tail_opening = tail_opening
        self.stability_fd_step = stability_fd_step

    def forces(self, x, t):
        """``AeroForces`` (wing and tail) for the state x at time t."""
        return aerodynamic_forces(self.wing, x, t, self.aerodynamics,
                                  wing_position=self.wing_position,
                                  tail_position=self.tail_position,
                                  tail_length=self.tail_length,
                                  tail_opening=self.tail_opening)

    def dynamics(self, x, t):
        """Time derivative of the state x = [u, w, q, theta] at time t."""
        return longitudinal_rhs(x, self.forces(x, t), self.mass, self.g, self.inertia_yy)

    def jacobian(self, x, t):
        """Finite-difference Jacobian of ``dynamics`` with respect to x."""
        return stability_matrix(x, t, self.forces, self.mass, self.g, self.inertia_yy,
                                self.stability_fd_step)

    get_stability_matrix = jacobian   # upstream name (model protocol alias)
