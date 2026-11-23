'''
file feathers.py
@author Victor Colognesi
@copyright Copyright © UCLouvain 2020
Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.

multiflap is a Python tool for finding periodic orbits and assess their stability via the Floquet multipliers.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>

List of the contributors to the development of multiflap, Description and complete License: see LICENSE and NOTICE files.

Licensed under the Apache License, Version 2.0 (the "License")
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

# Upstream values for the seven master feathers, from the most distal one.
# Note: study_1 Table 1 lists different lengths (primaries 0.25, 0.275, 0.25;
# secondaries 0.225, 0.2, 0.175, 0.15 m); see baseline/README.md.
DEFAULT_FEATHER_LENGTHS = (.25, .225, .2, .175, .15, .125, .1)
DEFAULT_FEATHER_SPREAD_ANGLES = (np.pi/2, 3*np.pi/8, np.pi/4, np.pi/8, 0, 0, 0)
DEFAULT_FEATHER_PITCH_ANGLES = (0, 0, 0, 0, 0, 0, 0)


def feather_geometry(lengths=DEFAULT_FEATHER_LENGTHS,
           spread_angles=DEFAULT_FEATHER_SPREAD_ANGLES,
           pitch_angles=DEFAULT_FEATHER_PITCH_ANGLES):
    """Rest rotations and vectors of the master feathers.

    Returns ``prot`` (2 x n: spread angles about y, pitch angles about x [rad])
    and ``pvec`` (3 x n: feather vectors, length along z [m]).
    """
    n = len(lengths)
    prot = np.array([list(spread_angles), list(pitch_angles)])
    pvec = np.array([[0]*n, [0]*n, list(lengths)])
    return prot, pvec

if __name__ == "__main__":
   feather_geometry()

