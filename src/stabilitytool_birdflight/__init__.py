# Modified by the stabilitytool-birdflight project (fork of multiflap), 2026. See CHANGELOG.md.
"""stabilitytool-birdflight: limit cycles, Floquet stability and bird flapping flight.

Subpackages are independent: ``kinematics``, ``aerodynamics`` and ``dynamics``
do not import each other; ``flight`` couples them. The names below (upstream
multiflap API) are imported lazily, so importing one subpackage does not load
the others.
"""
from importlib import import_module as _import_module
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("stabilitytool-birdflight")
except _PackageNotFoundError:  # running from a source tree without installation
    __version__ = "unknown"

_LAZY = {
    "KnownPeriodShooting": ".dynamics.shooting",
    "UnknownPeriodShooting": ".dynamics.shooting",
    "levenberg_marquardt": ".dynamics.solver",
    "ConvergenceError": ".dynamics.solver",
    "SaveData": ".utilities.save_data",
    "RedoxModel": ".dynamics.systems.redox",
    "Rossler": ".dynamics.systems.rossler",
    "Lorenz": ".dynamics.systems.lorenz",
    "ForcedVanDerPol": ".dynamics.systems.van_der_pol",
    "rk2": ".dynamics.integrators",
    "rk3": ".dynamics.integrators",
    "rk4": ".dynamics.integrators",
    "Plot": ".utils.mf_plots",
}

__all__ = ["__version__", *_LAZY]


def __getattr__(name):
    if name in _LAZY:
        value = getattr(_import_module(_LAZY[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_LAZY))
