"""rx1-02 step 5: JLC stock lines and options (committed sim/stock_lines.json and the check maths)."""
import importlib.util
import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
JSON = ROOT / "analysis" / "11_board_1rx" / "sim" / "stock_lines.json"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "stock_lines", ROOT / "analysis" / "11_board_1rx" / "stock_lines.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def res():
    return json.loads(JSON.read_text())


def test_every_failing_line_has_a_jlc_stocked_option(res):
    for key, ent in res["options"].items():
        if ent["line_status"] == "fail":
            assert any(o["jlc_ok"] for o in ent["options"]), key
            assert res["layout"]["by_line"][key] != "no JLC-stocked option"


def test_failing_lines_are_the_known_ones_plus_the_unresolved(res):
    fail = {ln["refs"][0] for ln in res["lines"] if ln["status"] == "fail"}
    assert {"U30", "U26", "U45", "U21", "P1", "L5"} <= fail          # par-09 list
    assert {"U3", "U12", "D1", "CON2", "J2"} <= fail                 # lines without a part number
    assert "U29" in {ln["refs"][0] for ln in res["lines"] if ln["status"] == "thin"}
    assert "P2" not in sum((ln["refs"] for ln in res["lines"]), [])  # RX2 is not fitted
    assert "U28" not in sum((ln["refs"] for ln in res["lines"]), [])


def test_every_cited_manifest_id_exists(res):
    ids = {e["id"] for e in yaml.safe_load((ROOT / "datasheets" / "manifest.yaml").read_text())["entries"]}
    for ent in res["options"].values():
        for o in ent["options"]:
            for cite in o["cites"]:
                assert cite[0] in ids, cite


def test_layout_count_matches_the_options(res):
    lay = res["layout"]
    assert lay["footprint_lines"] == ["CON2", "J2", "L5", "P1", "U26", "U45"]
    assert lay["design_lines"] == ["U21"]
    assert lay["layout_refs"] == 11      # CON2 1, J2 1, L5-L7 3, P1 U15 2, U26 U27 2, U45 1, U21 1


def test_inductor_limit(res):
    row = {r["option"].split()[0]: r for r in res["inductor_check"]}
    assert row["APS1040M330A"]["ok_vs_limit_typ"] and not row["APS1040M330A"]["ok_vs_limit_max"]
    for name in ("SRR6040A-330M", "SRR6038-330Y", "CDRH6D28NP-330NC"):
        assert not row[name]["ok_vs_full_load"]
    assert not any(r["ok_vs_limit_max"] for r in res["inductor_check"])


def test_divider_hits_10_volts(mod):
    for vref in (1.24, 1.242):
        best = mod.divider(vref)[0]
        assert abs(best["vout"] - 10.0) < 0.06
    assert mod.ohm_text(1.15e6) == "1.15M" and mod.ohm_text(162e3) == "162k"


def test_e96_values_are_a_decade_series(mod):
    vals = mod.e96_values(100e3, 999e3)
    assert len(vals) == 96 and vals[0] == 100e3 and 715e3 in vals
