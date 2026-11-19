"""Configuration of the aerodynamic model (lifting line and tail)."""
from __future__ import annotations

from dataclasses import dataclass

from ..configio import check_positive, from_dict, to_dict

__all__ = ["AerodynamicsConfig"]


@dataclass
class AerodynamicsConfig:
    """Air properties and lifting-line settings (defaults: upstream values).

    The geometry of the wing and tail is not here: it comes from
    ``kinematics`` (wing) and ``flight`` (tail and frame positions).
    """

    rho: float = 1.225
    cl_alpha: float = 6.283185307179586       # 2*pi [1/rad]
    kin_viscosity: float = 1.5e-5
    tail_reference_velocity: float = 15.0     # [m/s], tail Reynolds number
    circulation_tol: float = 0.001
    circulation_max_iterations: int = 50

    def __post_init__(self):
        check_positive("aerodynamics", rho=self.rho, cl_alpha=self.cl_alpha,
                       kin_viscosity=self.kin_viscosity,
                       tail_reference_velocity=self.tail_reference_velocity,
                       circulation_tol=self.circulation_tol,
                       circulation_max_iterations=self.circulation_max_iterations)

    @classmethod
    def from_dict(cls, data):
        return from_dict(cls, data, "aerodynamics")

    def to_dict(self):
        return to_dict(self)

    def force_parameters(self):
        """Keyword arguments of ``get_flappingforces`` set by this config."""
        return dict(rho=self.rho, cl_alpha=self.cl_alpha,
                    kin_viscosity=self.kin_viscosity,
                    tail_reference_velocity=self.tail_reference_velocity,
                    tol=self.circulation_tol,
                    max_iterations=self.circulation_max_iterations)
