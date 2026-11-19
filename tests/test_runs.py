"""Run directories, provenance, CLI and SaveData.

The bird solve takes minutes, so these tests replace ``BirdCaseConfig.solve``
with a fast Rossler solve; the real end-to-end bird run is in
``test_bird_regression.py`` (marked slow).
"""
import json
import re
from pathlib import Path

import numpy as np
import pytest

from stabilitytool_birdflight import cli
from stabilitytool_birdflight.dynamics.config import SolverConfig
from stabilitytool_birdflight.dynamics.result import LimitCycleResult
from stabilitytool_birdflight.dynamics.systems.rossler import Rossler
from stabilitytool_birdflight.flight.config import BirdCaseConfig
from stabilitytool_birdflight.provenance import collect_provenance, sha256_file
from stabilitytool_birdflight.runs import run_bird_case
from stabilitytool_birdflight.utilities.save_data import SaveData

CASE = Path(__file__).resolve().parents[1] / "examples" / "configs" / "bird_main.yaml"


@pytest.fixture(scope="module")
def toy_result():
    return SolverConfig(x0=[.1, 5., 3.6], method="unknown_period", points=30,
                        period_guess=5., t_steps=5000,
                        integrator="odeint").solve(Rossler(a=0.2, b=0.2, c=5.7))


@pytest.fixture
def fast_solve(monkeypatch, toy_result):
    def solve(self, verbose=False, log_stream=None):
        if log_stream is not None:
            log_stream.write("fake solver output\n")
        return toy_result
    monkeypatch.setattr(BirdCaseConfig, "solve", solve)


def test_run_directory_contents(tmp_path, fast_solve, toy_result):
    out = tmp_path / "run"
    run_bird_case(CASE, out)
    assert sorted(p.name for p in out.iterdir()) == [
        "config.yaml", "input.yaml", "provenance.json", "result.npz",
        "solver.log", "summary.json"]
    # resolved config reloads to the same case; input copied verbatim
    assert BirdCaseConfig.load(out / "config.yaml") == BirdCaseConfig.load(CASE)
    assert (out / "input.yaml").read_bytes() == CASE.read_bytes()
    assert "fake solver output" in (out / "solver.log").read_text()
    # result round trip
    back = LimitCycleResult.from_npz(out / "result.npz")
    for name, value in toy_result.to_arrays().items():
        if name != "final_error":
            assert np.array_equal(np.asarray(getattr(back, name)), value), name
    summary = json.loads((out / "summary.json").read_text())
    assert summary["n_iterations"] == toy_result.n_iterations
    assert len(summary["diagnostics"]["iteration_times_s"]) == len(toy_result.error_history)


def test_provenance(tmp_path, fast_solve):
    out = tmp_path / "run"
    run_bird_case(CASE, out)
    prov = json.loads((out / "provenance.json").read_text())
    assert prov["status"] == "completed" and prov["converged"] is True
    assert prov["input"]["sha256"] == sha256_file(CASE)
    assert prov["resolved_config_sha256"] == sha256_file(out / "config.yaml")
    assert prov["dependencies"]["numpy"] == np.__version__
    assert prov["started_utc"] <= prov["finished_utc"]
    git = prov["git"]
    assert git is not None and re.fullmatch(r"[0-9a-f]{40}", git["commit"])
    assert isinstance(git["dirty"], bool)
    assert not {"hostname", "host", "user", "username"} & set(prov)


def test_non_empty_output_dir_is_refused(tmp_path, fast_solve):
    out = tmp_path / "run"
    out.mkdir()
    (out / "something.txt").write_text("x")
    with pytest.raises(FileExistsError):
        run_bird_case(CASE, out)
    run_bird_case(CASE, out, overwrite=True)
    assert (out / "result.npz").exists()


def test_failed_run_is_recorded(tmp_path, monkeypatch):
    def broken(self, verbose=False, log_stream=None):
        raise RuntimeError("solver did not converge within 100 iterations")
    monkeypatch.setattr(BirdCaseConfig, "solve", broken)
    out = tmp_path / "run"
    with pytest.raises(RuntimeError):
        run_bird_case(CASE, out)
    prov = json.loads((out / "provenance.json").read_text())
    assert prov["status"] == "failed" and "converge" in prov["error"]
    assert "RuntimeError" in (out / "error.txt").read_text()
    assert not (out / "result.npz").exists()


def test_cli_run_validate_show(tmp_path, fast_solve, capsys):
    assert cli.main(["validate", str(CASE)]) == 0
    out = tmp_path / "run"
    assert cli.main(["run", str(CASE), "--output", str(out)]) == 0
    assert cli.main(["show", str(out)]) == 0
    text = capsys.readouterr().out
    assert "valid" in text and "status        completed" in text and "multipliers" in text
    # non-empty output directory: error, exit status 1
    assert cli.main(["run", str(CASE), "-o", str(out)]) == 1


def test_cli_validate_rejects_bad_file(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("kinematics: {}\nsolver: {x0: [1, 2, 3, 4]}\n")
    assert cli.main(["validate", str(bad)]) == 1
    assert "missing required key" in capsys.readouterr().err


def test_provenance_without_input():
    prov = collect_provenance()
    assert "input" not in prov and prov["package"]["name"] == "stabilitytool-birdflight"


def test_savedata_explicit_folder(tmp_path):
    from stabilitytool_birdflight.flight.bird_model import BirdModel
    from stabilitytool_birdflight.kinematics.bird import Elbow, Joint, Shoulder, Wrist
    with pytest.raises(TypeError):
        SaveData("sim")                       # no hidden default folder any more
    sd = SaveData("sim", tmp_path / "a" / "b")
    sd.make_folder()
    sd.save_data("multipliers_LC", np.array([1.0, 2.0]))
    assert (tmp_path / "a" / "b" / "sim" / "floquet_multipliers.npy").exists()
    bird = BirdModel(shoulder=Shoulder(Joint(0, 0, 0), Joint(0, 0, 0), Joint(0, 0, 0)),
                     elbow=Elbow(Joint(0, 0, 0), Joint(0, 0, 0)),
                     wrist=Wrist(axis_y=Joint(np.deg2rad(-30), np.deg2rad(30), np.deg2rad(90)),
                                 axis_z=Joint(0, 0, 0)))
    sd.write_simulation_settings(bird)
    text = (tmp_path / "a" / "b" / "sim" / "simulation_settings.txt").read_text()
    value = {m.group(1): float(m.group(2))
             for m in re.finditer(r"^(\w+ wrist y): (\S+)$", text, re.M)}
    # upstream wrote the amplitude (30) on the offset and phase lines
    assert value == pytest.approx({"Amplitude wrist y": 30.0,
                                   "Offset wrist y": -30.0, "Phase wrist y": 90.0})
