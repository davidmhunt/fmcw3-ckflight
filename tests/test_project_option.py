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


# ---- each tool's main() uses the resolved project paths -------------------------------------

class _Stop(Exception):
    """Raised by a stub to end a main() once the path under test has been captured."""


def _capture(monkeypatch, module, name, seen):
    def stub(*args, **kw):
        seen[name] = args
        raise _Stop
    monkeypatch.setattr(module, name, stub)


def _raiser(exc):
    def f(*a, **k):
        raise exc
    return f


PROJECTS = [([], "kicad", ""), (["--project", "kicad-1rx"], "kicad-1rx", "1rx/")]


@pytest.mark.parametrize("argv, proj, sub", PROJECTS)
def test_bom_main_paths(monkeypatch, argv, proj, sub):
    want = project.resolve(proj)
    seen = {}
    _capture(monkeypatch, bom, "build", seen)
    with pytest.raises(_Stop):
        bom.main(argv)
    assert seen["build"][0] == want.sch
    seen.clear()
    monkeypatch.setattr(bom, "build", lambda sch, *a, **k: [])
    _capture(monkeypatch, bom, "write_csv", seen)
    with pytest.raises(_Stop):
        bom.main(argv)
    assert seen["write_csv"][1] == ROOT / "parts" / "out" / (sub + "bom.csv")


@pytest.mark.parametrize("argv, proj, sub", PROJECTS)
def test_bom_main_pcb_for_cpl(monkeypatch, argv, proj, sub):
    """The CPL is exported from the project's board, not always kicad/'s."""
    import check_digikey
    import check_jlc
    seen = {}
    monkeypatch.setattr(bom, "build", lambda *a, **k: [])
    monkeypatch.setattr(bom, "write_csv", lambda *a, **k: None)
    monkeypatch.setattr(check_jlc, "ensure_db", _raiser(check_jlc.JlcError("x")))
    monkeypatch.setattr(check_digikey.Client, "from_env",
                        classmethod(lambda cls: _raiser(check_digikey.DigiKeyError("x"))()))
    monkeypatch.setattr(bom, "availability_rows", lambda *a, **k: [])
    monkeypatch.setattr(bom, "write_availability", lambda *a, **k: None)
    monkeypatch.setattr(bom, "write_jlc_bom", lambda *a, **k: None)
    monkeypatch.setattr(bom, "jlc_assembled", lambda rows: [])
    _capture(monkeypatch, bom, "export_pos", seen)
    with pytest.raises(_Stop):
        bom.main(argv + ["--offline"])
    assert seen["export_pos"][0] == project.resolve(proj).pcb


@pytest.mark.parametrize("argv, proj, sub", PROJECTS)
def test_watch_main_out_path(monkeypatch, argv, proj, sub):
    import check_jlc
    import watch
    seen = {}
    monkeypatch.setattr(check_jlc, "ensure_db", lambda *a, **k: Path("x.db"))
    monkeypatch.setattr(check_jlc, "Db", lambda p: None)
    monkeypatch.setattr(watch, "make_dk", lambda offline: None)
    _capture(monkeypatch, watch, "write_out", seen)
    with pytest.raises(_Stop):
        watch.main(argv)
    assert seen["write_out"][1] == ROOT / "parts" / "out" / (sub + "watch.csv")


@pytest.mark.parametrize("argv, proj, sub", PROJECTS)
def test_check_jlc_main_schematic(monkeypatch, argv, proj, sub):
    import check_jlc
    seen = {}
    monkeypatch.setattr(check_jlc, "ensure_db", lambda *a, **k: Path("x.db"))
    monkeypatch.setattr(check_jlc, "Db", lambda p: None)
    _capture(monkeypatch, bom, "build", seen)
    with pytest.raises(_Stop):
        check_jlc.main(argv)
    assert seen["build"][0] == project.resolve(proj).sch


@pytest.mark.parametrize("argv, proj, sub", PROJECTS)
def test_check_digikey_main_schematic(monkeypatch, argv, proj, sub):
    import check_digikey
    seen = {}
    monkeypatch.setattr(check_digikey.Client, "from_env", classmethod(lambda cls: object()))
    _capture(monkeypatch, bom, "build", seen)
    with pytest.raises(_Stop):
        check_digikey.main(argv)
    assert seen["build"][0] == project.resolve(proj).sch


@pytest.mark.parametrize("proj, suffix", [("kicad", ""), ("kicad-1rx", "-1rx")])
def test_run_checks_uses_project_files_and_baseline(tmp_path, proj, suffix):
    """run_checks.sh runs kicad-cli in the project directory on its own files and compares
    against checks/baseline<suffix>.json. A stub kicad-cli reports no violations."""
    import json
    import os
    p = project.resolve(proj)
    stub = tmp_path / "kicad-cli"
    stub.write_text(
        '#!/usr/bin/env bash\n'
        'echo "$PWD $*" >> "$STUB_LOG"\n'
        'out=""; while [ $# -gt 0 ]; do [ "$1" = -o ] && out="$2"; shift; done\n'
        'case "$out" in *erc.json) echo \'{"sheets": []}\' > "$out";;\n'
        '  *) echo \'{"violations": [], "unconnected_items": [], "schematic_parity": []}\' > "$out";; esac\n')
    stub.chmod(0o755)
    log = tmp_path / "log"
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "STUB_LOG": str(log)}
    r = subprocess.run(["bash", "checks/run_checks.sh", "--project", proj], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=120)
    base = json.loads((ROOT / "checks" / f"baseline{suffix}.json").read_text())
    assert f"ERC errors 0 (baseline {base['erc']['errors']})" in r.stdout, r.stdout + r.stderr
    assert f"DRC errors 0 (baseline {base['drc']['errors']})" in r.stdout
    lines = log.read_text().splitlines()
    assert len(lines) == 2
    assert all(l.startswith(f"{p.dir} ") for l in lines)
    assert lines[0].endswith(p.sch.name) and lines[1].endswith(p.pcb.name)
