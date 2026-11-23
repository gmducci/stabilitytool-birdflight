"""Largest Lyapunov exponent of the Lorenz system (sigma=10, r=28, b=8/3).

Reference value recorded with the upstream ``LyapunovExponents`` class
before Stage 7 (same settings); the literature value is about 0.906.
"""
import numpy as np

from stabilitytool_birdflight.dynamics.lyapunov import largest_lyapunov_exponent
from stabilitytool_birdflight.dynamics.systems.lorenz import Lorenz

UPSTREAM_VALUE = 0.9552359970272992   # x0=[10, 10, 3.6], n=40, t_f=20


def test_lorenz_matches_upstream():
    value = largest_lyapunov_exponent(Lorenz(sigma=10, r=28, b=8/3), [10., 10., 3.6], 40, 20.)
    assert np.isclose(value, UPSTREAM_VALUE, rtol=1e-8, atol=0)
