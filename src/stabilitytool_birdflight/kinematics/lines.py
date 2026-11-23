'''
file lines.py
@author Victor Colognesi
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

def distance_point_line(p, p0, v):
    s = np.sum(v*(p-p0))
    closest = p0 + (s*v)   # This might be .dot()
    d = np.sqrt(np.sum((p-closest)*(p-closest)))

    return s, closest, d



def distance_line_line(p01, v1, p02, v2):

    v1v2 = np.sum(v1*(v2))
    p01v1 = np.sum(p01*(v1))
    p02v1 = np.sum(p02*(v1))
    p01v2 = np.sum(p01*(v2))
    p02v2 = np.sum(p02*(v2))

    s1 = (p02v1 - p01v1 + p01v2*v1v2 - p02v2*v1v2)/(1 - v1v2*v1v2)
    s2 = p01v2 + s1*v1v2 - p02v2

    p1 = p01 + s1*v1
    p2 = p02 + s2*v2
    d = np.sqrt(np.sum((p1-p2)*((p1-p2))))

    return(s1, s2, p1, p2, d)


def quarter_chord_naive(leadingedge, trailingedge):
    line = .75*leadingedge + .25*trailingedge
    chord_leadingedge = leadingedge
    chord_trailingedge = trailingedge
    return line, chord_leadingedge, chord_trailingedge


def smooth_line(line, npt):

    smooth_radius = 0.05

    # Getting the length of the curve
    notok = 1
    l = np.zeros((3, npt))
    whilecicle = 0
    while notok == 1:
        whilecicle = whilecicle + 1
        n = np.size(line[0])
        lcurve = 0
        for i in range(n-1):
            lcurve = lcurve + np.sqrt(np.sum((line[:,i+1]-line[:,i])**2))

        ds = lcurve/(npt-1)

        l[:,0] = line [:,0]

        j = 0  #Until here is OK

        for i in range(1,npt):
            dist = np.sqrt(np.sum((line[:,j+1]-l[:,i-1])**2))
            while dist < ds:
                j = j+1
                if j < (np.size(line[0])-1):
                    dist = dist + np.sqrt(np.sum((line[:,j+1]-line[:,j])**2))
                else:
                    dist = ds + 1

            if j < (np.size(line[0])-1):
                fac = dist - ds
                den = np.sqrt(np.sum((line[:,j+1]-line[:,j])**2))
                fac = fac/den
                l[:,i] = (1-fac)*line[:,j+1]+fac*line[:,j]
            else:
                l[:,i] = line [:,-1]

        l2 = l

        notok = 0

        for i in range(1,npt-1):
            vec1 = l[:,i] - l[:,i-1]
            vec2 = l[:,i+1] - l[:,i]
            coss = np.sum(vec1*(vec2))/((np.linalg.norm(vec1))*(np.linalg.norm(vec2)))
            # =============================================================================
            # since truncation errors might lead to having coss slightly greater than 1
            # =============================================================================
            if coss > (1):
                angle = np.arccos(1.0)
            else:
                angle = np.arccos(coss)
            d = np.linalg.norm(vec1)
            smooth_angle = d/smooth_radius
            while angle > smooth_angle:
                notok = 1
                point = (l[:,i+1] + l[:,i-1])/2
                l2[:,i] = (l2[:,i] + point)/2
                vec1 = l2[:,i] - l[:, i-1]
                vec2 = l[:,i+1] - l2[:,i]
                coss = np.sum(vec1*(vec2))/((np.linalg.norm(vec1))*(np.linalg.norm(vec2)))
                angle = np.arccos(coss)
                d = np.linalg.norm(vec1)
                smooth_angle = d/smooth_radius

        line = l2

    return line


def smooth_quarter_chord_line(oldline,oldchordle,oldchordte):

    npt = np.size((oldline[0]))
    lcurve = 0
    for i in range(npt-1):
        lcurve = lcurve + np.sqrt(np.sum((oldline[:,i+1]-oldline[:,i])**2))

    ds = lcurve/(npt-1)

    line = np.zeros_like(oldline)
    chord_leadingedge = np.zeros_like((oldline))
    chord_trailingedge = np.zeros_like((oldline))
    line[:,0] = 1*oldline[:,0]
    chord_leadingedge[:,0] = oldchordle[:,0]
    chord_trailingedge[:,0] = oldchordte[:,0]
    j = 0

    for i in range(1,npt):
        dist = np.sqrt(np.sum((oldline[:,j+1]-line[:,i-1])**2))
        while dist < ds:
            j = j+1
            if j < (np.size(oldline[0])-1):
                dist = dist + np.sqrt(np.sum((oldline[:,j+1]-oldline[:,j])**2))
            else:
                dist = ds + 1

        if j < (np.size(line[0])-1):
            fac = dist - ds
            den = np.sqrt(np.sum((oldline[:,j+1]-oldline[:,j])**2))
            fac = fac/den
            line[:,i] = (1-fac)*oldline[:,j+1]+fac*oldline[:,j]
            chord_leadingedge[:,i] = (1-fac)*oldchordle[:,j+1]+fac*oldchordle[:,j]
            chord_trailingedge[:,i] = (1-fac)*oldchordte[:,j+1]+fac*oldchordte[:,j]
        else:
            line[:,i] = 1*oldline [:,-1]
            chord_leadingedge[:,i] = oldchordle[:,-1]
            chord_trailingedge[:,i] = oldchordte[:,-1]

    return line, chord_leadingedge, chord_trailingedge


def _refine_line_step(line, chord_leadingedge, chord_trailingedge, leadingedge, trailingedge):
    n = np.size(line[0])
    nle = np.size(leadingedge[0])
    nte = np.size(trailingedge[0])

    newline = np.zeros_like(line)
    newchordle = np.zeros_like(chord_leadingedge)
    newchordte = np.zeros_like(chord_trailingedge)
    newline[:,0] = line[:,0]
    newline[:,-1] = line[:,-1]
    newchordle[:,0] = chord_leadingedge[:,0]
    newchordle[:,-1] = chord_leadingedge[:,-1]
    newchordte[:,0] = chord_trailingedge[:,0]
    newchordte[:,-1] = chord_trailingedge[:,-1]

    # External Iteration

    for i in range(1,n-1):
        linevec = line[:,i+1] - line[:,i-1]
        linevec = linevec/np.linalg.norm(linevec)

        # orthogonalizing chordvec wrt linevec
        chordvec = chord_trailingedge[:,i] - chord_leadingedge[:,i]
        chordvec = chordvec - np.dot((np.sum(linevec*chordvec)),linevec)    # BUG HERE
        chordvec = chordvec/np.linalg.norm(chordvec)

        """
        getting points in le closest to chord line
        take the first two points of le as first references
        """
        jref1 = 0
        jref2 = 1

        [_ , _, dref1] = distance_point_line(leadingedge[:,jref1], line[:,i], chordvec) # If it does not work DP2L[][2] LAST ELEMENT OF OUTPUT
        [_, _, dref2] = distance_point_line(leadingedge[:,jref2], line[:,i], chordvec)


        """
        First IF Routine, checked (Below)
        """
        if (dref2<dref1):
            a = jref2
            jref2 = jref1
            jref1 = a
            a = dref2
            dref2 = dref1
            dref1 = a

        for j in range(2, nle):
            [_,_,dtest] = distance_point_line(leadingedge[:,j], line[:,i], chordvec)
            if (dtest < dref2):
                dref2 = dtest
                jref2 = j
            if (dref2 < dref1):
                a = jref2
                jref2 = jref1
                jref1 = a
                a = dref2
                dref2 = dref1
                dref1 = a

        levec = leadingedge[:,jref2] - leadingedge[:,jref1]
        levec = levec/np.linalg.norm(levec)
        [_, _, newchordle[:,i], _, _] = distance_line_line(leadingedge[:,jref1],levec,line[:,i],chordvec)

        # Repeat this for the trailing edge

        jref1 = 0
        jref2 = 1

        [_, _, dref1] = distance_point_line(trailingedge[:,jref1], line[:,i], chordvec) # If it does not work DP2L[][2] LAST ELEMENT OF OUTPUT
        [_, _, dref2] = distance_point_line(trailingedge[:,jref2], line[:,i], chordvec)

        if dref2 < dref1:
            a = jref2
            jref2 = jref1
            jref1 = a
            a = dref2
            dref2 = dref1
            dref1 = a

        for j in range(2, nte):

            [_,_,dtest] = distance_point_line(trailingedge[:,j], line[:,i], chordvec)
            if (dtest < dref2):
                dref2 = dtest
                jref2 = j
            if (dref2 < dref1):
                a = jref2
                jref2 = jref1
                jref1 = a
                a = dref2
                dref2 = dref1
                dref1 = a

        tevec = trailingedge[:,jref2] - trailingedge[:,jref1]
        tevec = tevec/np.linalg.norm(tevec)
        [_, _, newchordte[:,i], _, _] = distance_line_line(trailingedge[:,jref1],tevec,line[:,i],chordvec)
        newline[:,i] = .75*newchordle[:,i] + .25*newchordte[:,i]

    return(newline, newchordle, newchordte)

def refine_line(line, chord_leadingedge, chord_trailingedge, leadingedge, trailingedge, it):

    relfactor = .25

    [line, chord_leadingedge, chord_trailingedge] = smooth_quarter_chord_line(line,chord_leadingedge,chord_trailingedge)
    [newline, newchordle, newchordte] = _refine_line_step(line, chord_leadingedge, chord_trailingedge,leadingedge,trailingedge)

    chgt = 0

    for i in range(np.size(line[0]) - 1):

        local_max = np.maximum(0, i-1)
        local_min = np.minimum(np.size(line[0]), i + 1)
        norm1 = np.linalg.norm(newline[:,i] - line[:,i])
        norm2 = np.linalg.norm(line[:,local_max]-line[:,local_min])
        chgt = chgt + relfactor*norm1/norm2

    chgt = chgt/np.size(line[0])

    line = relfactor*newline + (1-relfactor)*line
    chord_leadingedge = relfactor*newchordle + (1-relfactor)*chord_leadingedge
    chord_trailingedge = relfactor*newchordte + (1-relfactor)*chord_trailingedge

    return line, chord_leadingedge, chord_trailingedge, chgt


def quarter_chord_line(leadingedge, trailingedge):
    """Quarter-chord line of the right wing and its mirror image.

    The edges are resampled on 16 points, the quarter-chord line is refined
    iteratively (``refine_line``) and smoothed. Returns ``lifting_line, updir,
    chord_direction, chord`` (right wing), the same four for the left wing,
    and the mean spacing ``dx`` of the line points.
    """

    nlete = 16

    leadingedge = smooth_line(leadingedge, nlete)
    trailingedge = smooth_line(trailingedge, nlete)

    [line, chord_leadingedge, chord_trailingedge] = quarter_chord_naive(leadingedge, trailingedge)

    tol = 0.1
    nmax = 10
    a = tol + 1
    chg = tol + 1
    it = 1

    while a > tol and it < nmax:
        [line, chord_leadingedge, chord_trailingedge, a] = refine_line(line,chord_leadingedge,
                                                        chord_trailingedge,leadingedge,trailingedge,it)

        chg = np.c_[chg, a]

        it = it + 1

    [lifting_line, chord_leadingedge, chord_trailingedge] = smooth_quarter_chord_line(line, chord_leadingedge, chord_trailingedge)

    line_dummy = np.copy(lifting_line)
    nl = np.size(line[0])
    chord_direction = np.zeros((3,nl))
    updir = np.zeros((3,nl))
    chord = np.zeros((nl))

# =============================================================================
#     Evaluating the chord and its direction
#     For every slice, it's calculated the distance btw Lead. edge and Trail.
#     edge (chord_distance), and then the modulus, so that the versor is
#     identified.
# =============================================================================

    for i in range(nl):

        chord_distance = (chord_trailingedge[:,i] - chord_leadingedge[:,i]) + 1e-20
        chord[i] = np.linalg.norm(chord_distance)
        #chord = chord[:,np.newaxis]
        chord_direction[:,i] = chord_distance/chord[i]

        if i == 0:
            linevec = line[:,1] - line[:,0]
        elif i == (nl - 1):
            linevec = line[:,-1] - line[:,-2]
        else:
            linevec = line[:,i+1] - line[:,i-1]

        linevec = linevec/np.linalg.norm(linevec)
        updir[:,i] = np.cross(chord_direction[:,i], linevec)  # Different value in the last iteration

    updir_dummy = np.copy(updir)
    chord_direction_dummy = np.copy(chord_direction)
    chord_dummy = np.copy(chord)
    # Left Wing

    line_left = np.fliplr(line_dummy)
    up_direction_left = np.fliplr(updir_dummy)
    chord_direction_left = np.fliplr(chord_direction_dummy)
    chord_left = chord_dummy[::-1]

    line_left[0,:] = np.negative(line_left[0,:])
    chord_direction_left[0,:] = np.negative(chord_direction_left[0,:])
    up_direction_left[0,:] = np.negative(up_direction_left[0,:])

    sumvector = np.zeros((1,nl))
    for i in range(nl):
        if i < nl-1:
            sumvector[0,i] = np.sum((lifting_line[:,i+1] - lifting_line[:,i])**2)
        else:
            sumvector[0,i] = np.sum((lifting_line[:,-1] - lifting_line[:, -2])**2)


    dx = np.mean(np.sqrt(sumvector))

    return lifting_line, updir, chord_direction, chord, line_left, up_direction_left, chord_direction_left, chord_left, dx



def merge_left_right(line_package, body_half_width):
    """Join both wings across the body into one lifting line.

    ``line_package`` is the output of ``quarter_chord_line``. The wings are
    shifted by +-``body_half_width`` and joined by straight points whose
    chord is divided by 1e4 (no lift over the body). Returns ``line, chordir,
    updir, chord``.
    """
    line_r,updir_r,chordir_r,chord_r,line_l,updir_l,chordir_l,chord_l, dx = line_package
    x_ep = body_half_width
    nmid = int(np.ceil(2*x_ep/dx))
    line_r[0,:] = line_r[0,:] + x_ep
    line_l[0,:] = line_l[0,:] - x_ep

    xmid = np.linspace(line_l[0,-1],line_r[0,0],nmid)
    length_xmid = np.size(xmid)
    line_mid = np.array([xmid, line_r[1,0]*np.ones(np.size(xmid)), line_r[2,0]*np.ones(np.size(xmid))])
    chordir_mid = np.array([chordir_r[:,0] for i in range(np.size(xmid))]).T
    updir_mid = np.array([updir_r[:,0] for i in range(np.size(xmid))]).T
    chord_mid = np.zeros(length_xmid)
    chord_mid[:] = chord_r[0]*np.ones(length_xmid)

    line = np.c_[line_l,line_mid[:,1:-1],line_r]
    chordir = np.c_[chordir_l, chordir_mid[:,1:-1], chordir_r]
    updir = np.c_[updir_l, updir_mid[:,1:-1], updir_r]
    chord = np.concatenate([chord_l, chord_mid[1:-1]/1e4, chord_r])
    return line, chordir, updir, chord


def centre_point_velocity(line, line_dt, dt):
    """Velocity of the lifting-line centre points by backward finite difference."""
    line_c = line[:, 1:-1:2]
    line_c2 = line_dt[:, 1:-1:2]
    v_kin = (line_c - line_c2)/dt
    return v_kin
