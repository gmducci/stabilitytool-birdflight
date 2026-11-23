"""Order of accuracy of the fixed-step Runge-Kutta integrators."""
import numpy as np
import pytest

from hopf import Hopf
from stabilitytool_birdflight.dynamics.integrators import rk2, rk3, rk4


@pytest.mark.parametrize("integrator,order", [(rk2, 2), (rk3, 3), (rk4, 4)],
                         ids=["rk2", "rk3", "rk4"])
def test_order_of_accuracy(integrator, order):
    model = Hopf(); x0 = np.array([0.7, 0.4, 0.3]); t_end = 2.0
    exact = model.flow(x0, t_end)
    errors = [np.max(np.abs(integrator(model.dynamics, x0, np.linspace(0, t_end, n + 1)).x[-1] - exact))
              for n in (20, 40, 80, 160)]
    observed = np.log2(np.array(errors[:-1]) / errors[1:])
    assert np.all(np.abs(observed - order) < 0.1), observed


def test_rk4_output_and_accuracy():
    model = Hopf(); x0 = np.array([0.7, 0.4, 0.3]); t = np.linspace(0, 2.0, 2001)
    sol = rk4(model.dynamics, x0, t)
    assert sol.x.shape == (t.size, 3) and sol.t is t
    assert np.array_equal(sol.x[0], x0)
    assert np.max(np.abs(sol.x[-1] - model.flow(x0, 2.0))) < 1e-12


def test_non_uniform_time_array():
    model = Hopf(); x0 = np.array([0.7, 0.4, 0.3])
    t = np.sort(np.r_[0, 2.0, np.random.default_rng(0).uniform(0, 2, 3000)])
    assert np.max(np.abs(rk4(model.dynamics, x0, t).x[-1] - model.flow(x0, 2.0))) < 1e-10
