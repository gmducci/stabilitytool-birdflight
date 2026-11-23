"""Configuration files: round trip, validation, and equivalence with direct construction."""
import contextlib
import io
from pathlib import Path

import numpy as np
import pytest
import yaml

from stabilitytool_birdflight.configio import ConfigError
from stabilitytool_birdflight.flight.bird import BirdModel
from stabilitytool_birdflight.flight.config import BirdCaseConfig
from stabilitytool_birdflight.kinematics.joints import Elbow, Joint, Shoulder, Wrist

CONFIGS = Path(__file__).resolve().parents[1] / "examples" / "configs"
CASE_FILES = sorted(CONFIGS.glob("*.yaml"))
REFERENCE = CONFIGS / "bird_main.yaml"


def raw(path=REFERENCE):
    return yaml.safe_load(path.read_text())


@pytest.mark.parametrize("path", CASE_FILES, ids=[p.name for p in CASE_FILES])
@pytest.mark.parametrize("suffix", [".yaml", ".json"])
def test_round_trip(path, suffix, tmp_path):
    case = BirdCaseConfig.load(path)
    out = tmp_path / f"case{suffix}"
    case.save(out)
    again = BirdCaseConfig.load(out)
    assert again == case
    assert again.to_dict() == case.to_dict()


def test_degrees_convert_exactly_to_upstream_radians():
    joints = BirdCaseConfig.load(REFERENCE).kinematics.joints()
    s, e, w = joints["shoulder"], joints["elbow"], joints["wrist"]
    got = [(j.offset, j.amplitude, j.phase) for j in
           (s.axis_x, s.axis_y, s.axis_z, e.axis_x, e.axis_y, w.axis_y, w.axis_z)]
    upstream = [(0.2, 0.014, -np.pi / 2), (-np.deg2rad(19), np.deg2rad(20), np.pi / 2),
                (0, np.deg2rad(44), np.pi), (0., np.pi / 6, -np.pi / 2),
                (np.pi / 6, np.pi / 6, -np.pi / 2), (-np.pi / 6, np.pi / 6, np.pi / 2),
                (0., 0., 0.)]
    assert got == upstream  # exact equality, bit for bit


def test_config_bird_equals_hand_built_bird():
    """Same RHS as BirdModel built like upstream main.py (all defaults)."""
    d = np.deg2rad
    hand = BirdModel(
        shoulder=Shoulder(axis_x=Joint(0.2, 0.014, -np.pi / 2),
                          axis_y=Joint(-d(19), d(20), np.pi / 2),
                          axis_z=Joint(0, d(44), np.pi)),
        elbow=Elbow(axis_x=Joint(0., np.pi / 6, -np.pi / 2),
                    axis_y=Joint(np.pi / 6, np.pi / 6, -np.pi / 2)),
        wrist=Wrist(axis_y=Joint(-np.pi / 6, np.pi / 6, np.pi / 2),
                    axis_z=Joint(0., 0., 0.)))
    cfg = BirdCaseConfig.load(REFERENCE).build_model()
    x, t = np.array([18.67, -2.15, -0.12, -0.116]), 0.07
    with contextlib.redirect_stdout(io.StringIO()):
        for name in ("get_aeroforces", "dynamics", "get_stability_matrix"):
            a = np.asarray(getattr(hand, name)(x, t), float)
            b = np.asarray(getattr(cfg, name)(x, t), float)
            assert np.array_equal(a, b), name


def test_period_defaults_to_inverse_frequency():
    data = raw()
    del data["solver"]["period"]
    data["kinematics"]["frequency"] = 5.0
    assert BirdCaseConfig.from_dict(data).solver.period == 0.2


def test_scientific_notation_without_dot_is_accepted():
    data = yaml.safe_load(REFERENCE.read_text().replace("tolerance: 1.0e-05", "tolerance: 1e-5"))
    assert data["solver"]["tolerance"] == "1e-5"          # PyYAML reads a string
    assert BirdCaseConfig.from_dict(data).solver.tolerance == 1e-5


def _set(data, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        data = data[k]
    if value is _DELETE:
        del data[keys[-1]]
    else:
        data[keys[-1]] = value


_DELETE = object()

INVALID = [
    ("flight.masss", 1.0, "unknown key"),
    ("kinematics.wrist_z", _DELETE, "missing required"),
    ("flight.mass", -1.0, "positive"),
    ("flight.mass", "heavy", "expected a number"),
    ("solver.points", 2.5, "expected an integer"),
    ("solver.points", 1, "at least 2"),
    ("solver.period", 0.3, "must equal 1/kinematics.frequency"),
    ("solver.method", "unknown_period", "known_period"),
    ("solver.jacobian", "symbolic", "is not one of"),
    ("solver.x0", [18.0, 0.5, 0.1], "4 values"),
    ("kinematics.shoulder_x", [1, 2], "offset, amplitude, phase"),
    ("kinematics.feather_lengths", [0.2, 0.2], "7 master feathers"),
    ("flight.tail.opening", 200.0, "[0, 180)"),
    ("flight.wing_position", [0.0, 0.0], "expected 3 values"),
]


@pytest.mark.parametrize("key,value,message", INVALID, ids=[c[0] + ":" + str(c[1]) for c in INVALID])
def test_invalid_config_is_rejected(key, value, message):
    data = raw()
    _set(data, key, value)
    with pytest.raises(ConfigError, match=None) as exc:
        BirdCaseConfig.from_dict(data)
    assert message in str(exc.value), str(exc.value)
