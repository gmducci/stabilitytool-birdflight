# Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
"""Upstream helper to save arrays and text reports of a simulation.

For new work prefer ``stabilitytool_birdflight.runs`` (``run_bird_case`` or the
``stabilitytool-birdflight run`` command), which also records the resolved
configuration and the provenance of the run.

Changes from upstream: the results folder must be given explicitly (upstream
default ``'../results'`` depended on the working directory); errors are raised
instead of being swallowed by bare ``except:`` clauses; files are closed; the
wrist offset and phase are written correctly (upstream wrote the amplitude).
"""
from pathlib import Path

import numpy as np

_ALIASES = {'multipliers_LC': 'floquet_multipliers', 'solution_LC': 'solution_LC',
            'time_array_LC': 'time_array', 'fixed_points': 'fixed_points'}


class SaveData:

    def __init__(self, simulation_name, folder_results):
        self.simulation_name = simulation_name
        self.folder_results = str(folder_results)
        self.folder_simulation = str(Path(folder_results) / simulation_name)

    def save_data(self, filename, data_array):
        name = _ALIASES.get(filename, filename)
        np.save(Path(self.folder_simulation) / name, data_array, allow_pickle=True)
        print(filename + " file saved")

    def make_folder(self):
        """Create the simulation folder (and parents); existing folder is fine."""
        Path(self.folder_simulation).mkdir(parents=True, exist_ok=True)

    def remove_contents(self):
        """Delete the files directly inside the simulation folder."""
        for f in Path(self.folder_simulation).iterdir():
            if f.is_file():
                f.unlink()

    def remove_directory(self):
        """Remove the simulation folder (it must be empty)."""
        Path(self.folder_simulation).rmdir()

    def write_simulation_settings(self, bird_obj):
        lines = [
            'FRAMES COORDINATES (with respect to the aerodynamic reference system)',
            'Wing frame position: ' + str(bird_obj.wingframe_position),
            'Tail frame position: ' + str(bird_obj.wingframe_position_tail),
            'Tail opening: ' + str(round(np.rad2deg(bird_obj.tail_opening))),
            '----------------------------------',
            'KINEMATICS',
            '----------------------------------',
            '----------------------------------',
        ]
        joints = [('SHOULDER', [('shoulder x', bird_obj.shoulder.axis_x),
                                ('shoulder y', bird_obj.shoulder.axis_y),
                                ('shoulder z', bird_obj.shoulder.axis_z)]),
                  ('ELBOW', [('elbow y', bird_obj.elbow.axis_y),
                             ('elbow x', bird_obj.elbow.axis_x)]),
                  ('WRIST', [('wrist y', bird_obj.wrist.axis_y),
                             ('wrist z', bird_obj.wrist.axis_z)])]
        for title, axes in joints:
            lines.append('- ' + title + ' JOINT:')
            for k, (label, joint) in enumerate(axes):
                lines += ['Amplitude ' + label + ': ' + str(np.rad2deg(joint.amplitude)),
                          'Offset ' + label + ': ' + str(np.rad2deg(joint.offset)),
                          'Phase ' + label + ': ' + str(np.rad2deg(joint.phase)),
                          '----------------------------------']
            lines.append('----------------------------------')
        with open(Path(self.folder_simulation) / 'simulation_settings.txt', 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def write_simulation_results(self, error, multipliers):
        lines = ['Number of Iterations: ' + str(np.size(error)),
                 'Error: ' + str(error[-1]),
                 'Floquet Multipliers: ' + str(multipliers)]
        lines += ['|$Lambda_%d$|: %s' % (k + 1, np.linalg.norm(m))
                  for k, m in enumerate(multipliers[:4])]
        with open(Path(self.folder_simulation) / 'DataFile_Results.txt', 'w') as f:
            f.write('\n'.join(lines) + '\n')
