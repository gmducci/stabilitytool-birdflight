"""Interface of the models the multiple-shooting solvers accept."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

__all__ = ["ODEModel", "get_jacobian", "get_dimension"]


@runtime_checkable
class ODEModel(Protocol):
    """A (possibly non-autonomous) ODE system dx/dt = f(x, t).

    Attributes and methods
    ----------------------
    dimension : int
        Number of state variables.
    dynamics(x, t) -> ndarray, shape (dimension,)
        Right-hand side f(x, t).
    jacobian(x, t) -> ndarray, shape (dimension, dimension)
        Stability matrix df/dx, needed for ``option_jacobian='analytical'``.
        Models written for upstream multiflap may call it
        ``get_stability_matrix`` instead; both names are accepted.
    """

    dimension: int

    def dynamics(self, x: np.ndarray, t: float) -> np.ndarray: ...


def get_jacobian(model):
    """The model's stability-matrix function (``jacobian`` or ``get_stability_matrix``)."""
    for name in ("jacobian", "get_stability_matrix"):
        fn = getattr(model, name, None)
        if callable(fn):
            return fn
    raise AttributeError(f"{type(model).__name__} defines neither jacobian(x, t) "
                         f"nor get_stability_matrix(x, t)")


def get_dimension(model):
    """The model's number of states (``dimension``; upstream bird: ``dimensions``)."""
    for name in ("dimension", "dimensions"):
        value = getattr(model, name, None)
        if value is not None:
            return int(value)
    raise AttributeError(f"{type(model).__name__} has no 'dimension' attribute")
