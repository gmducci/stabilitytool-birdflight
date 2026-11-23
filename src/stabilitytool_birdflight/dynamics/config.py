"""Configuration of the multiple-shooting limit-cycle solver."""
from __future__ import annotations

import contextlib
import logging
import sys
import time
from dataclasses import dataclass
from typing import Literal, Optional

from ..configio import ConfigError, check_finite, check_positive, from_dict, to_dict

__all__ = ["SolverConfig"]


@dataclass
class SolverConfig:
    """Multiple shooting + Levenberg–Marquardt settings.

    Parameters
    ----------
    x0 : list of float
        Initial guess for the first shooting point.
    method : "known_period" or "unknown_period"
        ``KnownPeriodShooting`` (fixed period, e.g. forced systems such as the
        bird) or ``UnknownPeriodShooting`` (period is an unknown).
    points : int
        Number of shooting points M (M - 1 intervals).
    period : float, optional
        Known period [s]; required for ``known_period`` unless the case sets
        it (the bird case uses 1/frequency).
    period_guess : float, optional
        Initial period guess; required for ``unknown_period``.
    t_steps : int
        Points per shooting interval (``t_steps - 1`` integration steps).
    integrator : "rk" or "odeint"
        Trajectory integrator for ``unknown_period`` (``known_period``
        always uses RK4).
    jacobian : "analytical" or "numerical"
        How the interval Jacobians are computed.
    tolerance : float
        Convergence threshold on max|E|.
    max_iterations : int
        Maximum number of solver iterations.
    """

    x0: tuple[float, ...]
    method: Literal["known_period", "unknown_period"] = "known_period"
    points: int = 2
    period: Optional[float] = None
    period_guess: Optional[float] = None
    t_steps: int = 70
    integrator: Literal["rk", "odeint"] = "rk"
    jacobian: Literal["analytical", "numerical"] = "analytical"
    tolerance: float = 1e-5
    max_iterations: int = 100

    def __post_init__(self):
        where = "solver"
        check_finite(where, x0=self.x0)
        if self.points < 2:
            raise ConfigError(f"{where}.points: at least 2 shooting points, got {self.points}")
        if self.t_steps < 2:
            raise ConfigError(f"{where}.t_steps: at least 2, got {self.t_steps}")
        check_positive(where, tolerance=self.tolerance,
                       max_iterations=self.max_iterations)
        if self.method == "known_period":
            if self.period_guess is not None:
                raise ConfigError(f"{where}.period_guess: only for method unknown_period")
            if self.integrator != "rk":
                raise ConfigError(f"{where}.integrator: known_period always uses RK4")
            if self.period is not None:
                check_positive(where, period=self.period)
        else:
            if self.period is not None:
                raise ConfigError(f"{where}.period: use period_guess with unknown_period")
            if self.period_guess is None:
                raise ConfigError(f"{where}.period_guess: required for unknown_period")
            check_positive(where, period_guess=self.period_guess)

    @classmethod
    def from_dict(cls, data):
        return from_dict(cls, data, "solver")

    def to_dict(self):
        return to_dict(self)

    def build(self, model):
        """Multiple-shooting discretisation of ``model`` described by this config."""
        from .shooting import KnownPeriodShooting, UnknownPeriodShooting
        x0 = list(self.x0)
        if self.method == "known_period":
            if self.period is None:
                raise ConfigError("solver.period: required for known_period")
            return KnownPeriodShooting(model, x0, points=self.points, period=self.period,
                                       t_steps=self.t_steps, jacobian=self.jacobian)
        return UnknownPeriodShooting(model, x0, points=self.points,
                                     period_guess=self.period_guess,
                                     t_steps=self.t_steps, jacobian=self.jacobian,
                                     integrator=self.integrator)

    def solve(self, model, verbose=False, log_stream=None):
        """Find the limit cycle of ``model``; returns a ``LimitCycleResult``.

        Solver progress (logger ``stabilitytool_birdflight``) is written to
        ``log_stream`` if given, or to standard output with ``verbose=True``.
        Raises ``solver.ConvergenceError`` if the solver does not converge.
        """
        from .result import LimitCycleResult
        from .solver import levenberg_marquardt
        shooting = self.build(model)
        stream = log_stream if log_stream is not None else (sys.stdout if verbose else None)
        t0 = time.perf_counter()
        with _log_to(stream):
            output = levenberg_marquardt(shooting, tolerance=self.tolerance,
                                         max_iterations=self.max_iterations)
        return LimitCycleResult.from_solver_output(output, self.tolerance,
                                                   time.perf_counter() - t0)


@contextlib.contextmanager
def _log_to(stream):
    """Send the package's log records (all levels) to ``stream`` meanwhile."""
    if stream is None:
        yield
        return
    logger = logging.getLogger("stabilitytool_birdflight")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
