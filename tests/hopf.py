"""Test system with an exactly known limit cycle, flow map and multipliers.

Hopf normal form plus a decoupled stable direction:

    x' = x - omega*y - x*(x^2 + y^2)
    y' = omega*x + y - y*(x^2 + y^2)
    z' = -lam*z

In polar coordinates r' = r(1 - r^2), theta' = omega, so the limit cycle is
the unit circle in z = 0 with period T = 2*pi/omega and Floquet multipliers
1 (along the cycle), exp(-2T) (radial) and exp(-lam*T) (z). The flow map has
a closed form, so interval Jacobians can be checked exactly.
"""
import numpy as np


class Hopf:
    dimension = 3

    def __init__(self, omega=1.0, lam=0.5):
        self.omega = omega
        self.lam = lam

    @property
    def period(self):
        return 2 * np.pi / self.omega

    @property
    def multipliers(self):
        """Exact Floquet multipliers, sorted by decreasing modulus."""
        T = self.period
        return np.array(sorted([1.0, np.exp(-2 * T), np.exp(-self.lam * T)], reverse=True))

    def dynamics(self, x, t):
        r2 = x[0] ** 2 + x[1] ** 2
        return np.array([x[0] - self.omega * x[1] - x[0] * r2,
                         self.omega * x[0] + x[1] - x[1] * r2,
                         -self.lam * x[2]])

    def jacobian(self, x, t):
        a, b = x[0], x[1]
        return np.array([[1 - 3 * a * a - b * b, -self.omega - 2 * a * b, 0.],
                         [self.omega - 2 * a * b, 1 - a * a - 3 * b * b, 0.],
                         [0., 0., -self.lam]])

    def flow(self, x, t):
        """Exact state at time t starting from x (autonomous system)."""
        r0 = np.hypot(x[0], x[1]); th0 = np.arctan2(x[1], x[0])
        r = 1 / np.sqrt(1 + (1 / r0 ** 2 - 1) * np.exp(-2 * t))
        th = th0 + self.omega * t
        return np.array([r * np.cos(th), r * np.sin(th), x[2] * np.exp(-self.lam * t)])

    def flow_jacobian(self, x, t, h=1e-6):
        """Jacobian of the exact flow map (central differences, error ~1e-10)."""
        J = np.zeros((3, 3))
        for j in range(3):
            e = np.zeros(3); e[j] = h
            J[:, j] = (self.flow(x + e, t) - self.flow(x - e, t)) / (2 * h)
        return J
