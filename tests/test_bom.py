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


def test_load_decisions_missing_file(tmp_path):
    assert bom.load_decisions(tmp_path / "none.csv") == {}


def test_write_csv(tmp_path):
    out = tmp_path / "o" / "bom.csv"
    bom.write_csv(groups(), out)
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["refs"] == "C1;C2" and rows[0]["qty"] == "2"


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
