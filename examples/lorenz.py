"""Lorenz system: an unstable periodic orbit and the largest Lyapunov exponent.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``examples/lorentz_system.py`` and
``multiflap/lorentz_main.py``.

* For r below the subcritical Hopf value (about 24.74), an unstable periodic
  orbit surrounds each non-trivial fixed point; multiple shooting finds it
  even though time integration cannot (multiplier with modulus > 1).
* At r = 28 the motion is chaotic: largest Lyapunov exponent about 0.9.

Usage::

    python examples/lorenz.py [--r 23] [--figure lorenz.png]
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle
from stabilitytool_birdflight.dynamics.lyapunov import largest_lyapunov_exponent
from stabilitytool_birdflight.dynamics.systems.lorenz import Lorenz


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--r", type=float, default=23.0,
                        help="Rayleigh number of the periodic orbit (below 24.74)")
    parser.add_argument("--figure", help="save the orbit to this file")
    args = parser.parse_args()

    model = Lorenz(sigma=10, r=args.r, b=8/3)
    fixed_point = np.array([np.sqrt(model.b*(model.r - 1)),
                            np.sqrt(model.b*(model.r - 1)), model.r - 1])
    solver = SolverConfig(x0=tuple(1.7*fixed_point), method="unknown_period", points=10,
                          period_guess=1.0, t_steps=500, tolerance=1e-8,
                          max_iterations=200)
    result = find_limit_cycle(model, solver)
    print(f"Unstable periodic orbit, r = {args.r}")
    print(result.summary())

    exponent = largest_lyapunov_exponent(Lorenz(sigma=10, r=28, b=8/3),
                                         [10., 10., 3.6], n=40, t_f=20.)
    print(f"Largest Lyapunov exponent at r = 28: {exponent:.3f}")

    if args.figure:
        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")
        x = result.trajectory_x
        ax.plot(x[:, 0], x[:, 1], x[:, 2], label=f"r = {args.r}")
        for sign in (1, -1):    # the two non-trivial fixed points
            ax.scatter(sign*fixed_point[0], sign*fixed_point[1], fixed_point[2], color="k")
        ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_zlabel("$z$")
        ax.legend()
        fig.savefig(args.figure, dpi=150)


if __name__ == "__main__":
    main()
