'''
file wing.py
@author Victor Colognesi, Gianmarco Ducci
@copyright Copyright © UCLouvain 2020
Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Wing geometry code moved here unchanged from bird_model.py (class BirdModel)
and bird_dynamics.py (centre_point_velocity) in Stage 3.

multiflap is a Python tool for finding periodic orbits and assess their stability via the Floquet multipliers.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>

List of the contributors to the development of multiflap, Description and complete License: see LICENSE and NOTICE files.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
from collections import namedtuple

import numpy as np

from .envelope import wing_edges
from .feathers import (DEFAULT_FEATHER_LENGTHS, DEFAULT_FEATHER_PITCH_ANGLES,
                       DEFAULT_FEATHER_SPREAD_ANGLES)
from .joints import Elbow, JointAngles, Shoulder, Wrist
from .lines import centre_point_velocity, merge_left_right, quarter_chord_line

__all__ = ["Wing", "WingGeometry"]

#: Lifting line of both wings at one instant (wing frame).
WingGeometry = namedtuple("WingGeometry", [
    "line",         # (3, N) lifting-line points, N odd (33 with the defaults)
    "chord_dir",    # (3, N) chord directions at the points
    "up_dir",       # (3, N) normal directions at the points
    "chord",        # (N,) chords [m]
    "velocity",     # (3, (N-1)/2) wing-motion velocity of the points line[:, 1:-1:2]
])


class Wing:
    """Kinematics and geometry of a poly-articulated bird wing pair.

    Defaults reproduce the upstream multiflap wing (northern bald ibis, study_1).

    Parameters
    ----------
    shoulder, elbow, wrist : Shoulder, Elbow, Wrist
        Joint gaits.
    frequency : float
        Flapping frequency [Hz], common to all joints.
    arm_length, forearm_length, hand_length : float
        Bone lengths [m].
    feather_lengths, feather_spread_angles, feather_pitch_angles : sequences
        Master feathers, from the most distal one (see ``feathers.feather_geometry``).
        Note (upstream behaviour): the skeleton is sampled at four points
        (shoulder, elbow, wrist, tip) and the trailing edge at each point is
        interpolated between neighbouring feathers; at these points feathers
        2, 4 and 6 get zero weight, so only feathers 1, 3, 5 and 7 shape the
        wing.
    body_half_width : float
        Half the gap between the two wing roots [m] (lifting line merged
        across the body).
    kinematic_dt : float
        Time step [s] of the backward finite difference for the wing velocity.
    """

    def __init__(self, shoulder=None, elbow=None, wrist=None, frequency=4,
                 arm_length=.134, forearm_length=.162, hand_length=.084,
                 feather_lengths=DEFAULT_FEATHER_LENGTHS,
                 feather_spread_angles=DEFAULT_FEATHER_SPREAD_ANGLES,
                 feather_pitch_angles=DEFAULT_FEATHER_PITCH_ANGLES,
                 body_half_width=0.05, kinematic_dt=0.25*1e-4):

        self.frequency = frequency
        self.arm_length = arm_length
        self.forearm_length = forearm_length
        self.hand_length = hand_length
        self.feather_lengths = feather_lengths
        self.feather_spread_angles = feather_spread_angles
        self.feather_pitch_angles = feather_pitch_angles
        self.body_half_width = body_half_width
        self.kinematic_dt = kinematic_dt

        self.shoulder = Shoulder()
        self.wrist = Wrist()
        self.elbow = Elbow()

        if isinstance(shoulder, Shoulder):
            self.shoulder = shoulder
        if isinstance(wrist, Wrist):
            self.wrist = wrist
        if isinstance(elbow, Elbow):
            self.elbow = elbow

    def joint_angles(self, t):
        """``JointAngles`` at time ``t`` [rad]."""
        f = self.frequency
        return JointAngles(shoulder_x=self.shoulder.axis_x.angle(t, f),
                           shoulder_y=self.shoulder.axis_y.angle(t, f),
                           shoulder_z=self.shoulder.axis_z.angle(t, f),
                           elbow_x=self.elbow.axis_x.angle(t, f),
                           elbow_y=self.elbow.axis_y.angle(t, f),
                           wrist_y=self.wrist.axis_y.angle(t, f),
                           wrist_z=self.wrist.axis_z.angle(t, f))

    def edges(self, t):
        """Leading and trailing edges of the right wing at time ``t``."""
        return wing_edges(self.joint_angles(t), self.arm_length, self.forearm_length,
                          self.hand_length, self.feather_lengths,
                          self.feather_spread_angles, self.feather_pitch_angles)

    def lifting_line(self, t):
        """Lifting line of both wings joined across the body at time ``t``.

        Returns ``line, chordir, updir, chord``.
        """
        leadingedge, trailingedge = self.edges(t)
        return merge_left_right(quarter_chord_line(leadingedge, trailingedge),
                                self.body_half_width)

    def geometry(self, t):
        """``WingGeometry`` at time ``t``.

        The velocity of the lifting-line centre points is a backward finite
        difference over ``kinematic_dt``.
        """
        dt = self.kinematic_dt
        line, chordir, updir, chord = self.lifting_line(t)
        line_dt, _, _, _ = self.lifting_line(t - dt)
        return WingGeometry(line, chordir, updir, chord,
                            centre_point_velocity(line, line_dt, dt))
