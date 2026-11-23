"""Largest Lyapunov exponent by renormalised trajectory separation.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Stage 7: the upstream class ``LyapunovExponents(x0, n, t_f, ms_object)`` with
method ``get_lyapunov_exponent()`` became the function below. The values
upstream hard-coded (transient, perturbation size, integration points) are
keyword arguments with the upstream defaults; the arithmetic is unchanged.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
"""
import numpy as np
from scipy.integrate import odeint

__all__ = ["largest_lyapunov_exponent"]


def largest_lyapunov_exponent(model, x0, n, t_f, *, transient_time=200.,
                              transient_steps=1000, relative_perturbation=1e-9,
                              steps_per_segment=5000):
    """Estimate the largest Lyapunov exponent of ``model``.

    The state is first integrated for ``transient_time`` to reach the
    attractor. A perturbed copy is then followed over ``n`` segments of
    length ``t_f / n``; after each segment the separation is rescaled to its
    initial size, and the exponent is the mean logarithmic growth rate.

    Parameters
    ----------
    model : ODEModel
        Model with ``dynamics(x, t)``, integrated with ``scipy.integrate.odeint``.
    x0 : array_like
        Initial condition.
    n : int
        Number of renormalisation segments.
    t_f : float
        Total integration time after the transient.
    transient_time : float
        Length of the discarded transient (upstream 200).
    transient_steps : int
        Output points of the transient integration (upstream 1000).
    relative_perturbation : float
        Initial separation, relative to the state (upstream 1e-9).
    steps_per_segment : int
        Output points of each segment integration (upstream 5000).

    Returns
    -------
    float
        Largest Lyapunov exponent [1/time unit].
    """
    delta_time = t_f/n
    time_array = np.linspace(0, transient_time, transient_steps)
    x = odeint(model.dynamics, x0, time_array)
    x = x[-1, :]
    d = x*relative_perturbation
    x_pert = x + d
    norm_d = np.linalg.norm(d)
    lambda_local = np.zeros(n)
    for i in range(n):
        t0 = i*delta_time
        time_array = np.linspace(t0, t0 + delta_time, steps_per_segment)
        fx = odeint(model.dynamics, x, time_array)[-1, :]
        fx_pert = odeint(model.dynamics, x_pert, time_array)[-1, :]
        d_j = fx_pert - fx
        norm_d_j = np.linalg.norm(d_j)
        lambda_local[i] = np.log(norm_d_j/norm_d)
        x = fx
        x_pert = x + (d_j*(norm_d/norm_d_j))
    return np.sum(lambda_local)/(n*delta_time)
