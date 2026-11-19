"""Configuration of the multiple-shooting limit-cycle solver."""
from __future__ import annotations

import contextlib
import io
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
        ``MultipleShooting`` (fixed period, e.g. forced systems such as the
        bird) or ``MultipleShootingPeriod`` (period is an unknown).
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
        """Multiple-shooting object and solver for ``model``."""
        from .multiple_shooting import MultipleShooting
        from .multiple_shooting_period import MultipleShootingPeriod
        from .lma_solver import Solver
        from .lma_solver_period import SolverPeriod
        x0 = list(self.x0)
        if self.method == "known_period":
            if self.period is None:
                raise ConfigError("solver.period: required for known_period")
            ms = MultipleShooting(x0, M=self.points, period=self.period,
                                  t_steps=self.t_steps, model=model,
                                  option_jacobian=self.jacobian)
            solver = Solver(tolerance=self.tolerance,
                            max_iterations=self.max_iterations, ms_obj=ms)
        else:
            ms = MultipleShootingPeriod(x0, M=self.points,
                                        period_guess=self.period_guess,
                                        t_steps=self.t_steps, model=model,
                                        option_jacobian=self.jacobian,
                                        integrator=self.integrator)
            solver = SolverPeriod(tolerance=self.tolerance,
                                  max_iterations=self.max_iterations, ms_obj=ms)
        return ms, solver

    def solve(self, model, verbose=False, log_stream=None):
        """Find the limit cycle of ``model``; returns a ``LimitCycleResult``.

        The upstream solvers print progress: written to ``log_stream`` if
        given, shown with ``verbose=True``, discarded otherwise.
        """
        import numpy as np
        from .result import LimitCycleResult
        _, solver = self.build(model)
        if log_stream is not None:
            stream = contextlib.redirect_stdout(log_stream)
        elif verbose:
            stream = contextlib.nullcontext()
        else:
            stream = contextlib.redirect_stdout(io.StringIO())
        t0 = time.perf_counter()
        try:
            with stream:
                output = solver.lma()
        except UnboundLocalError as exc:
            # upstream solvers leave jac_sg undefined when they do not converge
            raise RuntimeError(f"solver did not converge within {self.max_iterations} "
                               f"iterations") from exc
        return LimitCycleResult.from_solver_output(
            output, self.tolerance, time.perf_counter() - t0,
            iteration_times=np.diff(solver.iteration_start_times))
