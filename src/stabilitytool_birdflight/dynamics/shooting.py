"""Multiple-shooting discretisation of a periodic orbit.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Merged in Stage 7 from upstream ``multiple_shooting.py`` (``MultipleShooting``,
known period) and ``multiple_shooting_period.py`` (``MultipleShootingPeriod``,
unknown period), which duplicated most of their code. The arithmetic is
unchanged; the values upstream hard-coded differently in the two classes are
now constructor arguments with the upstream defaults:

======================  ===================  =====================
argument                KnownPeriodShooting  UnknownPeriodShooting
======================  ===================  =====================
``variational_steps``   30                   500
``fd_epsilon``          1e-3                 1e-5
``integrator``          ``"rk"`` only        ``"rk"`` or ``"odeint"``
======================  ===================  =====================

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
"""
from __future__ import annotations

import collections
import logging
import time

import numpy as np
from scipy.integrate import odeint

from .integrators import rk2, rk4
from .model import get_dimension, get_jacobian

__all__ = ["KnownPeriodShooting", "UnknownPeriodShooting"]

log = logging.getLogger(__name__)

Trajectory = collections.namedtuple("Trajectory", ["space", "time"])
_OdeintSolution = collections.namedtuple("odesol", ["x", "t"])


class _MultipleShooting:
    """Common part of the known- and unknown-period schemes.

    The orbit is represented by ``points`` states x_0 ... x_{M-1}, spaced by
    tau = period / (M - 1) in time. Subclasses define whether the period is an
    unknown of the Newton/Levenberg–Marquardt system.
    """

    period_is_unknown = False

    def __init__(self, model, x0, points, t_steps, jacobian, integrator,
                 variational_steps, fd_epsilon):
        if jacobian not in ("analytical", "numerical"):
            raise ValueError(f"jacobian must be 'analytical' or 'numerical', got {jacobian!r}")
        if integrator not in ("rk", "odeint"):
            raise ValueError(f"integrator must be 'rk' or 'odeint', got {integrator!r}")
        self.model = model
        self.dim = get_dimension(model)
        self.x0 = x0
        self.points = points
        self.t_steps = t_steps
        self.jacobian = jacobian
        self.integrator = integrator
        self.variational_steps = variational_steps
        self.fd_epsilon = fd_epsilon

    # -- interface used by the solver ---------------------------------------
    @property
    def initial_tau(self):
        """Time between consecutive shooting points at the start."""
        raise NotImplementedError

    def mapped_point(self, x0, t0, deltat):
        """Integrate from ``x0`` at ``t0`` for ``deltat``.

        Returns the final state and the trajectory (``.x``, ``.t``), with
        ``t_steps`` points.
        """
        time_array = np.linspace(t0, t0 + deltat, self.t_steps)
        if self.integrator == "rk":
            trajectory = rk4(self.model.dynamics, x0, time_array)
            return trajectory.x[-1, :], trajectory
        solution = odeint(self.model.dynamics, x0, time_array)
        return solution[-1, :], _OdeintSolution(solution, time_array)

    def initial_guess(self):
        """Spread the M points by integrating from ``x0`` with the initial tau."""
        guessed = np.zeros([self.points, self.dim])
        guessed[0, 0:] = self.x0
        tau = self.initial_tau
        for i in range(1, self.points):
            [guessed[i, 0:], _] = self.mapped_point(guessed[i - 1, :], (i - 1)*tau, tau)
        return guessed

    def error_vector(self, x, tau):
        """Shooting residual E = -(f(x_i) - x_{i+1}), last block -(x_{M-1} - x_0).

        Returns ``E`` (length n*M) and the trajectory over the M - 1
        intervals (``Trajectory(space, time)``).
        """
        m, n = x.shape
        error = np.zeros(m*n)
        x_m = x[-1, :]
        x_0 = x[0, :]
        steps = self.t_steps
        full_trajectory = np.zeros([steps*(self.points - 1), n])
        times = np.zeros(steps*(self.points - 1))
        for j in range(0, m - 1):
            fx_start, trajectory = self.mapped_point(x[j, :], j*tau, tau)
            full_trajectory[j*steps:j*steps + steps, :] = trajectory.x[0:, :]
            times[j*steps:j*steps + steps] = trajectory.t
            error[n*j:n*(j + 1)] = -(fx_start - x[j + 1, :])
        error[-n:] = -(x_m - x_0)
        return error, Trajectory(full_trajectory, times)

    def scheme(self, x, tau):
        r"""Multiple-shooting matrix, residual and trajectory at ``x``, ``tau``.

        Solves MS * DX = E. With N the dimension and M the number of points::

                 [ J(x_0, tau)  -I                          (v_0) ]
                 [              J(x_1, tau)  -I             (v_1) ]
            MS = [                    ...                   (...) ]
                 [ -I  .......................  I           ( 0 ) ]

        J are the interval Jacobians (monodromy matrices of each interval).
        The last column (velocities v_i at the interval ends) exists only when
        the period is an unknown.
        """
        d, M = self.dim, self.points
        MS = np.zeros([d*M, d*M + (1 if self.period_is_unknown else 0)])
        for i in range(0, M - 1):
            x_start = x[i, :]
            if self.jacobian == "analytical":
                jacobian = self.interval_jacobian_analytical(x_start, i*tau, tau)
            else:
                jacobian = self.interval_jacobian_numerical(x_start, i*tau, tau)
            MS[(i*d):d + (i*d), (i*d) + d:2*d + (i*d)] = -np.eye(d)
            MS[(i*d):d + (i*d), (i*d):(i*d) + d] = jacobian
            if self.period_is_unknown:
                [mapped_point, trajectory] = self.mapped_point(x_start, i*tau, tau)
                MS[(i*d):d + (i*d), -1] = self.model.dynamics(mapped_point, trajectory.t[-1])
        MS[-d:, 0:d] = -np.eye(d)
        if self.period_is_unknown:
            MS[-d:, -d - 1:-1] = np.eye(d)
        else:
            MS[-d:, -d:] = np.eye(d)
        error, trajectory = self.error_vector(x, tau)
        log.debug("Error vector is %s", error)
        return MS, error, trajectory

    # -- interval Jacobians --------------------------------------------------
    def variational_rhs(self, state, t):
        r"""Right-hand side of the state plus the variational equations.

        ``state`` holds x (d) followed by J (d*d, row-major); returns
        (f(x, t), A(x, t) J), with A the model Jacobian (Seydel, Practical
        Bifurcation and Stability Analysis, Eq. 7.18).
        """
        d = self.dim
        x0 = state[0:d]
        J = state[d:].reshape((d, d))
        rhs = np.zeros(np.size(state))
        rhs[0:d] = self.model.dynamics(x0, t)
        rhs[d:] = np.reshape(np.dot(get_jacobian(self.model)(x0, t), J), d**2)
        return rhs

    def interval_jacobian_analytical(self, x0, initial_time, integration_time):
        """Jacobian of the flow over one interval, from the variational equations.

        Integrated on ``variational_steps`` points: RK2 with ``integrator="rk"``,
        ``odeint`` otherwise.
        """
        d = self.dim
        initial = np.zeros(d + d**2)
        initial[0:d] = x0
        initial[d:] = np.reshape(np.identity(d), d**2)
        t_array = np.linspace(initial_time, initial_time + integration_time,
                              self.variational_steps)
        if self.integrator == "rk":
            start = time.time()
            solution = rk2(self.variational_rhs, initial, t_array).x
            log.debug("Jacobian time %s", time.time() - start)
        else:
            solution = odeint(self.variational_rhs, initial, t_array)
        return solution[-1, d:].reshape((d, d))

    def interval_jacobian_numerical(self, x0, initial_time, integration_time):
        """Jacobian of the flow over one interval by forward finite differences.

        Each state is perturbed by ``x0[j] * fd_epsilon`` (so a zero component
        gives a division by zero, as upstream).
        """
        d = self.dim
        jacobian = np.zeros((d, d))
        log.debug("... Running jacobian Function")
        for j in range(d):
            perturbation = np.zeros(d)
            perturbation[j] = perturbation[j] + x0[j]*self.fd_epsilon
            x0_pert = x0 + perturbation
            [vel, _] = self.mapped_point(x0, initial_time, integration_time)
            [vel_pert, _] = self.mapped_point(x0_pert, initial_time, integration_time)
            for i in range(d):
                jacobian[i, j] = (vel_pert[i] - vel[i])/perturbation[j]
        log.debug("... jacobian Calculated")
        return jacobian


class KnownPeriodShooting(_MultipleShooting):
    """Multiple shooting with a known period (e.g. forced systems, the bird).

    Upstream ``MultipleShooting``. The trajectory always uses RK4 and the
    variational equations RK2.

    Parameters
    ----------
    model : ODEModel
        Model with ``dynamics(x, t)`` and ``jacobian(x, t)`` (see ``model.py``).
    x0 : array_like
        Initial guess of the first point.
    points : int
        Number of shooting points M.
    period : float
        Period of the orbit.
    t_steps : int
        Points per interval for the trajectory integration.
    jacobian : "analytical" or "numerical"
        How interval Jacobians are computed.
    variational_steps : int
        Points per interval for the variational equations (upstream 30).
    fd_epsilon : float
        Relative perturbation of the numerical Jacobian (upstream 1e-3).
    """

    def __init__(self, model, x0, points=2, period=0.25, t_steps=70,
                 jacobian="analytical", variational_steps=30, fd_epsilon=1e-3):
        super().__init__(model, x0, points, t_steps, jacobian, "rk",
                         variational_steps, fd_epsilon)
        self.period = period
        self.tau = self.period/(self.points - 1)

    @property
    def initial_tau(self):
        return self.tau


class UnknownPeriodShooting(_MultipleShooting):
    """Multiple shooting with the period as an extra unknown (autonomous systems).

    Upstream ``MultipleShootingPeriod``.

    Parameters
    ----------
    model, x0, points, t_steps, jacobian
        As in ``KnownPeriodShooting``.
    period_guess : float
        Initial guess of the period.
    integrator : "rk" or "odeint"
        RK4 (trajectory) and RK2 (variational equations), or ``odeint`` for both.
    variational_steps : int
        Points per interval for the variational equations (upstream 500).
    fd_epsilon : float
        Relative perturbation of the numerical Jacobian (upstream 1e-5).
    """

    period_is_unknown = True

    def __init__(self, model, x0, points=2, period_guess=None, t_steps=40,
                 jacobian="analytical", integrator="rk", variational_steps=500,
                 fd_epsilon=1e-5):
        super().__init__(model, x0, points, t_steps, jacobian, integrator,
                         variational_steps, fd_epsilon)
        self.period_guess = period_guess

    @property
    def initial_tau(self):
        return self.period_guess/(self.points - 1)
