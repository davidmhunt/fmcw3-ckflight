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
    assert set(ts["design"]) == set(tg.DESIGN)
    assert set(ts["performance"]) == set(tg.PERFORMANCE)
    assert all(p["status"] == "assumed" for p in tg.params(ts).values())
    assert tg.value(ts, "board_quantity") > 0
    assert tg.value(ts, "freq_min_ghz") == 5.725 and tg.value(ts, "freq_max_ghz") == 5.875


def test_range_resolution_is_derived_not_set():
    ts = tg.load("default")
    assert "range_resolution_m" not in tg.params(ts)
    assert tg.range_resolution_m(ts) == pytest.approx(299792458 / (2 * 150e6))
    d = copy.deepcopy(ts)
    d["design"]["range_resolution_m"] = {"value": 1, "unit": "m", "status": "set"}
    assert any("unknown parameter range_resolution_m" in m for m in tg.validate(d))


def test_bandwidth_must_fit_band():
    d = copy.deepcopy(tg.load("default"))
    d["design"]["chirp_bandwidth_hz"]["value"] = 150e6
    assert tg.validate(d) == []
    d["design"]["chirp_bandwidth_hz"]["value"] = 200e6
    assert any("exceeds freq_max_ghz - freq_min_ghz" in m for m in tg.validate(d))
    d["design"]["chirp_bandwidth_hz"]["value"] = 100e6
    d["design"]["freq_min_ghz"]["value"] = 5.9
    assert any("must be below freq_max_ghz" in m for m in tg.validate(d))


def test_table_prints_design_first_then_performance_then_derived():
    r = tg.rows(tg.load("default"))
    groups = [row[0] for row in r[1:]]
    assert groups == ["design"] * 7 + ["performance"] * 3 + ["derived"]
    assert r[-1][1] == "range_resolution_m" and r[-1][4].startswith("derived")
    md = tg.format_table(tg.load("default"))
    assert md.index("freq_min_ghz") < md.index("max_range_m") < md.index("range_resolution_m")


def test_performance_is_optional():
    d = copy.deepcopy(tg.load("default"))
    del d["performance"]
    assert tg.validate(d) == []
    del d["design"]
    assert any("missing 'design' group" in m for m in tg.validate(d))


def test_unknown_set():
    with pytest.raises(tg.TargetError, match="not found"):
        tg.load("nope")
    with pytest.raises(tg.TargetError):
        tg.load("../x")


def test_schema_errors():
    d = copy.deepcopy(tg.load("default"))
    del d["design"]["sample_rate_hz"]
    d["performance"]["max_range_m"]["value"] = "far"
    d["performance"]["chirp_duration_s"]["status"] = "guess"
    d["design"]["tx_power_dbm"]["unit"] = "W"
    d["performance"]["extra"] = {}
    msg = " | ".join(tg.validate(d))
    for frag in ("missing parameter sample_rate_hz", "max_range_m.value must be a number",
                 "chirp_duration_s.status", "tx_power_dbm.unit", "unknown parameter extra"):
        assert frag in msg


def test_negative_values():
    d = copy.deepcopy(tg.load("default"))
    d["performance"]["antenna_gain_dbi"]["value"] = -3
    assert tg.validate(d) == []
    d["performance"]["max_range_m"]["value"] = -1
    assert any("positive" in m for m in tg.validate(d))


def test_report_prints_target_set(tmp_path, capsys):
    d = tmp_path / "98_t"
    d.mkdir()
    (d / "figures.py").write_text("")
    (d / "deck.yaml").write_text("slides:\n  - {layout: title, title: T}\n  - {layout: bullet, title: T, bullets: [x]}\n")
    (d / "writeup.md").write_text("# x\n")
    assert br.main([str(d), "--check"]) == 0
    assert "target set 'default'" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        br.main([str(d), "--check", "--targets", "nope"])


def test_deck_gets_targets_slide_after_title(tmp_path):
    ts = tg.load("default")
    slides = [{"layout": "title", "title": "T"}, {"layout": "bullet", "title": "B"}]
    out = br.with_targets_slide(slides, tmp_path, ts)
    assert [s["layout"] for s in out] == ["title", "table", "table", "bullet"]
    assert out[1]["title"].startswith("Design targets") and out[2]["title"].startswith("Performance")
    design = (tmp_path / "targets_design.csv").read_text().splitlines()
    assert design[1].startswith("design,freq_min_ghz") and design[-1].startswith("derived,range_resolution_m")
    assert "max_range_m" in (tmp_path / "targets_performance.csv").read_text()
    assert br.check_deck(out, tmp_path) == []
