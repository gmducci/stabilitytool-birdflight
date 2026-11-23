"""Find a limit cycle and its Floquet multipliers: the entry point of ``dynamics``."""
from __future__ import annotations

import contextlib
import logging
import sys
import time

from .config import ConfigError, SolverConfig
from .result import LimitCycleResult
from .shooting import KnownPeriodShooting, UnknownPeriodShooting
from .solver import levenberg_marquardt

__all__ = ["find_limit_cycle", "make_shooting"]


def make_shooting(model, config: SolverConfig):
    """Multiple-shooting discretisation of ``model`` described by ``config``."""
    x0 = list(config.x0)
    if config.method == "known_period":
        if config.period is None:
            raise ConfigError("solver.period: required for known_period")
        return KnownPeriodShooting(model, x0, points=config.points, period=config.period,
                                   t_steps=config.t_steps, jacobian=config.jacobian)
    return UnknownPeriodShooting(model, x0, points=config.points,
                                 period_guess=config.period_guess,
                                 t_steps=config.t_steps, jacobian=config.jacobian,
                                 integrator=config.integrator)


def find_limit_cycle(model, config: SolverConfig, *, verbose=False, log_stream=None):
    """Find the limit cycle of ``model`` with the settings of ``config``.

    Parameters
    ----------
    model : ODEModel
        Model with ``dimension``, ``dynamics(x, t)`` and ``jacobian(x, t)``
        (see ``model.py``).
    config : SolverConfig
        Shooting and solver settings.
    verbose : bool
        Write the solver progress to standard output.
    log_stream : file-like, optional
        Write the solver progress (all levels) to this stream instead.

    Returns
    -------
    LimitCycleResult

    Raises
    ------
    solver.ConvergenceError
        If the solver does not converge within ``config.max_iterations``.
    """
    shooting = make_shooting(model, config)
    stream = log_stream if log_stream is not None else (sys.stdout if verbose else None)
    t0 = time.perf_counter()
    with _log_to(stream):
        output = levenberg_marquardt(shooting, tolerance=config.tolerance,
                                     max_iterations=config.max_iterations)
    return LimitCycleResult.from_solver_output(output, config.tolerance,
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
