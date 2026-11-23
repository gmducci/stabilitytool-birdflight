"""Wing envelope: leading and trailing edges from the skeleton and the feathers.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Split in Stage 7 out of upstream ``BirdModel.get_wingenvelope`` (later
``BirdWing.wing_edges``); the arithmetic is unchanged. Two upstream
computations whose results were never used (feather start points, the
position of the hand tip) were dropped.

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
"""
import numpy as np

from .feathers import feather_geometry
from .rotations import rotation_matrix
from .skeleton import bone_rotations, sample_skeleton, skin_points

__all__ = ["feather_vectors", "trailing_edge", "wing_edges"]


def feather_vectors(angles, rotations, feather_rotations, feather_vectors_rest):
    """Master-feather vectors (3, 7) in the wing frame, from the most distal one.

    Each feather follows the bone it is attached to, with part of the next
    joint's rotation for the intermediate feathers.
    """
    rot1, rot2a, rot2b, rot4, _ = rotations
    wrist_y, wrist_z, elbow_x, elbow_y = angles.wrist_y, angles.wrist_z, angles.elbow_x, angles.elbow_y
    n = np.size(feather_rotations[0])
    vecpss = np.zeros((3, n))
    for i in range(n):
        if i == 0:
            prerot = rot4
        elif i == 1:
            prerot = rot4.dot(rotation_matrix(wrist_z/4, 'x'))
        elif i == 2:
            prerot = rot2b.dot(rotation_matrix(wrist_y/2, 'y')).dot(rotation_matrix(-wrist_z/2, 'x'))
        elif i == 3:
            prerot = rot2a.dot(rotation_matrix(elbow_x/2, 'x')).dot(
                rotation_matrix(wrist_y/2, 'y')).dot(rotation_matrix(-wrist_z/4, 'x'))
        elif i == 4:
            prerot = rot1.dot(rotation_matrix(elbow_y/2, 'y'))
        elif i == 5:
            prerot = rot1.dot(rotation_matrix(elbow_y/4, 'y'))
        elif i == 6:
            prerot = rot1
        rY = rotation_matrix(feather_rotations[0, i], 'y')
        rX = rotation_matrix(feather_rotations[1, i], 'x')
        rot = prerot.dot(rY).dot(rX)
        vecpss[:, i] = np.dot(rot, feather_vectors_rest[:, i])
    return vecpss


def trailing_edge(pts, vecpss, xslice, number_ellipses, arm_length, forearm_length,
                  hand_length):
    """Trailing edge (3, nslice): skin point plus the interpolated feather vector.

    At each station the feather vector is interpolated linearly between the
    two neighbouring master feathers.
    """
    l1, l2, l4 = arm_length, forearm_length, hand_length
    main1 = ((xslice[xslice >= l1+l2+l4/2]-(l1+l2+l4/2))/(l4/2))
    main1 = main1[:, np.newaxis].T
    main2 = ((xslice[(xslice >= l1+l2) & (xslice < l1+l2+l4/2)]-(l1+l2))/(l4/2))
    main2 = main2[:, np.newaxis].T
    abras1 = ((xslice[(xslice >= l1+l2/2) & (xslice < l1+l2)]-(l1+l2/2))/(l2/2))
    abras1 = abras1[:, np.newaxis].T
    abras2 = ((xslice[(xslice >= l1) & (xslice < l1+l2/2)]-(l1))/(l2/2))
    abras2 = abras2[:, np.newaxis].T
    bras1 = ((xslice[(xslice >= l1/2) & (xslice < l1)]-(l1/2))/(l1/2))
    bras1 = bras1[:, np.newaxis].T
    bras2 = (xslice[xslice < l1/2]/(l1/2))
    bras2 = bras2[:, np.newaxis].T

    pm1 = vecpss[:, 0][:, np.newaxis].dot(main1)+vecpss[:, 1][:, np.newaxis].dot(1-main1)
    pm2 = vecpss[:, 1][:, np.newaxis].dot(main2)+vecpss[:, 2][:, np.newaxis].dot(1-main2)
    pa1 = vecpss[:, 2][:, np.newaxis].dot(abras1)+vecpss[:, 3][:, np.newaxis].dot(1-abras1)
    pa2 = vecpss[:, 3][:, np.newaxis].dot(abras2)+vecpss[:, 4][:, np.newaxis].dot(1-abras2)
    pb1 = vecpss[:, 4][:, np.newaxis].dot(bras1)+vecpss[:, 5][:, np.newaxis].dot(1-bras1)
    pb2 = vecpss[:, 5][:, np.newaxis].dot(bras2)+vecpss[:, 6][:, np.newaxis].dot(1-bras2)
    # stations from the root to the tip
    vecps = np.c_[pb2, pb1, pa2, pa1, pm2, pm1]

    nslice = np.size(xslice)
    trailingedge = np.zeros((3, nslice))
    for j in range(nslice):
        vecp = np.array(vecps[:, j])
        trailingedge[0, j] = pts[0, j*number_ellipses]+vecp[0]
        trailingedge[1, j] = pts[1, j*number_ellipses]+vecp[1]
        trailingedge[2, j] = pts[2, j*number_ellipses]+vecp[2]
    return trailingedge


def wing_edges(angles, arm_length, forearm_length, hand_length, feather_lengths,
               feather_spread_angles, feather_pitch_angles):
    """Leading and trailing edges of the right wing for ``JointAngles`` ``angles``.

    Returns
    -------
    leadingedge : ndarray (3, nslice + 1)
        Skin points at mid-ellipse, plus the tip of the trailing edge.
    trailingedge : ndarray (3, nslice)
    """
    [feather_rotations, feather_vectors_rest] = feather_geometry(
        feather_lengths, feather_spread_angles, feather_pitch_angles)
    sampling = sample_skeleton(arm_length, forearm_length, hand_length)
    rotations = bone_rotations(angles)
    pts = skin_points(sampling, rotations, arm_length, forearm_length, hand_length)
    vecpss = feather_vectors(angles, rotations, feather_rotations, feather_vectors_rest)
    ne = sampling.number_ellipses
    trailingedge = trailing_edge(pts, vecpss, sampling.xslice, ne, arm_length,
                                 forearm_length, hand_length)
    leadingedge = np.c_[pts[:, int(ne/2)::int(ne)], trailingedge[:, -1]]
    return leadingedge, trailingedge
