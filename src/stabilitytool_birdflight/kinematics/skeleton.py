"""Wing skeleton: bone rotations and skin points from the joint angles.

Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
Split in Stage 7 out of upstream ``BirdModel.get_wingenvelope`` (later
``BirdWing.wing_edges``); the arithmetic is unchanged.

The skeleton is in the wing frame (x spanwise, y up, z backward): arm
(length l1) from the shoulder, forearm (l2) from the elbow, hand (l4) from
the wrist. It is sampled at ``nslice`` spanwise stations (upstream: four,
shoulder, elbow, wrist and tip), each carrying ``number_ellipses`` skin points.
Each skin point follows the bones with blending weights (w1: arm, w2a/w2b:
forearm without/with the elbow twist, w3: straight shoulder-wrist segment,
w4: hand).

Copyright <2020> <Université catholique de Louvain (UCLouvain), Belgique>
Licensed under the Apache License, Version 2.0 (see LICENSE and NOTICE).
"""
from collections import namedtuple

import numpy as np

from .rotations import rotation_matrix, scaling_matrix

__all__ = ["SkeletonSampling", "BoneRotations", "sample_skeleton", "bone_rotations",
           "skin_points"]

#: Spanwise sampling of the skeleton (independent of time).
SkeletonSampling = namedtuple("SkeletonSampling", [
    "xslice",            # spanwise station positions along the straight skeleton
    "feather_index",     # 1-based station where each master feather starts
    "points",            # (3, nslice*number_ellipses) skin points, straight wing
    "weights",           # (w1, w2a, w2b, w3, w4), one value per skin point
    "number_ellipses",   # skin points per station
])

#: Rotations of the bones at one instant.
BoneRotations = namedtuple("BoneRotations", ["rot1", "rot2a", "rot2b", "rot4", "ey1"])


def sample_skeleton(arm_length, forearm_length, hand_length):
    """Spanwise stations, skin points and blending weights of the straight wing."""
    l1, l2, l4 = arm_length, forearm_length, hand_length
    npoints_arm = 1
    npoints_forearm = 1
    npoints_hand = 2
    nslice = npoints_arm + npoints_forearm + npoints_hand
    delta_arm = l1/npoints_arm
    delta_forearm = l2/npoints_forearm
    delta_hand = l4/(npoints_hand-1)

    xslice = np.zeros(nslice)
    for i in range(npoints_arm):
        xslice[i] = 0 + (i*delta_arm)
    for i in range(npoints_forearm):
        xslice[i + npoints_arm] = l1 + (i*delta_forearm)
    for i in range(npoints_hand):
        xslice[i + npoints_arm + npoints_forearm] = l1 + l2 + (i*delta_hand)

    # station (1-based) where each master feather starts, from the most distal
    index = np.zeros(7)
    index[0] = np.size(xslice)
    index[1] = np.nonzero(xslice >= l1+l2+l4/2)[0][0]
    index[2] = np.nonzero(xslice >= l1+l2)[0][0]
    index[3] = np.nonzero(xslice >= l1+l2/2)[0][0]
    index[4] = np.nonzero(xslice >= l1)[0][0]
    index[5] = np.nonzero(xslice >= l1/2)[0][0]
    index[6] = 1

    # skin points: an ellipse (here 2 points) around each station
    number_ellipses = 2
    s = np.linspace(0, 2*np.pi, number_ellipses + 1)
    s = s[0:number_ellipses]
    skz = .01
    sky = .01
    z = skz*np.cos(s)
    y = sky*np.sin(s)
    points = np.zeros((3, nslice*number_ellipses))

    w1 = np.zeros(nslice*number_ellipses)
    w2a = np.zeros(nslice*number_ellipses)
    w2b = np.zeros(nslice*number_ellipses)
    w3 = np.zeros(nslice*number_ellipses)
    w4 = np.zeros(nslice*number_ellipses)
    for j in range(nslice):
        block = slice(j*number_ellipses, (j+1)*number_ellipses)
        for k in range(number_ellipses):
            points[:, (j)*number_ellipses+k] = [xslice[j], y[k], z[k]]
        facb = (z/skz + 1)/2
        if xslice[j] < l1:
            lrefcd = min(l1, l2)
            if xslice[j] < l1-lrefcd/2:
                faccd1 = 1
            else:
                faccd1 = 0.5*(1-np.sin(np.pi*(xslice[j]-l1)/lrefcd))
            faccd2 = 1-faccd1
            fac2a = 1
            fac2b = 0
            w1[block] = facb*faccd1
            w2a[block] = facb*faccd2*fac2a
            w2b[block] = facb*faccd2*fac2b
            w3[block] = (1-facb)
            w4[block] = 0
        elif xslice[j] < l1 + l2:
            lrefcd = min(l1, l2)
            if xslice[j] < l1+lrefcd/2:
                faccd2 = 0.5*(1+np.sin(np.pi*(xslice[j]-l1)/lrefcd))
            else:
                faccd2 = 1
            faccd1 = 1-faccd2
            fac2b = (xslice[j]-l1)/l2
            fac2a = 1-fac2b
            lrefpg = min(l2, l4)
            if xslice[j] < l1+l2-lrefpg/2:
                facpg2 = 1
            else:
                facpg2 = 0.5*(1-np.sin(np.pi*(xslice[j]-(l1+l2))/lrefpg))
            facpg4 = 1-facpg2
            w1[block] = facb*faccd1*facpg2
            w2a[block] = facb*faccd2*fac2a*facpg2
            w2b[block] = facb*faccd2*fac2b*facpg2
            w3[block] = (1-facb)*facpg2
            w4[block] = facpg4
        else:
            fac2a = 0
            fac2b = 1
            lrefpg = min(l2, l4)
            if xslice[j] < l1+l2+lrefpg/2:
                facpg4 = 0.5*(1+np.sin(np.pi*(xslice[j]-(l1+l2))/lrefpg))
            else:
                facpg4 = 1
            facpg2 = 1-facpg4
            w1[block] = 0
            w2a[block] = facb*facpg2*fac2a
            w2b[block] = facb*facpg2*fac2b
            w3[block] = (1-facb)*facpg2
            w4[block] = facpg4

    return SkeletonSampling(xslice, index, points, (w1, w2a, w2b, w3, w4), number_ellipses)


def bone_rotations(angles):
    """Rotation matrices of arm, forearm and hand for ``JointAngles`` ``angles``."""
    ey = [0, 1, 0]
    rot1X = rotation_matrix(angles.shoulder_x, 'x')
    rot1Z = rotation_matrix(angles.shoulder_z, 'z')
    rot1Y = rotation_matrix(angles.shoulder_y, 'y')
    rot1 = np.array(rot1X).dot(np.array(rot1Z)).dot(np.array(rot1Y))
    ey1 = np.array(rot1).dot(np.array(ey))

    rot2relY = rotation_matrix(angles.elbow_y, 'y')
    rot2relX = rotation_matrix(angles.elbow_x, 'x')
    rot2b = np.array(rot1).dot(np.array(rot2relY)).dot(np.array(rot2relX))
    rot2a = np.array(rot1).dot(np.array(rot2relY))

    rot4relY = rotation_matrix(angles.wrist_y, 'y')
    rot4relZ = rotation_matrix(angles.wrist_z, 'z')
    rot4 = np.array(rot2b).dot(np.array(rot4relY)).dot(np.array(rot4relZ))
    return BoneRotations(rot1, rot2a, rot2b, rot4, ey1)


def skin_points(sampling, rotations, arm_length, forearm_length, hand_length):
    """Skin points of the articulated wing, shape (3, nslice*number_ellipses)."""
    rot1, rot2a, rot2b, rot4, ey1 = rotations
    origin = [0, 0, 0]
    end1 = np.array([arm_length, 0, 0])
    end2 = np.array([forearm_length, 0, 0])
    end4 = np.array([hand_length, 0, 0])
    vec30 = np.array(end1) + np.array(end2) - np.array(origin)

    endd1 = np.array(rot1).dot(np.array(end1))
    endd2 = np.array(rot2a).dot(np.array(end2))+np.array(endd1)
    endd4 = np.array(rot4).dot(np.array(end4))+np.array(endd2)  # noqa: F841 (upstream)
    vec3 = np.array(endd2)-np.array(origin)

    # straight segment from the shoulder to the wrist, stretched along x
    ex3 = vec3/np.linalg.norm(vec3)
    ey3 = ey1
    ez3 = np.array([ex3[1]*ey3[2]-ex3[2]*ey3[1], ex3[2]*ey3[0]-ex3[0]*ey3[2],
                    ex3[0]*ey3[1]-ex3[1]*ey3[0]])
    rot3 = np.array([ex3, ey3, ez3])
    rot3 = rot3.transpose()
    kx = np.linalg.norm(vec3)/np.linalg.norm(vec30)
    comp3 = scaling_matrix(kx, 'x')

    w1, w2a, w2b, w3, w4 = sampling.weights
    points = sampling.points
    pts = np.array(points)
    for j in range(np.size(points[0])):
        pt = np.array(points[:, j])
        pt1 = rot1.dot(pt)
        pt2a = rot2a.dot((pt-end1)) + endd1
        pt2b = rot2b.dot((pt-end1)) + endd1
        pt3 = rot3.dot(comp3).dot(pt)
        pt4 = rot4.dot((pt-(end1+end2))) + endd2
        pts[:, j] = pt1*w1[j] + pt2a*w2a[j] + pt2b*w2b[j] + pt3*w3[j] + pt4*w4[j]
    return pts
