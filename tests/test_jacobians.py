"""Analytical Jacobians of the vector fields against central differences."""
import numpy as np
import pytest

from hopf import Hopf
from stabilitytool_birdflight.dynamics.model import get_jacobian
from stabilitytool_birdflight.dynamics.systems.goodwin_model import GoodwinModel
from stabilitytool_birdflight.dynamics.systems.isothermal_reaction import IsothermalReaction
from stabilitytool_birdflight.dynamics.systems.lorentz import Lorentz
from stabilitytool_birdflight.dynamics.systems.redox_oscillation import RedoxModel
from stabilitytool_birdflight.dynamics.systems.rossler import Rossler
from stabilitytool_birdflight.dynamics.systems.torus import Torus


def central_difference(f, x, t, h=1e-6):
    n = len(x)
    J = np.zeros((n, n))
    for j in range(n):
        e = np.zeros(n); e[j] = h * max(1.0, abs(x[j]))
        J[:, j] = (f(x + e, t) - f(x - e, t)) / (2 * e[j])
    return J


MODELS = {
    "rossler": lambda: Rossler(a=0.2, b=0.2, c=5.7),
    "lorenz": lambda: Lorentz(sigma=10, r=28, b=8 / 3),
    "redox": RedoxModel,
    "goodwin": GoodwinModel,
    "isothermal": IsothermalReaction,
    "hopf": Hopf,
}


@pytest.mark.parametrize("name", MODELS)
def test_analytical_jacobian(name):
    model = MODELS[name]()
    jac = get_jacobian(model)
    rng = np.random.default_rng(1)
    for _ in range(10):
        # positive states: Goodwin has z**n terms
        x = rng.uniform(0.1, 1.5, model.dimension); t = rng.uniform(0, 10)
        J = jac(x, t)
        N = central_difference(model.dynamics, x, t)
        assert J.shape == (model.dimension, model.dimension)
        assert np.max(np.abs(J - N)) <= 1e-7 * np.max(np.abs(N)), x


@pytest.mark.xfail(strict=True, reason="upstream Torus.get_stability_matrix is unfinished and "
                                       "returns None (to be fixed or removed in Stage 7)")
def test_torus_jacobian():
    model = Torus(); x = np.array([0.3, 0.4, 0.5])
    assert np.allclose(model.get_stability_matrix(x, 0.0), central_difference(model.dynamics, x, 0.0))
