"""Configuration of the wing kinematics (gait and morphology).

All angles are in **degrees**. Joint angles follow the code's reference system
(wing frame: x spanwise, y up, z backward); see ``baseline/README.md`` for the
mapping to study_1 Table 1. Each joint angle is

    q(t) = offset + amplitude * sin(2*pi*frequency*t + phase).

In a YAML file a joint is written ``[offset, amplitude, phase]``::

    kinematics:
      frequency: 4.0
      shoulder_x: [11.459155902616464, 0.8021409131831525, -90]
      ...
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..configio import ConfigError, check_finite, check_positive, from_dict, to_dict
from .joints import Elbow, Joint, Shoulder, Wrist

__all__ = ["JointConfig", "WingConfig"]


@dataclass
class JointConfig:
    """Harmonic joint: offset, amplitude, phase [deg]."""

    offset: float
    amplitude: float
    phase: float

    def __post_init__(self):
        check_finite("JointConfig", offset=self.offset, amplitude=self.amplitude,
                     phase=self.phase)

    @classmethod
    def _from_value(cls, value, where):
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return from_dict(cls, dict(zip(("offset", "amplitude", "phase"), value)), where)
        raise ConfigError(f"{where}: a joint is [offset, amplitude, phase] in degrees "
                          f"or a mapping with these keys, got {value!r}")

    def _to_value(self):
        return [float(self.offset), float(self.amplitude), float(self.phase)]

    def build(self):
        """``Joint`` in radians."""
        return Joint(np.deg2rad(self.offset), np.deg2rad(self.amplitude),
                     np.deg2rad(self.phase))


@dataclass
class WingConfig:
    """Gait and morphology of the wing pair (see ``kinematics.wing.BirdWing``).

    Defaults are the upstream multiflap values, except the joints, which must
    be given.
    """

    shoulder_x: JointConfig
    shoulder_y: JointConfig
    shoulder_z: JointConfig
    elbow_x: JointConfig
    elbow_y: JointConfig
    wrist_y: JointConfig
    wrist_z: JointConfig
    frequency: float = 4.0
    arm_length: float = .134
    forearm_length: float = .162
    hand_length: float = .084
    feather_lengths: tuple[float, ...] = (.25, .225, .2, .175, .15, .125, .1)
    feather_spread_angles: tuple[float, ...] = (90.0, 67.5, 45.0, 22.5, 0.0, 0.0, 0.0)
    feather_pitch_angles: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    body_half_width: float = 0.05
    kinematic_dt: float = 0.25*1e-4

    def __post_init__(self):
        where = "kinematics"
        check_positive(where, frequency=self.frequency, arm_length=self.arm_length,
                       forearm_length=self.forearm_length,
                       hand_length=self.hand_length,
                       body_half_width=self.body_half_width,
                       kinematic_dt=self.kinematic_dt)
        n = len(self.feather_lengths)
        if n != 7:
            raise ConfigError(f"{where}.feather_lengths: the wing model has 7 master "
                              f"feathers, got {n}")
        for name in ("feather_spread_angles", "feather_pitch_angles"):
            if len(getattr(self, name)) != n:
                raise ConfigError(f"{where}.{name}: expected {n} values")
        check_positive(where, **{f"feather_lengths[{i}]": v
                                 for i, v in enumerate(self.feather_lengths)})

    @classmethod
    def from_dict(cls, data):
        return from_dict(cls, data, "kinematics")

    def to_dict(self):
        return to_dict(self)

    def wing_parameters(self):
        """Keyword arguments of ``BirdWing`` (radians, metres, seconds)."""
        return dict(
            frequency=self.frequency,
            arm_length=self.arm_length,
            forearm_length=self.forearm_length,
            hand_length=self.hand_length,
            feather_lengths=tuple(self.feather_lengths),
            feather_spread_angles=tuple(np.deg2rad(self.feather_spread_angles)),
            feather_pitch_angles=tuple(np.deg2rad(self.feather_pitch_angles)),
            body_half_width=self.body_half_width,
            kinematic_dt=self.kinematic_dt,
        )

    def joints(self):
        """``shoulder``, ``elbow``, ``wrist`` objects (radians)."""
        return dict(
            shoulder=Shoulder(axis_x=self.shoulder_x.build(),
                              axis_y=self.shoulder_y.build(),
                              axis_z=self.shoulder_z.build()),
            elbow=Elbow(axis_x=self.elbow_x.build(), axis_y=self.elbow_y.build()),
            wrist=Wrist(axis_y=self.wrist_y.build(), axis_z=self.wrist_z.build()),
        )

    def build(self):
        """A ``BirdWing`` with this gait and morphology."""
        from .wing import BirdWing
        return BirdWing(**self.joints(), **self.wing_parameters())
