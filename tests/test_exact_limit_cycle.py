"""Solvers and interval Jacobians on a limit cycle known in closed form.

See ``hopf.py``: period 2*pi, multipliers 1, exp(-lam*T), exp(-2T).

The tolerances record the accuracy of the upstream algorithms as they are
(no numerical change in Stage 6); comments give the measured values. The
known-period analytical monodromy (RK2 with a fixed 30 points per shooting
interval, used by the bird model) is the least accurate part: its error
on the unit multiplier is about 3e-3 with 4 shooting points.
"""
import numpy as np
import pytest

from hopf import Hopf
from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.shooting import KnownPeriodShooting, UnknownPeriodShooting
from stabilitytool_birdflight.dynamics.solver import ConvergenceError

X0 = [0.6, 0.3, 0.4]          # off the cycle
STATE = np.array([0.7, 0.4, 0.3])
TAU = 2.0


def rel(a, b):
    return np.max(np.abs(np.asarray(a) - b)) / np.max(np.abs(b))


def check_cycle(res, model, tol):
    radius = np.hypot(res.trajectory_x[:, 0], res.trajectory_x[:, 1])
    assert res.converged
    assert np.max(np.abs(radius - 1)) < tol
    assert np.max(np.abs(res.trajectory_x[:, 2])) < tol
    assert np.allclose(np.hypot(res.points[:, 0], res.points[:, 1]), 1, atol=tol)


# --- interval Jacobians against the exact flow map -------------------------------

@pytest.mark.parametrize("integrator,tol", [("rk", 3e-5), ("odeint", 1e-7)])   # measured 8.3e-6, 1.5e-8
def test_interval_jacobian_unknown_period(integrator, tol):
    model = Hopf()
    ms = UnknownPeriodShooting(model, list(STATE), points=2, period_guess=TAU,
                               t_steps=200, integrator=integrator)
    exact = model.flow_jacobian(STATE, TAU)
    assert rel(ms.interval_jacobian_analytical(STATE, 0., TAU), exact) < tol
    assert rel(ms.interval_jacobian_numerical(STATE, 0., TAU), exact) < 2e-5   # 5.3e-6


def test_interval_jacobian_known_period():
    model = Hopf()
    ms = KnownPeriodShooting(model, list(STATE), points=2, period=TAU, t_steps=200)
    exact = model.flow_jacobian(STATE, TAU)
    assert rel(ms.interval_jacobian_analytical(STATE, 0., TAU), exact) < 1e-2   # 2.5e-3 (RK2, 30 points)
    assert rel(ms.interval_jacobian_numerical(STATE, 0., TAU), exact) < 2e-3    # 5.3e-4 (epsilon 1e-3)


def test_known_period_monodromy_converges_with_finer_intervals():
    """The RK2 monodromy error shrinks with shorter shooting intervals.

    (With M = 2 the solver stalls near max|E| = 1e-7: the inaccurate
    interval Jacobian degrades the Newton steps.)
    """
    model = Hopf(); errors = []
    for M in (4, 8, 16):
        res = SolverConfig(x0=X0, method="known_period", period=model.period, points=M,
                           t_steps=200, tolerance=1e-9).solve(model)
        errors.append(abs(res.multipliers[0] - 1))
    assert all(a > b for a, b in zip(errors, errors[1:])), errors   # 2.7e-3, 9.5e-4, 3.0e-4


@pytest.mark.filterwarnings("ignore:invalid value encountered:RuntimeWarning")
@pytest.mark.xfail(strict=True, reason="upstream numerical Jacobians perturb x[j] by x[j]*epsilon: "
                                       "zero step (NaN) when a coordinate is exactly zero")
@pytest.mark.parametrize("cls", ["known", "unknown"])
def test_numerical_jacobian_with_zero_coordinate(cls):
    model = Hopf(); x = np.array([1.0, 0.0, 0.0])
    ms = (KnownPeriodShooting(model, list(x), points=2, period=TAU, t_steps=200) if cls == "known"
          else UnknownPeriodShooting(model, list(x), points=2, period_guess=TAU, t_steps=200))
    assert np.all(np.isfinite(ms.interval_jacobian_numerical(x, 0., TAU)))


# --- full solves -----------------------------------------------------------------

@pytest.mark.parametrize("integrator,unit_tol", [("rk", 5e-5), ("odeint", 1e-7)])   # 8.7e-6, 5e-9
def test_unknown_period_solver(integrator, unit_tol):
    model = Hopf()
    res = SolverConfig(x0=X0, method="unknown_period", points=4, period_guess=6.0,
                       t_steps=200, integrator=integrator, tolerance=1e-9).solve(model)
    check_cycle(res, model, 1e-7)
    assert abs(res.period - model.period) < 1e-6 * model.period
    exact = model.multipliers
    assert abs(res.multipliers[0] - 1) < unit_tol
    assert abs(res.multipliers[1] - exact[1]) < 1e-4 * exact[1]
    assert abs(res.multipliers[2] - exact[2]) < 1e-3 * exact[2]
    assert np.allclose(np.abs(res.floquet_exponents[1:].real), [0.5, 2.0], rtol=1e-3)


def test_unknown_period_solver_other_frequency():
    model = Hopf(omega=2.0, lam=1.0)
    res = SolverConfig(x0=X0, method="unknown_period", points=4, period_guess=3.3,
                       t_steps=200, integrator="odeint", tolerance=1e-9).solve(model)
    assert abs(res.period - np.pi) < 1e-6
    assert np.allclose(res.multipliers, model.multipliers, rtol=1e-3, atol=1e-7)


@pytest.mark.parametrize("jacobian,unit_tol", [("analytical", 1e-2), ("numerical", 3e-3)])  # 2.7e-3, 7.4e-4
def test_known_period_solver(jacobian, unit_tol):
    model = Hopf()
    res = SolverConfig(x0=X0, method="known_period", period=model.period, points=4,
                       t_steps=200, jacobian=jacobian, tolerance=1e-9).solve(model)
    check_cycle(res, model, 1e-7)
    assert res.period == model.period
    assert abs(res.multipliers[0] - 1) < unit_tol
    assert abs(res.multipliers[1] - model.multipliers[1]) < 1e-3   # 3.0e-5
    # the radial multiplier exp(-4*pi) = 3.5e-6 is below the accuracy of these monodromies
    assert abs(res.multipliers[2]) < 1e-4


def test_solver_reports_non_convergence():
    with pytest.raises(ConvergenceError, match="did not converge"):
        SolverConfig(x0=X0, method="unknown_period", points=4, period_guess=6.0,
                     t_steps=200, integrator="odeint", tolerance=1e-14,
                     max_iterations=2).solve(Hopf())
