"""Tests of the baseline comparison logic embedded in checks/run_checks.sh.

The script runs kicad-cli, then feeds erc.json/drc.json to an inline Python program.
Here that program is extracted from the script and run on fixture JSON, so no KiCad
is needed.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "checks" / "run_checks.sh"


def _program() -> str:
    m = re.search(r"<<'P'\n(.*?)\nP\n", SCRIPT.read_text(), re.S)
    assert m, "inline python program not found in run_checks.sh"
    return m.group(1)


def _viol(severity, typ="t"):
    return {"severity": severity, "type": typ}


def _run(tmp_path, base_erc, base_drc, erc_errors, drc_errors, unconnected=0, parity=0):
    tmp = tmp_path / "tmp"
    chk = tmp_path / "chk"
    tmp.mkdir()
    chk.mkdir()
    (tmp / "erc.json").write_text(json.dumps(
        {"sheets": [{"violations": [_viol("error")] * erc_errors + [_viol("warning")] * 3}]}))
    (tmp / "drc.json").write_text(json.dumps(
        {"violations": [_viol("error")] * drc_errors + [_viol("warning")] * 5,
         "unconnected_items": [{}] * unconnected,
         "schematic_parity": [{}] * parity}))
    (chk / "baseline.json").write_text(json.dumps(
        {"erc": {"errors": base_erc}, "drc": {"errors": base_drc}}))
    return subprocess.run([sys.executable, "-c", _program(), str(tmp), str(chk), ""],
                          capture_output=True, text=True)


def test_equal_passes(tmp_path):
    r = _run(tmp_path, 4, 7, 4, 7)
    assert r.returncode == 0, r.stdout
    assert r.stdout.strip().endswith("PASS")


def test_more_errors_fails(tmp_path):
    r = _run(tmp_path, 4, 7, 5, 7)
    assert r.returncode == 1
    assert "ERC errors 5 > 4" in r.stdout


def test_more_drc_errors_fails(tmp_path):
    r = _run(tmp_path, 4, 7, 4, 8)
    assert r.returncode == 1
    assert "DRC errors 8 > 7" in r.stdout


def test_fewer_errors_passes(tmp_path):
    r = _run(tmp_path, 4, 7, 2, 3)
    assert r.returncode == 0, r.stdout
    assert "PASS" in r.stdout


@pytest.mark.parametrize("field", ["unconnected", "parity"])
def test_unconnected_or_parity_fails_even_at_baseline(tmp_path, field):
    r = _run(tmp_path, 4, 7, 4, 7, **{field: 2})
    assert r.returncode == 1
    assert "FAIL" in r.stdout
