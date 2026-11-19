"""Reading, writing and validating configuration dataclasses (YAML or JSON).

Shared by the per-module configurations (``kinematics.config``,
``aerodynamics.config``, ``dynamics.config``, ``flight.config``). It does not
import any of those modules, so they stay independent of each other.

Conversion rules (``from_dict``):

* unknown keys and missing required fields raise ``ConfigError``;
* ``float`` fields accept ints, floats and numeric strings such as ``1e-5``
  (which PyYAML reads as a string), not booleans; ``int`` fields only ints, ``bool`` only booleans, ``str`` only strings;
* ``tuple[float, ...]`` and fixed-length tuples accept lists;
* ``Literal[...]`` values are checked; ``Optional[X]`` accepts ``None``;
* nested dataclasses accept mappings; a dataclass may define
  ``_from_value(value, where)`` / ``_to_value()`` to accept a compact form
  (for example a joint as ``[offset, amplitude, phase]``).

Each dataclass may validate its values in ``__post_init__``.
"""
from __future__ import annotations

import dataclasses
import json
import math
import types
import typing
from pathlib import Path

import yaml

__all__ = ["ConfigError", "from_dict", "to_dict", "load_file", "save_file",
           "check_positive", "check_finite"]


class ConfigError(ValueError):
    """Invalid configuration (message names the offending key)."""


# ---------------------------------------------------------------------------
# dict -> dataclass
# ---------------------------------------------------------------------------

def from_dict(cls, data, where=None):
    """Build dataclass ``cls`` from a (nested) mapping, with validation."""
    where = where or cls.__name__
    if hasattr(cls, "_from_value") and not isinstance(data, dict):
        return cls._from_value(data, where)
    if not isinstance(data, dict):
        raise ConfigError(f"{where}: expected a mapping, got {type(data).__name__}")
    hints = typing.get_type_hints(cls)
    init_fields = {f.name: f for f in dataclasses.fields(cls) if f.init}
    unknown = sorted(set(data) - set(init_fields))
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {unknown}; allowed: "
                          f"{sorted(init_fields)}")
    missing = [n for n, f in init_fields.items()
               if n not in data and f.default is dataclasses.MISSING
               and f.default_factory is dataclasses.MISSING]
    if missing:
        raise ConfigError(f"{where}: missing required key(s) {missing}")
    kwargs = {k: _convert(hints[k], v, f"{where}.{k}") for k, v in data.items()}
    try:
        return cls(**kwargs)
    except ConfigError:
        raise
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{where}: {exc}") from exc


def _convert(tp, value, where):
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if dataclasses.is_dataclass(tp):
        return from_dict(tp, value, where)
    if origin in (typing.Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _convert(non_none[0], value, where)
        raise ConfigError(f"{where}: unsupported union type {tp}")
    if origin is typing.Literal:
        if value not in args:
            raise ConfigError(f"{where}: {value!r} is not one of {list(args)}")
        return value
    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise ConfigError(f"{where}: expected a list, got {type(value).__name__}")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_convert(args[0], v, f"{where}[{i}]") for i, v in enumerate(value))
        if len(value) != len(args):
            raise ConfigError(f"{where}: expected {len(args)} values, got {len(value)}")
        return tuple(_convert(a, v, f"{where}[{i}]") for i, (a, v) in enumerate(zip(args, value)))
    if tp is float:
        if isinstance(value, str):
            # PyYAML (YAML 1.1) reads "1e-5" (no decimal point) as a string.
            try:
                return float(value)
            except ValueError:
                raise ConfigError(f"{where}: expected a number, got {value!r}") from None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{where}: expected a number, got {value!r}")
        return float(value)
    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{where}: expected an integer, got {value!r}")
        return value
    if tp is bool:
        if not isinstance(value, bool):
            raise ConfigError(f"{where}: expected true/false, got {value!r}")
        return value
    if tp is str:
        if not isinstance(value, str):
            raise ConfigError(f"{where}: expected a string, got {value!r}")
        return value
    raise ConfigError(f"{where}: unsupported field type {tp}")


# ---------------------------------------------------------------------------
# dataclass -> dict
# ---------------------------------------------------------------------------

def to_dict(obj):
    """Plain (YAML/JSON-serialisable) representation of a config dataclass."""
    if hasattr(obj, "_to_value"):
        return obj._to_value()
    if dataclasses.is_dataclass(obj):
        return {f.name: to_dict(getattr(obj, f.name))
                for f in dataclasses.fields(obj) if f.init}
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    if isinstance(obj, float):
        return float(obj)
    return obj


# ---------------------------------------------------------------------------
# files
# ---------------------------------------------------------------------------

def load_file(path):
    """Read a mapping from a ``.yaml``/``.yml`` or ``.json`` file."""
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    elif path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        raise ConfigError(f"{path}: unknown config file type (use .yaml, .yml or .json)")
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return data


def save_file(data, path):
    """Write a mapping to ``.yaml``/``.yml`` or ``.json`` (floats written exactly)."""
    path = Path(path)
    if path.suffix.lower() in (".yaml", ".yml"):
        path.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=None))
    elif path.suffix.lower() == ".json":
        path.write_text(json.dumps(data, indent=2) + "\n")
    else:
        raise ConfigError(f"{path}: unknown config file type (use .yaml, .yml or .json)")


# ---------------------------------------------------------------------------
# small validators for __post_init__
# ---------------------------------------------------------------------------

def check_positive(where, **values):
    for name, v in values.items():
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            raise ConfigError(f"{where}.{name}: must be a positive number, got {v!r}")


def check_finite(where, **values):
    for name, v in values.items():
        seq = v if isinstance(v, (list, tuple)) else [v]
        if not all(isinstance(e, (int, float)) and math.isfinite(e) for e in seq):
            raise ConfigError(f"{where}.{name}: must be finite, got {v!r}")
