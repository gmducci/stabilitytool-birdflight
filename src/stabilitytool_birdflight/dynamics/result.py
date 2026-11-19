"""Structured result of a limit-cycle computation."""
from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

__all__ = ["LimitCycleResult", "sort_multipliers"]


def sort_multipliers(multipliers, eigenvectors):
    """Sort by descending modulus; complex pairs by descending imaginary part."""
    w = np.asarray(multipliers)
    order = sorted(range(len(w)), key=lambda k: (-abs(w[k]), -w[k].imag))
    return w[order], np.asarray(eigenvectors)[:, order]


@dataclass
class LimitCycleResult:
    """Limit cycle found by multiple shooting, with its Floquet analysis.

    Attributes
    ----------
    points : ndarray (M, n)
        Converged multiple-shooting points.
    period : float
        Period of the limit cycle (last time of ``trajectory_t``).
    trajectory_t, trajectory_x : ndarray
        Limit-cycle trajectory over one period, ``(N,)`` and ``(N, n)``.
        Interval ends appear twice (end of one interval, start of the next).
    monodromy : ndarray (n, n)
        Monodromy matrix.
    multipliers : ndarray (n,)
        Floquet multipliers, sorted by descending modulus (complex pairs by
        descending imaginary part).
    eigenvectors : ndarray (n, n)
        Corresponding eigenvectors (columns), same order.
    n_iterations : int
        Number of Levenberg–Marquardt updates.
    error_history : ndarray
        max|E| of the shooting residual at each evaluation.
    points_history : ndarray (k, M, n)
        Multiple-shooting points along the iterations.
    converged : bool
        Final residual below the solver tolerance.
    elapsed_s : float
        Wall time of the solve [s].
    """

    points: np.ndarray
    period: float
    trajectory_t: np.ndarray
    trajectory_x: np.ndarray
    monodromy: np.ndarray
    multipliers: np.ndarray
    eigenvectors: np.ndarray
    n_iterations: int
    error_history: np.ndarray
    points_history: np.ndarray
    converged: bool
    elapsed_s: float

    @property
    def final_error(self):
        return float(self.error_history[-1])

    @property
    def state_at_t0(self):
        return self.points[0]

    @property
    def floquet_exponents(self):
        """ln(multipliers) / period (complex)."""
        return np.log(self.multipliers.astype(complex)) / self.period

    @classmethod
    def from_solver_output(cls, output, tolerance, elapsed_s=float("nan")):
        """Build from the tuple of ``Solver.lma()`` / ``SolverPeriod.lma()``."""
        x, ptlist, error, complete_solution, jac_sg = output
        eigvals, eigvecs = np.linalg.eig(jac_sg)
        multipliers, eigenvectors = sort_multipliers(eigvals, eigvecs)
        t = np.asarray(complete_solution.time, float)
        return cls(
            points=np.asarray(x, float),
            period=float(t[-1]),
            trajectory_t=t,
            trajectory_x=np.asarray(complete_solution.space, float),
            monodromy=np.asarray(jac_sg, float),
            multipliers=multipliers,
            eigenvectors=eigenvectors,
            n_iterations=len(error) - 1,
            error_history=np.asarray(error, float),
            points_history=np.asarray([np.asarray(p, float) for p in ptlist]),
            converged=bool(error[-1] < tolerance),
            elapsed_s=float(elapsed_s),
        )

    def to_arrays(self):
        """Dictionary of arrays (for ``np.savez``)."""
        out = {f.name: np.asarray(getattr(self, f.name)) for f in fields(self)}
        out["final_error"] = np.float64(self.final_error)
        return out

    def summary(self):
        """Short readable summary."""
        lines = [f"period        {self.period:.10g}",
                 f"iterations    {self.n_iterations} (final error {self.final_error:.3e}, "
                 f"{'converged' if self.converged else 'NOT converged'})",
                 f"state at t0   {np.array2string(self.state_at_t0, precision=6)}",
                 "multipliers   " + ", ".join(
                     f"{m.real:.6g}{m.imag:+.6g}j  |{abs(m):.6g}|" for m in self.multipliers)]
        return "\n".join(lines)
