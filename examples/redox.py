"""Limit cycle of the redox oscillator (default parameters), unknown period.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``examples/redox_oscillator.py``.

Usage::

    python examples/redox.py [--figure redox.png]
"""
import argparse

import matplotlib.pyplot as plt

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle
from stabilitytool_birdflight.dynamics.systems.redox import RedoxModel


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", help="save the time series to this file")
    args = parser.parse_args()

    solver = SolverConfig(x0=(0.5, 0.5, 0.6, 0.2), method="unknown_period", points=2,
                          period_guess=23.0, t_steps=90000, integrator="odeint")
    result = find_limit_cycle(RedoxModel(), solver)
    print(result.summary())

    if args.figure:
        fig, ax = plt.subplots()
        for k, label in enumerate(["D1", "D2", "R", "A"]):
            ax.plot(result.trajectory_t, result.trajectory_x[:, k], label=label)
        ax.set_xlabel("time"); ax.legend()
        fig.savefig(args.figure, dpi=150)


if __name__ == "__main__":
    main()
