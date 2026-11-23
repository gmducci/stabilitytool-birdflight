"""Model interface, SolverConfig and LimitCycleResult on the toy systems."""
from pathlib import Path

import numpy as np
import pytest

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.model import ODEModel, get_dimension, get_jacobian
from stabilitytool_birdflight.dynamics.result import LimitCycleResult
from stabilitytool_birdflight.dynamics.systems.van_der_pol import ForcedVanDerPol
from stabilitytool_birdflight.dynamics.systems.redox import RedoxModel
from stabilitytool_birdflight.dynamics.systems.rossler import Rossler
from stabilitytool_birdflight.flight.bird import BirdModel

DATA = Path(__file__).resolve().parents[1] / "baseline" / "data"

# (name, model, solver settings, relative tolerance; see baseline/compare_baseline.py)
TOY_CASES = [
    ("rossler", lambda: Rossler(a=0.2, b=0.2, c=5.7),
     dict(x0=[.1, 5., 3.6], method="unknown_period", points=30, period_guess=5.,
          t_steps=5000, integrator="odeint"), 1e-8),
    ("redox", RedoxModel,
     dict(x0=[0.5, 0.5, 0.6, 0.2], method="unknown_period", points=2,
          period_guess=23., t_steps=90000, integrator="odeint"), 1e-6),
    ("forced_vdp", lambda: ForcedVanDerPol(lam=1.8),
     dict(x0=[1., 1.], method="known_period", points=2, period=10.4719755,
          t_steps=4000, jacobian="numerical", tolerance=1e-6), 1e-8),
]


def rel(a, b):
    return np.max(np.abs(np.asarray(a) - np.asarray(b))) / np.max(np.abs(np.asarray(b)))


@pytest.mark.parametrize("name,model,settings,rtol", TOY_CASES, ids=[c[0] for c in TOY_CASES])
def test_toy_regression_through_solver_config(name, model, settings, rtol):
    res = SolverConfig(**settings).solve(model())
    ref = np.load(DATA / f"{name}.npz")
    assert isinstance(res, LimitCycleResult) and res.converged
    assert res.n_iterations == int(ref["n_iterations"])
    assert rel(res.points, ref["points"]) <= rtol
    assert rel(res.multipliers, ref["multipliers_sorted"]) <= rtol
    assert rel(res.monodromy, ref["monodromy"]) <= rtol
    assert abs(res.period - float(ref["period"])) <= rtol * float(ref["period"])
    assert "multipliers" in res.summary()


def test_floquet_exponents():
    res = SolverConfig(**TOY_CASES[0][2]).solve(TOY_CASES[0][1]())
    expected = np.log(res.multipliers.astype(complex)) / res.period
    assert np.allclose(res.floquet_exponents, expected)


@pytest.mark.parametrize("model", [Rossler(a=0.2, b=0.2, c=5.7), RedoxModel(),
                                   ForcedVanDerPol(), BirdModel()],
                         ids=["rossler", "redox", "vdp", "bird"])
def test_models_satisfy_protocol(model):
    assert isinstance(model, ODEModel)
    assert get_dimension(model) in (2, 3, 4)
    if not isinstance(model, ForcedVanDerPol):   # VdP: numerical Jacobian only
        assert callable(get_jacobian(model))


def test_model_without_jacobian_is_reported():
    class NoJac:
        dimension = 1

        def dynamics(self, x, t):
            return -x

    with pytest.raises(AttributeError, match="jacobian"):
        get_jacobian(NoJac())


def test_solver_config_validation():
    from stabilitytool_birdflight.configio import ConfigError
    with pytest.raises(ConfigError, match="period_guess"):
        SolverConfig(x0=[1.0], method="unknown_period")
    with pytest.raises(ConfigError, match="RK4"):
        SolverConfig(x0=[1.0], period=1.0, integrator="odeint")
