# Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("stabilitytool-birdflight")
except _PackageNotFoundError:  # running from a source tree without installation
    __version__ = "unknown"

from .dynamics.multiple_shooting_period import MultipleShootingPeriod
from .dynamics.lma_solver_period import SolverPeriod
from .dynamics.multiple_shooting import MultipleShooting
from .dynamics.lma_solver import Solver
from .utilities.save_data import SaveData
from .dynamics.systems.redox_oscillation import RedoxModel
from .dynamics.systems.rossler import Rossler
from .dynamics.systems.lorentz import Lorentz
from .dynamics.systems.forced_vdp import ForcedVanDerPol
from .dynamics.rk_integrator import rk2, rk3, rk4
from .utils.mf_plots import Plot
