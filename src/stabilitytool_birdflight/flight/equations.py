'''
file equations.py
Longitudinal equations of motion of a rigid body, state x = [u, w, q, theta]:
u, w velocity components (the free stream seen by the wing is [0, w, u] in the
wing frame: x spanwise, y up, z backward), q pitch rate, theta pitch angle.
@author Gianmarco Ducci
@copyright Copyright © UCLouvain 2020
Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Stage 7: the functions of upstream bird_dynamics.py (attached to BirdModel as
methods) became plain functions of the state, the forces and the body
parameters; the aerodynamic part moved to forces.py. Arithmetic unchanged.

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

__all__ = ["longitudinal_rhs", "stability_matrix"]


def longitudinal_rhs(x, forces, mass, g, inertia_yy):
    """Time derivative of x = [u, w, q, theta].

    ``forces`` is an ``aerodynamics.lifting_line.AeroForces`` evaluated at x.
    """
    u, w, q, theta = x
    Fy, Fz, My, F_tail = forces.fy, forces.fz, forces.my, forces.tail_fy
    dudt = -q*w - g*np.sin(theta) - Fz/mass
    dwdt = q*u + g*np.cos(theta) - Fy/mass - F_tail/mass
    dqdt = My/inertia_yy
    dthetadt = q
    return np.array([dudt, dwdt, dqdt, dthetadt], float)


def stability_matrix(x0, t, forces, mass, g, inertia_yy, perturbation):
    """Jacobian A[i, j] = d(x_dot[i])/d(x[j]) of ``longitudinal_rhs`` at x0.

    The force derivatives are forward finite differences with relative step
    ``perturbation`` in u, w and q (so a zero component gives a division by
    zero, as upstream); ``forces(x, t)`` returns ``AeroForces``.
    """
    m = mass
    Iyy = inertia_yy
    x0_u = x0 + [x0[0]*perturbation, 0, 0, 0]
    x0_w = x0 + [0, x0[1]*perturbation, 0, 0]
    x0_q = x0 + [0, 0, x0[2]*perturbation, 0]
    [_, Fy, Fz, My, F_tail, _, _, _, _] = forces(x0, t)
    [_, Fyu, Fzu, Myu, F_tailu, _, _, _, _] = forces(x0_u, t)
    [_, Fyw, Fzw, Myw, F_tailw, _, _, _, _] = forces(x0_w, t)
    [_, Fyq, Fzq, Myq, F_tailq, _, _, _, _] = forces(x0_q, t)

    dFzu_dU = (Fzu - Fz)/(x0[0]*perturbation)
    dFzw_dW = (Fzw - Fz)/(x0[1]*perturbation)
    dFzq_dq = (Fzq - Fz)/(x0[2]*perturbation)

    dFyu_dU = (Fyu - Fy)/(x0[0]*perturbation)
    dFyw_dW = (Fyw - Fy)/(x0[1]*perturbation)
    dFyq_dq = (Fyq - Fy)/(x0[2]*perturbation)

    dFytail_du = (F_tailu - F_tail)/(x0[0]*perturbation)
    dFytail_dw = (F_tailw - F_tail)/(x0[1]*perturbation)
    dFytail_dq = (F_tailq - F_tail)/(x0[2]*perturbation)

    dMy_du = (Myu - My)/(x0[0]*perturbation)
    dMy_dw = (Myw - My)/(x0[1]*perturbation)
    dMy_dq = (Myq - My)/(x0[2]*perturbation)
    u, w, q, theta = x0

    A = np.array([[-dFzu_dU/m, -q - dFzw_dW/m,
                   -w - dFzq_dq/m, -g*np.cos(theta)],
                  [q - dFyu_dU/m - dFytail_du/m, -dFyw_dW/m - dFytail_dw/m,
                   u - dFyq_dq/m - dFytail_dq/m, -g*np.sin(theta)],
                  [dMy_du/Iyy, dMy_dw/Iyy, dMy_dq/Iyy, 0],
                  [0, 0, 1, 0]], float)
    return A
