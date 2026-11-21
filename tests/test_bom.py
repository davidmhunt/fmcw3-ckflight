"""parts/bom.py: grouping, classification, decisions merge (no kicad-cli needed except one)."""
import csv
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
import bom  # noqa: E402

RAW = '''"Reference","Value","Footprint","DNP","EXCLUDE_FROM_BOM","MPN","Manufacturer","LCSC","DigiKey PN"
"C1","100n","Footprints:SMD_0402","","","","","",""
"C2","100n","Footprints:SMD_0402","","","","","",""
"C3","100n","Footprints:SMD_0402","","","GRM155","Murata","",""
"C4","DNP","Footprints:SMD_0402","","","","","",""
"R1","10k","Footprints:SMD_0402","DNP","","","","",""
"U1","ADF4159","Footprints:LFCSP","","","","","",""
"U2","LM","Footprints:SOT","","","LM1","TI","",""
"J1","USB","Footprints:USB","","Excluded","","","",""
'''


def groups(dec=None):
    return bom.group_rows(bom.merge_decisions(bom.parse_export(RAW), dec or {}))


def by_ref(gs, ref):
    return next(g for g in gs if ref in g["refs"])


def test_grouping_splits_on_part_fields():
    gs = groups()
    assert by_ref(gs, "C1")["refs"] == ["C1", "C2"]
    assert by_ref(gs, "C3")["refs"] == ["C3"]
    assert sum(g["qty"] for g in gs) == 8


def test_classes():
    gs = groups()
    assert by_ref(gs, "C1")["class"] == "generic"
    assert by_ref(gs, "C3")["class"] == "mpn"
    assert by_ref(gs, "C4")["class"] == "dnp"      # value DNP
    assert by_ref(gs, "R1")["class"] == "dnp"      # DNP attribute
    assert by_ref(gs, "J1")["class"] == "dnp"      # excluded from BOM
    assert by_ref(gs, "U1")["class"] == "nopart"
    assert by_ref(gs, "U2")["class"] == "mpn"


def test_decisions_fill_but_do_not_override():
    dec = {"U1": {"MPN": "ADF4159CCPZ"}, "U2": {"MPN": "OTHER"}, "C1": {"DNP": "yes"}}
    gs = groups(dec)
    assert by_ref(gs, "U1")["class"] == "mpn"
    assert by_ref(gs, "U2")["MPN"] == "LM1"
    assert by_ref(gs, "C1")["class"] == "dnp"
    assert by_ref(gs, "C2")["class"] == "generic"


def test_spec_fields_reach_groups_and_parametric_query():
    dec = {"C1": {"Tolerance": "10%", "Voltage": "16V", "Dielectric": "X7R"},
           "C2": {"Tolerance": "10%", "Voltage": "16V", "Dielectric": "X7R"}}
    g = by_ref(groups(dec), "C1")
    assert g["refs"] == ["C1", "C2"] and g["Voltage"] == "16V"
    import check_digikey as dk
    q, spec = dk.parametric_query(g)
    assert spec["dielectric"] == "X7R" and "16V" in q and "10%" in q
    assert by_ref(groups(), "C1")["Tolerance"] == ""


def test_load_decisions_missing_file(tmp_path):
    assert bom.load_decisions(tmp_path / "none.csv") == {}


def test_write_csv(tmp_path):
    out = tmp_path / "o" / "bom.csv"
    bom.write_csv(groups(), out)
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["refs"] == "C1;C2" and rows[0]["qty"] == "2"


# ---- quantity scaling, verdicts, availability rows (no network: results are plain dicts)

def test_need_qty_scales_with_boards_and_spares():
    assert bom.need_qty(4, 1) == 4
    assert bom.need_qty(4, 5) == 20
    assert bom.need_qty(4, 5, spares=2) == 22
    assert bom.need_qty(1, 10, spares=3) == 13


def test_board_count_override_and_validation():
    assert bom.board_count(override=7) == 7
    with pytest.raises(SystemExit):
        bom.board_count(override=0)
    assert bom.board_count("default") >= 1   # board_quantity from analysis/targets/default.yaml


def g_(cls="mpn", value="x", fp="SMD_0402"):
    return {"class": cls, "Value": value, "Footprint": fp}


JLC_OK = {"jlc_status": "Available", "jlc_match": "exact", "jlc_library": "Basic",
          "jlc_lcsc": "C1"}
DK_OK = {"dk_status": "Active", "dk_stock": 100, "dk_pn": "X-ND"}


def test_verdict_not_fitted_and_no_part():
    assert bom.verdict(g_("dnp"), JLC_OK, DK_OK, 1)[0] == "not fitted"
    assert bom.verdict(g_("nopart", "RF_via", "Footprints:RF_via"), {}, {}, 1)[0] == "no part"
    v, why = bom.verdict(g_("nopart", "ADF"), {}, {}, 1)
    assert v == "unresolved" and "no MPN" in why


def test_verdict_jlc_assemble_exact_or_package_only():
    assert bom.verdict(g_(), JLC_OK, DK_OK, 5)[0] == "JLC assemble"
    assert bom.verdict(g_(), {**JLC_OK, "jlc_match": "package"}, {}, 5)[0] == "JLC assemble"
    # a near match needs review: falls through to DigiKey
    near = {**JLC_OK, "jlc_match": "review"}
    assert bom.verdict(g_(), near, DK_OK, 5)[0] == "consign from DigiKey"


def test_verdict_digikey_stock_must_cover_need():
    low = {"jlc_status": "Low stock"}
    assert bom.verdict(g_(), low, {**DK_OK, "dk_stock": 20}, 20)[0] == "consign from DigiKey"
    v, why = bom.verdict(g_(), low, {**DK_OK, "dk_stock": 19}, 20)
    assert v == "unresolved" and "JLC Low stock" in why
    sug = {"dk_status": "Suggested", "dk_stock": 50}
    assert bom.verdict(g_("generic"), {"jlc_status": "No-result"}, sug, 5)[0] == "consign from DigiKey"
    obs = {"dk_status": "Obsolete", "dk_stock": 500}
    assert bom.verdict(g_(), {"jlc_status": "No-result"}, obs, 1)[0] == "unresolved"


def test_verdict_through_hole_is_hand_solder():
    th = g_("mpn", "hdr", "PinHeader_1x04")
    assert bom.verdict(th, {"jlc_status": "No-result"}, DK_OK, 1)[0] == "hand-solder"


def test_verdict_unresolved_reasons():
    v, why = bom.verdict(g_(), {"jlc_status": "Not-checked"}, {}, 1)
    assert v == "unresolved" and "JLC not checked" in why and "DigiKey not checked" in why
    v, why = bom.verdict(g_(), {"jlc_match": "review", "jlc_mpn": "ABC"}, {}, 1)
    assert "near match ABC needs review" in why


def test_verdict_depends_on_boards():
    """Same stock, more boards: the line stops being coverable from DigiKey."""
    jlc = {"jlc_status": "No-result"}
    dk = {"dk_status": "Active", "dk_stock": 40}
    assert bom.verdict(g_(), jlc, dk, bom.need_qty(2, 5))[0] == "consign from DigiKey"
    assert bom.verdict(g_(), jlc, dk, bom.need_qty(2, 25))[0] == "unresolved"


def test_availability_rows_offline_and_need():
    gs = groups()
    rows = bom.availability_rows(gs, boards=5, spares=1, db=None, client=None)
    c1 = next(r for r in rows if "C1" in r["refs"].split(";"))
    assert c1["qty"] == 2 and c1["need"] == 11 and c1["verdict"] == "unresolved"
    assert c1["jlc_status"] == "Not-checked" and c1["dk_status"] == "Not-checked"
    assert next(r for r in rows if r["refs"] == "R1")["verdict"] == "not fitted"
    assert set(bom.availability_cols()) <= set(c1)
    assert "not fitted 3" in bom.verdict_summary(rows)   # C4, R1, J1


def test_missing_mpn_and_jlc_files(tmp_path):
    gs = groups()
    # generic passives (C1/C2) have no MPN either; C3, U2 have one, C4/R1/J1 are not fitted
    assert [g["refs"] for g in bom.missing_mpn(gs)] == [["C1", "C2"], ["U1"]]
    rows = [{"verdict": "JLC assemble", "refs": "C1;C2", "value": "100n", "footprint": "F",
             "LCSC": "", "jlc_lcsc": "C9"},
            {"verdict": "hand-solder", "refs": "J2", "value": "h", "footprint": "F", "LCSC": "",
             "jlc_lcsc": ""},
            {"verdict": "unresolved", "refs": "U1", "value": "u", "footprint": "F", "LCSC": "",
             "jlc_lcsc": "C5"}]
    out = tmp_path / "jlc" / "bom.csv"
    bom.write_jlc_bom(rows, out)
    got = list(csv.reader(out.open()))
    assert got[0] == ["Comment", "Designator", "Footprint", "LCSC Part #"]
    assert got[1:] == [["100n", "C1, C2", "F", "C9"], ["u", "U1", "F", ""]]


def test_cpl_rows_filters_and_sorts():
    pos = ("Ref,Val,Package,PosX,PosY,Rot,Side\n"
           "C10,a,p,1.0,2.0,90,top\nC2,a,p,3.0,4.0,0,bottom\nR1,a,p,5,6,0,top\n")
    rows = bom.cpl_rows(pos, {"C10", "C2"})
    assert rows == [["C2", "3.0", "4.0", "bottom", "0"], ["C10", "1.0", "2.0", "top", "90"]]


def test_cached_digikey_offline_miss_and_hit(tmp_path):
    offline = bom.CachedDigiKey(None, cache=tmp_path)
    with pytest.raises(bom.CachedDigiKey.OfflineMiss):
        offline.search("A")

    class Live:
        calls = 0

        def search(self, kw, limit):
            Live.calls += 1
            return [{"ManufacturerProductNumber": kw}]

    c = bom.CachedDigiKey(Live(), cache=tmp_path)
    assert c.search("A") == c.search("A") == [{"ManufacturerProductNumber": "A"}]
    assert Live.calls == 1
    assert offline.search("A") == [{"ManufacturerProductNumber": "A"}]   # cache serves offline


@pytest.mark.skipif(not shutil.which("kicad-cli"), reason="kicad-cli not available")
def test_matches_production_bom():
    """Group and ref counts equal the as-ordered production/bom.csv (84 groups, 370 refs)."""
    gs = bom.build(decisions=Path("/nonexistent"))
    prod = list(csv.DictReader((ROOT / "production" / "bom.csv").open(encoding="utf-8-sig")))
    assert len(prod) == 84
    assert sum(g["qty"] for g in gs) == sum(int(p["Quantity"]) for p in prod) == 370
    # One known difference: R26, R28, R31, R38 were 500 ohm when ordered and are 1k in the
    # current schematic, so the 500 group is gone and they join the 1k group (84 -> 83 groups).
    assert len(gs) == 83
    prod_refs = {frozenset(p["Designator"].split(", ")) for p in prod}
    ours = {frozenset(g["refs"]) for g in gs}
    changed = {"R26", "R28", "R31", "R38"}
    # every production group is reproduced exactly, except the 500 group and the 1k group that
    # absorbed it
    missing = prod_refs - ours
    assert frozenset(changed) in missing
    assert all(m == frozenset(changed) or m.isdisjoint(changed) is True and "R4" in m for m in missing)
    assert next(g for g in gs if "R26" in g["refs"])["Value"] == "1k"
