"""Run a case and write a self-describing output directory.

Layout of an output directory::

    config.yaml       fully resolved configuration (all defaults filled in)
    input.<ext>       verbatim copy of the input file, if the case came from one
    result.npz        LimitCycleResult arrays (LimitCycleResult.from_npz reads it)
    summary.json      key results and solver diagnostics, human-readable
    provenance.json   code version (package, git commit, dirty flag), Python,
                      dependency and BLAS versions, platform, threading
                      environment, command line, input checksums, timestamps,
                      status
    solver.log        console output of the solver

The directory is chosen by the caller (there is no default location). It must
not exist or be empty unless ``overwrite=True``. If the run fails,
``provenance.json`` (status ``failed``) and ``error.txt`` are still written.
"""
from __future__ import annotations

import json
import shutil
import time
import traceback
from pathlib import Path

import numpy as np

from .configio import save_file
from .provenance import collect_provenance, sha256_file, utc_now

__all__ = ["prepare_output_dir", "run_bird_case", "write_summary"]


def prepare_output_dir(output_dir, overwrite=False):
    """Create ``output_dir``; refuse a non-empty one unless ``overwrite``."""
    out = Path(output_dir)
    if out.exists() and not out.is_dir():
        raise FileExistsError(f"{out} exists and is not a directory")
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise FileExistsError(f"{out} is not empty; choose another directory or "
                              f"use overwrite=True (--overwrite)")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _json_default(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"not JSON serialisable: {type(obj).__name__}")


def _dump_json(data, path):
    Path(path).write_text(json.dumps(data, indent=2, default=_json_default) + "\n")


def write_summary(result, path):
    """Readable summary of a LimitCycleResult (``summary.json``)."""
    _dump_json(dict(
        converged=result.converged,
        period=result.period,
        n_iterations=result.n_iterations,
        final_error=result.final_error,
        state_at_t0=result.state_at_t0,
        multipliers=[dict(real=float(m.real), imag=float(m.imag), modulus=float(abs(m)))
                     for m in result.multipliers],
        floquet_exponents=[dict(real=float(e.real), imag=float(e.imag))
                           for e in result.floquet_exponents],
        diagnostics=dict(error_history=result.error_history,
                         iteration_times_s=result.iteration_times,
                         elapsed_s=result.elapsed_s),
    ), path)


def run_bird_case(case, output_dir, input_path=None, overwrite=False, verbose=False):
    """Solve a ``BirdCaseConfig`` and write the output directory.

    Parameters
    ----------
    case : BirdCaseConfig or path
        The case, or the path of its ``.yaml``/``.yml``/``.json`` file.
    output_dir : path
        Where to write; must not exist or be empty unless ``overwrite``.
    input_path : path, optional
        Input file to copy and checksum (set automatically when ``case``
        is a path).
    verbose : bool
        Also print the solver output to the console.

    Returns
    -------
    LimitCycleResult
    """
    from .flight.config import BirdCaseConfig

    if not isinstance(case, BirdCaseConfig):
        input_path = Path(case)
        case = BirdCaseConfig.load(input_path)
    out = prepare_output_dir(output_dir, overwrite=overwrite)

    case.save(out / "config.yaml")
    if input_path is not None:
        shutil.copyfile(input_path, out / f"input{Path(input_path).suffix.lower()}")

    started, t0 = utc_now(), time.perf_counter()
    prov = collect_provenance(input_path=input_path, extra=dict(
        case_type="BirdCaseConfig",
        resolved_config_sha256=sha256_file(out / "config.yaml"),
        started_utc=started, status="running"))
    _dump_json(prov, out / "provenance.json")

    try:
        with open(out / "solver.log", "w") as log:
            stream = _Tee(log) if verbose else log
            result = case.solve(log_stream=stream)
    except BaseException as exc:
        prov.update(status="failed", finished_utc=utc_now(),
                    elapsed_s=time.perf_counter() - t0, error=repr(exc))
        _dump_json(prov, out / "provenance.json")
        (out / "error.txt").write_text(traceback.format_exc())
        raise

    np.savez_compressed(out / "result.npz", **result.to_arrays())
    write_summary(result, out / "summary.json")
    prov.update(status="completed", converged=result.converged,
                finished_utc=utc_now(), elapsed_s=time.perf_counter() - t0)
    _dump_json(prov, out / "provenance.json")
    return result


class _Tee:
    """Write to a log file and to the console."""

    def __init__(self, log):
        import sys
        self._streams = (log, sys.__stdout__)

    def write(self, text):
        for s in self._streams:
            s.write(text)

    def flush(self):
        for s in self._streams:
            s.flush()
