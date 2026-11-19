"""Provenance of a run: code version, environment and inputs.

Collected for every run written by ``runs.write_run`` (``provenance.json``).
Deliberately not recorded: host name and user name.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

__all__ = ["collect_provenance", "git_info", "sha256_file", "utc_now"]

DEPENDENCIES = ("numpy", "scipy", "matplotlib", "pyyaml")
THREAD_ENV_VARS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                   "VECLIB_MAXIMUM_THREADS", "MPLBACKEND", "PYTHONHASHSEED")
PACKAGE = "stabilitytool-birdflight"


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(repo, *args):
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                             text=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


def git_info(path=None):
    """Commit, describe, branch and dirty flag of the repository holding ``path``.

    ``dirty`` is true when tracked files differ from the commit (untracked
    files are ignored). Returns ``None`` if ``path`` is not in a git
    repository or git is unavailable (for example an installed wheel).
    """
    path = Path(path or Path(__file__).parent)
    root = _git(path, "rev-parse", "--show-toplevel")
    if not root:
        return None
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    lock = Path(root) / "uv.lock"
    return dict(
        commit=_git(root, "rev-parse", "HEAD"),
        describe=_git(root, "describe", "--tags", "--always", "--dirty"),
        branch=_git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        dirty=bool(status) if status is not None else None,
        uv_lock_sha256=sha256_file(lock) if lock.exists() else None,
    )


def _version(dist):
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def _blas():
    try:
        import numpy as np
        cfg = np.show_config(mode="dicts")
        blas = cfg.get("Build Dependencies", {}).get("blas", {})
        return {k: blas.get(k) for k in ("name", "version")}
    except Exception as exc:  # show_config formats differ across numpy versions
        return {"error": repr(exc)}


def collect_provenance(input_path=None, extra=None):
    """Dictionary describing the code, environment and input of a run."""
    pkg_dir = Path(__file__).resolve().parent
    prov = dict(
        package=dict(name=PACKAGE, version=_version(PACKAGE), location=str(pkg_dir)),
        git=git_info(pkg_dir),
        python=dict(version=sys.version, implementation=platform.python_implementation(),
                    executable=sys.executable),
        dependencies={d: _version(d) for d in DEPENDENCIES},
        blas=_blas(),
        platform=dict(system=platform.system(), release=platform.release(),
                      machine=platform.machine(), processor=platform.processor()),
        environment={v: os.environ.get(v) for v in THREAD_ENV_VARS},
        command=list(sys.argv),
        working_directory=os.getcwd(),
    )
    if input_path is not None:
        p = Path(input_path)
        prov["input"] = dict(path=str(input_path), sha256=sha256_file(p))
    if extra:
        prov.update(extra)
    return prov
