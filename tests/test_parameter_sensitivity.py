"""Every bird parameter must change the output it is supposed to affect.

Guards against the upstream bug where BirdModel attributes (wing position,
tail, frequency) were silently ignored because the code read module-level
settings instead (CLAUDE.md, Section 4).
"""
import contextlib
import io

import numpy as np
import pytest

from stabilitytool_birdflight.flight.bird_model import BirdModel
from stabilitytool_birdflight.kinematics.bird import Elbow, Joint, Shoulder, Wrist

# A state near the study_1 limit cycle, with q != 0 so that angular-velocity
# terms (wing and tail positions) contribute.
X = np.array([18.07, -2.0, -0.112, -0.117])
T = 0.05
OPEN_TAIL = dict(tail_opening=np.deg2rad(30))


def make_bird(**attrs):
    d = np.deg2rad
    bird = BirdModel(
        shoulder=Shoulder(axis_x=Joint(0.2, 0.014, -np.pi / 2),
                          axis_y=Joint(-d(19), d(20), np.pi / 2),
                          axis_z=Joint(0, d(42), np.pi)),
        elbow=Elbow(axis_x=Joint(0., np.pi / 6, -np.pi / 2),
                    axis_y=Joint(np.pi / 6, np.pi / 6, -np.pi / 2)),
        wrist=Wrist(axis_y=Joint(-np.pi / 6, np.pi / 6, np.pi / 2),
                    axis_z=Joint(0., 0., 0.)))
    for k, v in attrs.items():
        setattr(bird, k, v)
    return bird


def output(bird, kind):
    with contextlib.redirect_stdout(io.StringIO()):
        if kind == "forces":
            return np.array(bird.get_aeroforces(X, T), float)
        if kind == "dynamics":
            return np.asarray(bird.dynamics(X, T), float)
        return np.asarray(bird.get_stability_matrix(X, T), float)


# (parameter, new value, attributes of the reference bird, affected output)
CASES = [
    ("mass", 1.3, {}, "dynamics"),
    ("g", 9.7, {}, "dynamics"),
    ("inertia_yy", 0.12, {}, "dynamics"),
    ("rho", 1.1, {}, "forces"),
    ("wingframe_position", np.array([0., 0., -0.08]), {}, "forces"),
    ("frequency", 4.5, {}, "forces"),
    ("arm_length", 0.14, {}, "forces"),
    ("forearm_length", 0.17, {}, "forces"),
    ("hand_length", 0.09, {}, "forces"),
    ("feather_lengths", (.25, .275, .25, .225, .2, .175, .15), {}, "forces"),
    # Feathers 2, 4 and 6 have zero weight at the four skeleton points of the
    # upstream discretisation (see BirdWing docstring), so vary feather 1.
    ("feather_spread_angles",
     (np.pi / 2 + 0.1, 3 * np.pi / 8, np.pi / 4, np.pi / 8, 0, 0, 0), {}, "forces"),
    ("feather_pitch_angles", (0.1, 0, 0, 0, 0, 0, 0), {}, "forces"),
    ("body_half_width", 0.06, {}, "forces"),
    ("kinematic_dt", 1e-4, {}, "forces"),
    ("tail_opening", np.deg2rad(30), {}, "forces"),
    ("tail_length", 0.3, OPEN_TAIL, "forces"),
    ("wingframe_position_tail", np.array([0., 0., 0.35]), OPEN_TAIL, "forces"),
    ("stability_fd_step", 1e-4, {}, "stability"),
]


@pytest.mark.parametrize("name,value,base,kind", CASES, ids=[c[0] for c in CASES])
def test_parameter_changes_output(name, value, base, kind):
    ref = output(make_bird(**base), kind)
    new = output(make_bird(**base, **{name: value}), kind)
    rel = np.max(np.abs(new - ref)) / np.max(np.abs(ref))
    assert rel > 1e-9, f"changing {name} had no effect on {kind} (rel {rel:.1e})"


def test_tail_parameters_have_no_effect_when_tail_closed():
    """With tail_opening = 0 the tail has zero span: no tail force (as upstream)."""
    ref = output(make_bird(), "forces")
    new = output(make_bird(tail_length=0.3), "forces")
    assert np.array_equal(ref, new)


def test_wing_parameters_can_be_passed_to_constructor():
    bird = BirdModel(frequency=5, arm_length=0.14)
    assert bird.frequency == 5 and bird.arm_length == 0.14
