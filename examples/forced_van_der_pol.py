"""Forced Van der Pol oscillator: limit cycle with a known (forcing) period.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``examples/forced_van_der_pol.py``.

Usage::

    python examples/forced_van_der_pol.py [--figure vdp.png]
"""
import argparse

import matplotlib.pyplot as plt

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle
from stabilitytool_birdflight.dynamics.systems.van_der_pol import ForcedVanDerPol


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", help="save a phase portrait to this file")
    args = parser.parse_args()

    model = ForcedVanDerPol(lam=1.8)
    solver = SolverConfig(x0=(1.0, 1.0), method="known_period", points=2,
                          period=10.4719755, t_steps=4000, jacobian="numerical",
                          tolerance=1e-6)
    result = find_limit_cycle(model, solver)
    print(result.summary())

    if args.figure:
        fig, ax = plt.subplots()
        ax.plot(result.trajectory_x[:, 0], result.trajectory_x[:, 1])
        ax.scatter(*result.state_at_t0, color="r", label="state at t0")
        ax.set_xlabel("$x$"); ax.set_ylabel("$y$"); ax.legend()
        fig.savefig(args.figure, dpi=150)


if __name__ == "__main__":
    main()
