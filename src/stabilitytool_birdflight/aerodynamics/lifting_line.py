'''
file lifting_line.py
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
import numpy as np  # Import NumPy
from .vortex import induced_velocity_filament, induced_velocity_segment
from .tail import tail_force, tail_geometry


def solve_circulation(y,z,yc,zc,chord,angle_of_attack,cl_alpha,velocity_module,gamma):

    gamma_new = np.zeros_like(gamma)
    vs = np.zeros([3,np.size(gamma)])
    relfac = 0.1

    gamma_filament = np.c_[gamma[:,0], gamma[:,1:] - gamma[0:,:-1], -gamma[0,-1]]

    dz = z[1:] - z[0:-1]
    dy = y[1:] - y[0:-1]
    ds = np.sqrt((dy**2)+(dz**2))
    dz = dz/ds
    dy = dy/ds
    down = np.array([dz,-dy,np.zeros_like(dy)])

    n = np.size(yc)

    for i in range(n):
        v = np.array([[0],[0],[0]])

        for j in range(n+1):

            dy_1 = yc[i] - y[j]
            dz_1 = zc[i] - z[j]

            v = v + gamma_filament[0,j]*np.array([[dz_1],[-dy_1],[0]])/(dy_1**2 + dz_1**2)

        v = (v/(4*np.pi))
        vdown = np.sum(v[:,0]*down[:,i])
        gamma_new[0,i] = 0.5*velocity_module[i]*chord[i]*cl_alpha*(angle_of_attack[i] - vdown/velocity_module[i])
        vs[:,i] = v[:,0]

    gamma_new = relfac*gamma_new + (1-relfac)*gamma

    return gamma_new, vs


def lifting_line_forces(freestream, angular_velocity, v_kin, line, chordir,
                       updir, chord, *, wing_position, tail_position,
                       tail_length, tail_opening, rho=1.225,
                       cl_alpha=2*np.pi, kin_viscosity=1.5e-5,
                       tail_reference_velocity=15, tol=0.001,
                       max_iterations=50):
    """Quasi-steady lifting-line forces on a wing, plus a tail.

    All vectors are expressed in the wing frame used by the lifting line.

    Parameters
    ----------
    freestream : (3,) array
        Velocity of the air relative to the body, far from the wing
        (upstream bird model: ``[0, w, u]``).
    angular_velocity : (3,) array
        Angular velocity of the body (upstream bird model: ``[q, 0, 0]``).
    v_kin : (3, n) array
        Velocity of the lifting-line centre points due to the wing motion.
    line, chordir, updir, chord : arrays
        Lifting-line geometry (points, chord and up directions, chords).
    wing_position : (3,) array
        Position of the wing frame origin relative to the centre of mass.
    tail_position : (3,) array
        Position of the tail frame origin relative to the centre of mass.
    tail_length : float
        Tail length [m].
    tail_opening : float
        Tail opening angle [rad] (0: no tail surface).
    rho : float
        Air density [kg/m^3].
    cl_alpha : float
        Lift-curve slope of the wing sections [1/rad].
    kin_viscosity : float
        Kinematic viscosity of air [m^2/s] (tail skin friction).
    tail_reference_velocity : float
        Velocity [m/s] used for the tail Reynolds number.
    tol, max_iterations : float, int
        Convergence settings of the circulation iteration.
    """
    U = freestream
    ang_velocity = angular_velocity

    wingframe_position = wing_position
    tail_frame_position = tail_position
    # -------------------------------------------------------------------------
    # Initialization of the vector force. It must have the same dimension of the time vector
    # -------------------------------------------------------------------------
    Fx = 0
    Fy = 0
    Fz = 0
    My = 0
    M_wing = 0
    M_drag = 0
    M_lift = 0
    M_tail = 0
    F_tail_tot = 0

    line_c = line[:, 1:-1:2] # Center points: at the center of each
    # interval --> every other point,
    # starting from the second until the one
    # before the last one
    updir = updir[:, 1:-1:2]  # updir, chordir and chord at the center points
    chordir = chordir[:, 1:-1:2]
    chord = chord[1:-1:2]
    line = line[:, ::2]  # "mid" points: points at the junction between two segments --> every other point from the first one to the last one

    # -------------------------------------------------------------------------
    #  u_inf = free stream velocity, equal over each profile (points)
    # -------------------------------------------------------------------------

    u_inf = np.array([U for j in range(np.size(line_c[0]))]).T
    # tangential_wing = (line_c - line_c2)/dt
    line_velocity = np.zeros_like(line_c)
    for j in range(np.size(line_c[0])):
        line_velocity[:, j] = np.cross(ang_velocity, wingframe_position+line_c[:, j])

    line_velocity = line_velocity + v_kin

#    velocity = u_inf - (line_c - line_c2)/dt

    velocity = u_inf - line_velocity

    velocity_profile = np.zeros_like(velocity)
    line_direction = np.zeros_like(updir)
    norm_velocity = np.zeros_like(chord)
    direction_velocity = np.zeros_like(velocity)
    angle_of_attack = np.zeros_like(chord)

    for j in range(np.size(line_c[0])):
        line_direction[:, j] = np.cross(updir[:, j], chordir[:, j])
        velocity_profile[:, j] = velocity[:, j] - line_direction[:, j]*np.sum(line_direction[:, j]*velocity[:, j])
        norm_velocity[j] = np.sqrt(np.sum(velocity_profile[:, j]*velocity_profile[:, j]))
        direction_velocity[:, j] = velocity_profile[:, j]/norm_velocity[j]
        angle_of_attack[j] = np.arctan2(np.sum(direction_velocity[:, j]*updir[:, j]), np.sum(direction_velocity[:, j]*chordir[:, j]))
    ds = np.zeros(len(chord))
    s = np.zeros((np.size(line[0])))
#    print(np.mean(np.rad2deg(angle_of_attack)))
    # -------------------------------------------------------------------------
    # Evaluation of ds length by distance point to point
    # ds is the distance between two consecutives discretised points
    # that belong to the lifting line
    # -------------------------------------------------------------------------

    for j in range(np.size(line[0])-1):
        ds[j] = np.sqrt(np.sum((line[:, j+1] - line[:, j])**2))

    for j in range(1, np.size(line[0])):
        s[j] = s[j-1] + ds[j-1]

    gamma = np.zeros((1, np.size(ds)))
    error = tol + 1
    error_p = np.inf
    count = 0

    while (error > tol) and (count < max_iterations):

        count = count + 1

        [gamma_new, v_downwash] = solve_circulation(line[0,:], line[1,:], line_c[0,:], line_c[1,:],chord, angle_of_attack, cl_alpha, norm_velocity, gamma)

        error = np.mean(np.abs(gamma - gamma_new))/np.mean(np.abs(gamma_new))

        if error > error_p and count > 0:
            print("Error increasing after iteration ",count)
            break

        error_p = error

        gamma = gamma_new

    gamma_filament = np.c_[gamma[:,0], gamma[:,1:] - gamma[0:,:-1], -gamma[0,-1]]
    gamma = np.reshape(gamma, np.size(gamma))
    gamma_filament = np.reshape(gamma_filament, np.size(gamma_filament))
    local_velocity = velocity + v_downwash
    lever_arm = np.zeros_like(line_c)
    BS_radius = np.zeros_like(line_c)
# =============================================================================
#     Induced velocity on the tail
# =============================================================================
    [tail_span, AR_tail, NP_tail] = tail_geometry(
        tail_length, tail_opening=tail_opening, tail_position=tail_position)
    V_ind = 0
    dl_induced = line[:,1:] - line[:,:-1]
    for i in range (np.size(gamma)):
        lever_arm[:, i] = line_c[:, i] + wingframe_position
        BS_radius[:,i] = (NP_tail - lever_arm[:, i])
        cross_prod = (np.cross(dl_induced[:,i],BS_radius[:,i]))
        V_ind = V_ind + ((gamma[i]/(4*np.pi))*cross_prod)/(np.linalg.norm(BS_radius[:,i])**3)
#        V_ind = V_ind + circulation.InducedVel_Segment(NP_tail,line[:,i]+wingframe_position, line[:,i+1]+wingframe_position, gamma[i], 1e-13)

    lever_arm1 = np.zeros_like(line)
    BS_radius1 = np.zeros_like(line)
    for i in range (len(line)):
        lever_arm1[:, i] = line[:, i] + wingframe_position
        BS_radius1[:,i] = (NP_tail - lever_arm1[:, i])
        V_ind = V_ind + induced_velocity_filament(BS_radius1[:,i],line[:,i], U, gamma_filament[i])


    velocity_tail_q = np.cross(ang_velocity,tail_frame_position)
    U_tail = U + V_ind + velocity_tail_q
#    U_tail = U + V_ind
    M = np.zeros_like(gamma)
#    alpha_tail = np.arctan2(U_tail[1],U_tail[2])
    for j in range(np.size(gamma)):
        F = rho*gamma[j]*np.cross(local_velocity[:,j] , line_direction[:,j])
        lever_arm[:, j] = line_c[:, j] + wingframe_position
        F_moment = np.array([F[0]*ds[j], F[1]*ds[j], F[2]*ds[j]])
        Drag_moment = np.array([0., 0., F[2]*ds[j]])
        Lift_moment = np.array([0., F[1]*ds[j], 0.])

        Fx = Fx + F[0]*ds[j]  # Component along wing span
        Fy = Fy + F[1]*ds[j]  # Component of Lift (perpendicular to the free stream)
        Fz = Fz + F[2]*ds[j]  # Component of drag (along free stream)
        M_drag_j = np.cross(lever_arm[:, j], Drag_moment)
        M_lift_j = np.cross(lever_arm[:, j], Lift_moment)
        M_wing_j = np.cross(lever_arm[:, j], F_moment)

        M_wing = M_wing + M_wing_j[0]
        M_drag = M_drag + M_drag_j[0]
        M_lift = M_lift + M_lift_j[0]
        My = My + M[0]

    F_tail_tot = tail_force(U_tail, tail_span, tail_length=tail_length,
                            rho=rho, kin_viscosity=kin_viscosity,
                            reference_velocity=tail_reference_velocity)

    M_tail = np.cross(NP_tail, F_tail_tot)
    My = M_wing + M_tail[0]
    return Fx, Fy, Fz, My, F_tail_tot[1], M_wing, M_tail[0], M_drag, M_lift
