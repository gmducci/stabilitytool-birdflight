"""Periodic orbit of the Rössler system (a = b = 0.2, c = 5.7), unknown period.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``examples/rossler_system.py``. Expected:
period 5.881088559, multipliers -2.40395, ~1e-14, ~1 (Dednam & Botha 2015).

Usage::

    python examples/rossler.py [--figure rossler.png]
"""
import argparse

import matplotlib.pyplot as plt

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle
from stabilitytool_birdflight.dynamics.systems.rossler import Rossler


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", help="save a phase portrait to this file")
    args = parser.parse_args()

    model = Rossler(a=0.2, b=0.2, c=5.7)
    solver = SolverConfig(x0=(0.1, 5.0, 3.6), method="unknown_period", points=30,
                          period_guess=5.0, t_steps=5000, integrator="odeint")
    result = find_limit_cycle(model, solver)
    print(result.summary())

    if args.figure:
        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")
        x = result.trajectory_x
        ax.plot(x[:, 0], x[:, 1], x[:, 2], color="b", label="limit cycle")
        ax.scatter(*result.points.T, color="r", s=8, label="shooting points")
        ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_zlabel("$z$")
        ax.legend()
        fig.savefig(args.figure, dpi=150)


if __name__ == "__main__":
    main()
