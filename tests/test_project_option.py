"""--project DIR: tools/project.py resolves a project directory to its files and output paths;
`kicad` stays the default; an unknown directory fails with a clear message in every tool.
No KiCad, no network: the failing runs stop before any tool does work."""
import argparse
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "parts"))
import bom  # noqa: E402
import kicad_ipc  # noqa: E402
import project  # noqa: E402


def test_default_is_kicad():
    p = project.resolve()
    assert project.DEFAULT == "kicad"
    assert p.dir == ROOT / "kicad"
    assert (p.pro, p.sch, p.pcb) == tuple(ROOT / "kicad" / f"fmcw3.kicad_{e}" for e in ("pro", "sch", "pcb"))
    assert p.parts_out == ROOT / "parts" / "out"
    assert p.baseline == ROOT / "checks" / "baseline.json"


def test_1rx_files_and_outputs():
    p = project.resolve("kicad-1rx")
    assert p.dir == ROOT / "kicad-1rx"
    assert p.sch == ROOT / "kicad-1rx" / "fmcw3_1rx.kicad_sch"
    assert p.pcb == ROOT / "kicad-1rx" / "fmcw3_1rx.kicad_pcb"
    assert p.pro.is_file() and p.sch.is_file() and p.pcb.is_file()
    assert p.parts_out == ROOT / "parts" / "out" / "1rx"
    assert p.baseline == ROOT / "checks" / "baseline-1rx.json"
    assert p.baseline.is_file()


def test_absolute_path_resolves_same():
    assert project.resolve(ROOT / "kicad-1rx") == project.resolve("kicad-1rx")


def test_unknown_directory_message():
    with pytest.raises(project.ProjectError) as e:
        project.resolve("kicad-nope")
    msg = str(e.value)
    assert "kicad-nope" in msg and "not a directory" in msg
    assert "kicad-1rx" in msg  # lists the projects that do exist


def test_directory_without_project_file(tmp_path):
    with pytest.raises(project.ProjectError, match="needs exactly one"):
        project.resolve(tmp_path)


def test_directory_missing_board(tmp_path):
    (tmp_path / "x.kicad_pro").write_text("{}")
    (tmp_path / "x.kicad_sch").write_text("")
    with pytest.raises(project.ProjectError, match="missing x.kicad_pcb"):
        project.resolve(tmp_path)


def test_resolve_or_exit():
    with pytest.raises(SystemExit) as e:
        project.resolve_or_exit("kicad-nope")
    assert "unknown project directory" in str(e.value)


def _args(*argv):
    ap = argparse.ArgumentParser()
    bom.add_project_arg(ap)
    return ap.parse_args(list(argv))


def test_parts_tools_default_and_1rx():
    assert bom.project_from(_args()).dir == ROOT / "kicad"
    p = bom.project_from(_args("--project", "kicad-1rx"))
    assert p.sch.name == "fmcw3_1rx.kicad_sch" and p.parts_out.name == "1rx"


def test_parts_tools_unknown_exits():
    with pytest.raises(SystemExit, match="unknown project directory"):
        bom.project_from(_args("--project", "kicad-nope"))


def test_kicad_ipc_project_file():
    assert kicad_ipc.project_file() == Path(kicad_ipc.DEFAULT_PROJECT)
    assert kicad_ipc.project_file("kicad-1rx") == ROOT / "kicad-1rx" / "fmcw3_1rx.kicad_pro"
    with pytest.raises(kicad_ipc.IpcError, match="unknown project directory"):
        kicad_ipc.project_file("kicad-nope")
    with pytest.raises(kicad_ipc.IpcError, match="not both"):
        kicad_ipc.project_file("kicad", "x.kicad_pro")


def _run(*cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("script", [
    "parts/bom.py", "parts/check_jlc.py", "parts/check_digikey.py", "parts/watch.py",
])
def test_parts_cli_unknown_project(script):
    r = _run(sys.executable, script, "--project", "kicad-nope")
    assert r.returncode != 0
    assert "unknown project directory" in r.stderr + r.stdout


def test_kicad_ipc_status_unknown_project():
    r = _run(sys.executable, "tools/kicad_ipc.py", "status", "--project", "kicad-nope")
    assert r.returncode == 2
    assert "unknown project directory" in r.stderr


def test_run_checks_unknown_project():
    r = _run("bash", "checks/run_checks.sh", "--project", "kicad-nope")
    assert r.returncode != 0
    assert "unknown project directory" in r.stderr
