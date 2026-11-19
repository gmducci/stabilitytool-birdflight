# Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("stabilitytool-birdflight")
except _PackageNotFoundError:  # running from a source tree without installation
    __version__ = "unknown"

from .ms_package.multiple_shooting_period import MultipleShootingPeriod
from .ms_package.lma_solver_period import SolverPeriod
from .ms_package.multiple_shooting import MultipleShooting
from .ms_package.lma_solver import Solver
from .utilities.save_data import SaveData
from .odes.redox_oscillation import RedoxModel
from .odes.rossler import Rossler
from .odes.lorentz import Lorentz
from .odes.forced_vdp import ForcedVanDerPol
from .ms_package.rk_integrator import rk2, rk3, rk4
from .utils.mf_plots import Plot
