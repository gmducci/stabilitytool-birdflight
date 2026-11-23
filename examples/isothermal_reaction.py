"""Limit cycle of an isothermal autocatalytic reaction (lambda = 11), unknown period.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``multiflap/main_isothermal.py``
(Copyright © UCLouvain 2020, Apache License 2.0). The model lives in
``examples/systems/isothermal_reaction.py``.

Usage::

    python examples/isothermal_reaction.py [--figure isothermal.png]
"""
import argparse

import matplotlib.pyplot as plt

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle, make_shooting
from systems.isothermal_reaction import IsothermalReaction   # examples/systems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", help="save a phase portrait to this file")
    args = parser.parse_args()

    model = IsothermalReaction(lam=11.)
    solver = SolverConfig(x0=(40., 20., 20.), method="unknown_period", points=20,
                          period_guess=0.5, t_steps=200, integrator="odeint")
    result = find_limit_cycle(model, solver)
    print(result.summary())

    if args.figure:
        guess = make_shooting(model, solver).initial_guess()
        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")
        x = result.trajectory_x
        ax.plot(x[:, 0], x[:, 1], x[:, 2], color="b", label="limit cycle")
        ax.scatter(*guess.T, color="r", label="initial guess")
        ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.set_zlabel("$z$")
        ax.legend()
        fig.savefig(args.figure, dpi=150)


if __name__ == "__main__":
    main()
