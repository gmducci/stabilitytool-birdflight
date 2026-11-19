"""Configuration of a bird flight case: kinematics + aerodynamics + flight + solver.

A case is fully specified by one YAML (or JSON) file with four sections::

    kinematics:   {...}   # kinematics.config.WingConfig (angles in degrees)
    aerodynamics: {...}   # aerodynamics.config.AerodynamicsConfig
    flight:       {...}   # FlightConfig below
    solver:       {...}   # dynamics.config.SolverConfig

Example::

    case = BirdCaseConfig.load("examples/configs/bird_study1_reference.yaml")
    result = case.solve()            # LimitCycleResult
    print(result.summary())
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..aerodynamics.config import AerodynamicsConfig
from ..configio import (ConfigError, check_finite, check_positive, from_dict,
                        load_file, save_file, to_dict)
from ..dynamics.config import SolverConfig
from ..kinematics.config import WingConfig

__all__ = ["TailConfig", "FlightConfig", "BirdCaseConfig"]


@dataclass
class TailConfig:
    """Tail geometry. ``opening`` in degrees (0: no tail surface)."""

    length: float = 0.25
    opening: float = 0.0
    position: tuple[float, float, float] = (0.0, -0.0, 0.3)

    def __post_init__(self):
        check_positive("flight.tail", length=self.length)
        check_finite("flight.tail", opening=self.opening, position=self.position)
        if not 0.0 <= self.opening < 180.0:
            raise ConfigError(f"flight.tail.opening: must be in [0, 180) degrees, "
                              f"got {self.opening}")


@dataclass
class FlightConfig:
    """Body and flight-mechanics parameters (defaults: upstream values).

    Positions are relative to the centre of mass, in the wing frame
    (x spanwise, y up, z backward), in metres.
    """

    mass: float = 1.2
    g: float = 9.81
    inertia_yy: float = 0.1
    wing_position: tuple[float, float, float] = (0.0, -0.0, -0.05)
    tail: TailConfig = field(default_factory=TailConfig)
    stability_fd_step: float = 1e-3

    def __post_init__(self):
        check_positive("flight", mass=self.mass, g=self.g, inertia_yy=self.inertia_yy,
                       stability_fd_step=self.stability_fd_step)
        check_finite("flight", wing_position=self.wing_position)


@dataclass
class BirdCaseConfig:
    """A complete bird flight case."""

    kinematics: WingConfig
    solver: SolverConfig
    aerodynamics: AerodynamicsConfig = field(default_factory=AerodynamicsConfig)
    flight: FlightConfig = field(default_factory=FlightConfig)

    def __post_init__(self):
        if self.solver.method != "known_period":
            raise ConfigError("solver.method: the bird model is forced by the wing "
                              "motion; use known_period")
        expected = 1.0 / self.kinematics.frequency
        if self.solver.period is None:
            self.solver.period = expected
        elif not math.isclose(self.solver.period, expected, rel_tol=1e-12):
            raise ConfigError(f"solver.period ({self.solver.period}) must equal "
                              f"1/kinematics.frequency ({expected})")
        if len(self.solver.x0) != 4:
            raise ConfigError("solver.x0: the bird state is [u, w, q, theta] (4 values)")

    # -- files -------------------------------------------------------------
    @classmethod
    def from_dict(cls, data):
        return from_dict(cls, data, "case")

    @classmethod
    def load(cls, path):
        """Read a case from a ``.yaml``/``.yml`` or ``.json`` file."""
        try:
            return cls.from_dict(load_file(path))
        except ConfigError as exc:
            raise ConfigError(f"{path}: {exc}") from None

    def to_dict(self):
        return to_dict(self)

    def save(self, path):
        """Write the fully resolved case (all defaults filled in)."""
        save_file(self.to_dict(), path)

    # -- model and solve ---------------------------------------------------
    def build_model(self):
        """The ``BirdModel`` described by this case."""
        from .bird_model import BirdModel
        k, a, f = self.kinematics, self.aerodynamics, self.flight
        bird = BirdModel(**k.joints(), **k.wing_parameters())
        bird.mass = f.mass
        bird.g = f.g
        bird.inertia_yy = f.inertia_yy
        bird.stability_fd_step = f.stability_fd_step
        bird.wingframe_position = np.array(f.wing_position)
        bird.wingframe_position_tail = np.array(f.tail.position)
        bird.tail_length = f.tail.length
        bird.tail_opening = np.deg2rad(f.tail.opening)
        bird.rho = a.rho
        bird.cl_alpha = a.cl_alpha
        bird.kin_viscosity = a.kin_viscosity
        bird.tail_reference_velocity = a.tail_reference_velocity
        bird.circulation_tol = a.circulation_tol
        bird.circulation_max_iterations = a.circulation_max_iterations
        return bird

    def solve(self, verbose=False):
        """Find the limit cycle; returns a ``dynamics.result.LimitCycleResult``."""
        return self.solver.solve(self.build_model(), verbose=verbose)
