"""The wing kinematics can be used without aerodynamics or flight mechanics."""
import subprocess
import sys
import textwrap


def test_birdwing_without_aero_or_flight():
    code = textwrap.dedent("""
        import sys
        import numpy as np
        from stabilitytool_birdflight.kinematics.wing import BirdWing
        from stabilitytool_birdflight.kinematics.joints import Shoulder, Elbow, Wrist, Joint
        wing = BirdWing(
            shoulder=Shoulder(axis_x=Joint(0.2, 0.014, -np.pi/2),
                              axis_y=Joint(-np.deg2rad(19), np.deg2rad(20), np.pi/2),
                              axis_z=Joint(0, np.deg2rad(42), np.pi)),
            elbow=Elbow(axis_x=Joint(0., np.pi/6, -np.pi/2),
                        axis_y=Joint(np.pi/6, np.pi/6, -np.pi/2)),
            wrist=Wrist(axis_y=Joint(-np.pi/6, np.pi/6, np.pi/2),
                        axis_z=Joint(0., 0., 0.)))
        line, chordir, updir, chord, v_kin = wing.get_lifting_line_kinematics(0.05)
        assert line.shape[0] == 3 and v_kin.shape[0] == 3
        loaded = [m for m in sys.modules
                  if m.startswith(("stabilitytool_birdflight.aerodynamics",
                                   "stabilitytool_birdflight.flight",
                                   "stabilitytool_birdflight.dynamics"))]
        assert not loaded, loaded
        print("ok")
    """)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
