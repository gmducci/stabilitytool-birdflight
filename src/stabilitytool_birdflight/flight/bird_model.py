'''
file bird_model.py
@author Victor Colognesi, Gianmarco Ducci
@copyright Copyright © UCLouvain 2020
Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.

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
import numpy as np
from ..kinematics.wing import BirdWing
from .bird_dynamics import dynamics, get_aeroforces, get_stability_matrix


class BirdModel(BirdWing):
    """Longitudinal flight dynamics of a flapping bird, state x = [u, w, q, theta].

    Couples the wing kinematics (``BirdWing``: joints, frequency, morphology)
    with the lifting-line aerodynamics. All parameters are read at call time,
    so changing an attribute changes the model. Defaults reproduce upstream
    multiflap (study_1 reference bird).

    Attributes
    ----------
    g : float
        Gravitational acceleration [m/s^2].
    mass : float
        Body mass [kg].
    inertia_yy : float
        Pitch moment of inertia [kg m^2] (hard-coded 0.1 upstream).
    wingframe_position, wingframe_position_tail : (3,) arrays
        Wing and tail frame origins relative to the centre of mass, in the
        wing frame (x spanwise, y up, z backward) [m].
    tail_length, tail_opening : float
        Tail length [m] and opening angle [rad] (0: no tail).
    tail_chord : float
        Unused (as upstream).
    rho : float
        Air density [kg/m^3].
    stability_fd_step : float
        Relative step of the finite differences in ``get_stability_matrix``.

    Keyword arguments other than the joints are passed to ``BirdWing``
    (``frequency``, bone and feather geometry, ``body_half_width``,
    ``kinematic_dt``).
    """

    def __init__(self, shoulder=None, elbow=None, wrist=None, **wing_parameters):

        #Parameters:
        self.dimensions = 4
        self.g = 9.81
        self.mass = 1.2
        self.inertia_yy = 0.1
        self.stability_fd_step = 1e-3
        self.wingframe_position = np.array([0, -0.0, -0.05])
        self.wingframe_position_tail = np.array([0, -0., .3])
        self.tail_length = 0.25
        self.tail_chord = 0.15
        self.tail_opening = 0.
        self.rho = 1.225  # air density [kg/m^3]
        super().__init__(shoulder=shoulder, elbow=elbow, wrist=wrist,
                         **wing_parameters)

    # calling methods of BirdModel that are defined in other files
    get_aeroforces = get_aeroforces
    dynamics = dynamics
    get_stability_matrix = get_stability_matrix
#bird_shoulder = Shoulder(axis_x=Joint(0.2,0.014,-np.pi/2), 
#                         axis_y=Joint(-np.deg2rad(19),np.pi/12,np.pi/2), 
#                         axis_z=Joint(0,np.deg2rad(42),np.pi))
#bird_elbow = Elbow(axis_x=Joint(0.,np.pi/6,-np.pi/2), 
#                   axis_y=Joint(np.pi/6,np.pi/6,-np.pi/2))
#
#bird_wrist = Wrist(axis_y=Joint(-np.pi/6,np.pi/6,np.pi/2), 
#                   axis_z=Joint(0.,0.,0.))
#
#mybird = BirdModel(shoulder=bird_shoulder, elbow=bird_elbow, wrist=bird_wrist)
