"""Tests of tools/targets.py and the shipped default target set."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_report as br  # noqa: E402
import targets as tg  # noqa: E402


def test_default_loads_and_is_assumed():
    ts = tg.load("default")
    assert set(ts["parameters"]) == set(tg.REQUIRED)
    assert all(p["status"] == "assumed" for p in ts["parameters"].values())
    assert tg.value(ts, "board_quantity") > 0


def test_default_resolution_consistent_with_bandwidth():
    ts = tg.load("default")
    res = 299792458 / (2 * tg.value(ts, "chirp_bandwidth_hz"))
    assert tg.value(ts, "range_resolution_m") == pytest.approx(res, rel=0.05)


def test_unknown_set():
    with pytest.raises(tg.TargetError, match="not found"):
        tg.load("nope")
    with pytest.raises(tg.TargetError):
        tg.load("../x")


def test_schema_errors():
    d = copy.deepcopy(tg.load("default"))
    del d["parameters"]["sample_rate_hz"]
    d["parameters"]["max_range_m"]["value"] = "far"
    d["parameters"]["chirp_duration_s"]["status"] = "guess"
    d["parameters"]["tx_power_dbm"]["unit"] = "W"
    d["parameters"]["extra"] = {}
    msg = " | ".join(tg.validate(d))
    for frag in ("missing parameter sample_rate_hz", "max_range_m.value must be a number",
                 "chirp_duration_s.status", "tx_power_dbm.unit", "unknown parameter extra"):
        assert frag in msg


def test_negative_values():
    d = copy.deepcopy(tg.load("default"))
    d["parameters"]["antenna_gain_dbi"]["value"] = -3
    assert tg.validate(d) == []
    d["parameters"]["max_range_m"]["value"] = -1
    assert any("positive" in m for m in tg.validate(d))


def test_report_prints_target_set(tmp_path, capsys):
    d = tmp_path / "98_t"
    d.mkdir()
    (d / "figures.py").write_text("")
    (d / "deck.yaml").write_text("slides:\n  - {layout: bullet, title: T, bullets: [x]}\n")
    (d / "writeup.md").write_text("# x\n")
    assert br.main([str(d), "--check"]) == 0
    assert "target set 'default'" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        br.main([str(d), "--check", "--targets", "nope"])
