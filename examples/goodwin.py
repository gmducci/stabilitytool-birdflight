"""Goodwin oscillator (circadian clock model): limit cycle and response to a pulse.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Rewritten in Stage 7 from upstream ``multiflap/goodwin_main.py``
(Copyright © UCLouvain 2020, Apache License 2.0). The model lives in
``examples/systems/goodwin.py``.

Usage::

    python examples/goodwin.py [--figure goodwin.png]
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import odeint

from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.limit_cycle import find_limit_cycle
from systems.goodwin import GoodwinModel   # examples/systems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", help="save the pulse response to this file")
    args = parser.parse_args()

    solver = SolverConfig(x0=(0.1, 1., 1.), method="unknown_period", points=40,
                          period_guess=23., t_steps=200, integrator="odeint",
                          jacobian="numerical")
    result = find_limit_cycle(GoodwinModel(), solver)
    print(result.summary())

    if args.figure:
        # rectangular pulse of amplitude 0.05 at t = 150, from the limit cycle
        t = np.linspace(0, 250, 90000)
        x0 = result.trajectory_x[-1]
        perturbed = odeint(GoodwinModel(perturbation=True).dynamics, x0, t)
        unperturbed = odeint(GoodwinModel(perturbation=False).dynamics, x0, t)
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True, figsize=(10, 8))
        ax1.plot(t, GoodwinModel().square(t, amp=0.05, t_0=150))
        ax1.set_ylabel("pulse")
        for k, name in enumerate("xyz"):
            ax2.plot(t, perturbed[:, k], label=name)
            ax3.plot(t, perturbed[:, k] - unperturbed[:, k], label=f"{name} pert - unpert")
        ax2.legend(); ax3.legend()
        ax3.set_xlabel("time (h)")
        fig.savefig(args.figure, dpi=150)


if __name__ == "__main__":
    main()
