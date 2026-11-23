"""Levenberg–Marquardt solver for the multiple-shooting system.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Merged in Stage 7 from upstream ``lma_solver.py`` (``Solver.lma``) and
``lma_solver_period.py`` (``SolverPeriod.lma``), which differed only in the
period unknown. The arithmetic is unchanged. Progress goes to ``logging``
(logger ``stabilitytool_birdflight.dynamics.solver``) instead of ``print``,
and a solve that does not converge raises ``ConvergenceError`` instead of
upstream's ``UnboundLocalError``.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
"""
from __future__ import annotations

import collections
import logging
import time

import numpy as np
from numpy import inf
from numpy.linalg import norm

__all__ = ["ConvergenceError", "ShootingSolution", "levenberg_marquardt"]

log = logging.getLogger(__name__)

#: Raw solver output: the fields of upstream ``lma()``'s tuple
#: ``(x, ptlist, error, complete_solution, jac_sg)``, plus the wall-clock
#: start time of each iteration and the end of the last one.
ShootingSolution = collections.namedtuple(
    "ShootingSolution",
    ["points", "points_history", "error_history", "trajectory", "monodromy",
     "iteration_start_times"])


class ConvergenceError(RuntimeError):
    """The solver reached ``max_iterations`` above the tolerance.

    Attributes ``error_history`` and ``points_history`` hold the iterations.
    """

    def __init__(self, message, error_history, points_history):
        super().__init__(message)
        self.error_history = error_history
        self.points_history = points_history


def levenberg_marquardt(shooting, tolerance=1e-5, max_iterations=100, damping=1.0):
    """Solve the multiple-shooting system of ``shooting``.

    Parameters
    ----------
    shooting : KnownPeriodShooting or UnknownPeriodShooting
        Discretised orbit (see ``shooting.py``).
    tolerance : float
        Convergence threshold on max|E|.
    max_iterations : int
        Maximum number of iterations.
    damping : float
        Initial Levenberg–Marquardt damping (divided by 10 after a step that
        lowers max|E|, multiplied by 10 otherwise).

    Returns
    -------
    ShootingSolution
        ``monodromy`` is the product of the interval Jacobians at the
        converged points.

    Raises
    ------
    ConvergenceError
        If max|E| is still above ``tolerance`` after ``max_iterations``.

    Notes
    -----
    As upstream, the shooting points are updated in place even when a step
    does not lower max|E| (only the damping and, for an unknown period, the
    period react to a rejected step).
    """
    period_is_unknown = shooting.period_is_unknown
    tau = shooting.initial_tau
    damp = damping
    x0 = shooting.initial_guess()
    x = 1*(x0)
    ptlist = [x0]
    error = []
    dim = shooting.dim
    iteration_start_times = []
    for i in range(max_iterations):
        iteration_start_times.append(time.perf_counter())
        start_timing = time.time()
        log.info("... Iteration i = %d", i)
        if period_is_unknown:
            log.debug("tau is: %s", tau)
        MS, E, complete_solution = shooting.scheme(x, tau)
        epsilon = max(np.abs(E))
        error.append(epsilon)
        log.info("... Iteration %d time: %s", i, time.time() - start_timing)
        log.info("... Iteration number i = %d has error: %s", i, norm(E, inf))

        if epsilon < tolerance:
            log.info("Iteration terminates at error : %s", norm(E, inf))
            log.info("Calculating Floquet Multipliers")
            ptlist.append(1*x)
            # monodromy matrix from the interval Jacobians (semigroup property)
            jac_sg = np.eye(dim)
            for k in range(0, shooting.points - 1):
                jac_sg = (MS[(k*dim):dim + (k*dim), (k*dim):(k*dim) + dim]).dot(jac_sg)
            iteration_start_times.append(time.perf_counter())
            return ShootingSolution(x, ptlist, error, complete_solution, jac_sg,
                                    iteration_start_times)

        # [(MS.T)MS + lambda*diag((MS.T)MS)]*delta_x = (MS.T)E
        A_0 = np.dot(MS.T, MS)
        A = A_0 + damp*np.diag(np.diag(A_0))
        B = np.dot(MS.T, E)
        delta_x = np.linalg.solve(A, B)
        for k in range(shooting.points):
            x[k, :] = x[k, :] + delta_x[k*dim:(k + 1)*dim]
        tau_new = tau + delta_x[-1] if period_is_unknown else tau
        [E_new, _] = shooting.error_vector(x, tau_new)
        if norm(E_new, inf) < norm(E, inf):
            tau = tau_new
            damp = damp/10.0
        else:
            damp = damp*10.0
        ptlist.append(1*x)

    last = f"error {error[-1]:.3e}, " if error else ""
    raise ConvergenceError(f"solver did not converge within {max_iterations} iterations "
                           f"({last}tolerance {tolerance:g})", error, ptlist)
