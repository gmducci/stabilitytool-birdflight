"""Size of the tail pitch-rate sign error: forces vs pitch damping (about 1 min).

Along the stored study_1 limit cycle (upstream wing, tail opened to 20 and
30 deg), compares the code's tail inflow with the rotation term subtracted
(study_2 Eq. 8): tail force and moment along the cycle, and the pitch-damping
entry d(q')/dq of the Jacobian.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from stabilitytool_birdflight.flight.config import BirdCaseConfig  # noqa: E402

from model import REPO, Study2Bird  # noqa: E402


def bird(opening, fix_rotation):
    case = BirdCaseConfig.load(REPO / "examples" / "configs" / "bird_study1_reference.yaml")
    case.flight.tail.opening = opening
    k, a, f = case.kinematics, case.aerodynamics, case.flight
    return Study2Bird(k.build(), a, mass=f.mass, g=f.g, inertia_yy=f.inertia_yy,
                      wing_position=f.wing_position, tail_position=f.tail.position,
                      tail_length=f.tail.length, tail_opening=np.deg2rad(f.tail.opening),
                      stability_fd_step=f.stability_fd_step,
                      force_options=dict(fix_rotation=fix_rotation))


def main():
    d = np.load(REPO / "baseline" / "data" / "bird_study1.npz")
    t_all, x_all = d["trajectory_t"], d["trajectory_x"]
    _, idx = np.unique(t_all, return_index=True)
    ts, xs = t_all[idx][::3], x_all[idx][::3]
    wing_only = np.mean([bird(0, False).jacobian(x, t)[2, 2] for x, t in zip(xs, ts)])
    print(f"{len(ts)} points on the study_1 cycle; d(q')/dq of the wing alone: {wing_only:+.3f} 1/s\n")
    for opening in (20, 30):
        out = {}
        for fix in (False, True):
            b = bird(opening, fix)
            f = [b.forces(x, t) for x, t in zip(xs, ts)]
            out[fix] = dict(tail=np.array([g.tail_fy for g in f]),
                            mtail=np.array([g.tail_moment for g in f]),
                            a22=np.array([b.jacobian(x, t)[2, 2] for x, t in zip(xs, ts)]))
        rel = lambda k: np.max(np.abs(out[True][k] - out[False][k]))/np.max(np.abs(out[False][k]))
        print(f"tail {opening} deg: tail force along the cycle differs by at most {100*rel('tail'):.1f} %, "
              f"tail moment {100*rel('mtail'):.1f} %")
        print(f"   pitch damping d(q')/dq (mean): code {out[False]['a22'].mean():+.3f}, "
              f"rotation term subtracted {out[True]['a22'].mean():+.3f} 1/s\n")


if __name__ == "__main__":
    main()
