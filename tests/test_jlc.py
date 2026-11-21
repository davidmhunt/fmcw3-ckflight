"""parts/check_jlc.py against a tiny database built in the plugin's schema: no network, no cache.

The fixture rows are shaped like rows of bouni/kicad-jlcpcb-tools' parts-fts5.db (FTS5 table
`parts`, trigram tokenizer). They are invented, not copied from the real database.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
import check_jlc as jlc  # noqa: E402

CAP = "Multilayer Ceramic Capacitors MLCC - SMD/SMT"
RES = "Chip Resistor - Surface Mount"
IND = "Inductors (SMD)"
FERR = "Ferrite Beads"
PRICE = "1-199:0.0100,200-:0.0050"

#      LCSC     cat  mpn                pkg   mfr    lib         desc                              stock
ROWS = [
    ("C100", CAP, "GRM155R71C104KA88D", "0402", "Murata", "Extended", "100nF 16V X7R ±10%", "5000"),
    ("C101", CAP, "CC0402KRX7R7BB104", "0402", "Yageo", "Basic", "100nF 16V X7R ±10%", "900000"),
    ("C102", CAP, "CL05A105KA5NQNC", "0402", "Samsung", "Basic", "1uF 25V X5R ±10%", "700000"),
    ("C103", CAP, "CL10A105KA8NNNC", "0603", "Samsung", "Basic", "1uF 25V X5R ±10%", "800000"),
    ("C200", RES, "0402WGF4990TCE", "0402", "UNI-ROYAL", "Basic",
     "-55℃~+155℃ 49.9Ω 50V 62.5mW Thick Film Resistor ±1%", "1000000"),
    ("C201", RES, "0402WGF4992TCE", "0402", "UNI-ROYAL", "Preferred",
     "-55℃~+155℃ 49.9kΩ 50V 62.5mW Thick Film Resistor ±1%", "700000"),
    ("C202", RES, "0402WGF0000TCE", "0402", "UNI-ROYAL", "Basic",
     "-55℃~+155℃ 0Ω 50V 62.5mW Thick Film Resistor", "2000000"),
    ("C300", IND, "LQW15AN9N9J80D", "0402", "Murata", "Extended", "9.9nH 800mA 150mΩ ±5%", "3"),
    ("C301", IND, "LQW15AN9N9J80Z", "0402", "Murata", "Extended", "9.9nH 800mA 150mΩ ±5%", "9000"),
    ("C302", IND, "XYZ0402-2R2", "0402", "Acme", "Extended", "2.2uH 100mΩ", "5000"),
    ("C400", FERR, "BLM18PG181SN1D", "0603", "Murata", "Extended", "180Ω@100MHz 1.5A", "126463"),
]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("jlc") / "parts.db"
    con = sqlite3.connect(path)
    con.execute("""CREATE VIRTUAL TABLE parts USING fts5 ('LCSC Part', 'First Category',
        'Second Category', 'MFR.Part', 'Package', 'Solder Joint' UNINDEXED, 'Manufacturer',
        'Library Type', 'Description', 'Datasheet' UNINDEXED, 'Price' UNINDEXED,
        'Stock' UNINDEXED, tokenize="trigram")""")
    for lcsc, cat, mpn, pkg, mfr, lib, desc, stock in ROWS:
        con.execute("INSERT INTO parts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (lcsc, "Cat", cat, mpn, pkg, 2, mfr, lib, desc, "", PRICE, stock))
    con.commit()
    con.close()
    return jlc.Db(path)


def group(cls, refs=("R1",), value="", fp="SMD_0402", mpn="", lcsc=""):
    return {"class": cls, "refs": list(refs), "Value": value, "Footprint": fp, "MPN": mpn,
            "LCSC": lcsc, "DigiKey PN": "", "Manufacturer": "", "DNP": cls == "dnp",
            "qty": len(refs)}


def test_parse_price_and_breaks():
    breaks = jlc.parse_price("1-199:0.025,200-599:0.019,20000-:0.014")
    assert breaks == [(1, 0.025), (200, 0.019), (20000, 0.014)]
    assert jlc.price_at(breaks, 1) == 0.025
    assert jlc.price_at(breaks, 250) == 0.019
    assert jlc.price_at(breaks, 10**6) == 0.014
    assert jlc.price_at([], 5) is None
    assert jlc.parse_price("") == []


def test_exact_mpn(db):
    r = jlc.check_group(db, group("mpn", ["L1"], mpn="LQW15AN9N9J80D"), 6)
    assert (r["jlc_match"], r["jlc_lcsc"], r["jlc_library"]) == ("exact", "C300", "Extended")
    assert r["jlc_status"] == "Low stock" and r["jlc_stock"] == 3
    assert r["jlc_unit_price"] == 0.01


def test_exact_mpn_ignores_case_and_dashes(db):
    r = jlc.check_group(db, group("mpn", ["L1"], mpn="lqw15an9n9j80d"), 1)
    assert r["jlc_match"] == "exact" and r["jlc_lcsc"] == "C300"


def test_lcsc_number_wins(db):
    r = jlc.check_group(db, group("mpn", ["C1"], mpn="NOPE", lcsc="c101"), 1)
    assert (r["jlc_match"], r["jlc_lcsc"]) == ("exact", "C101")


def test_suffix_variant_needs_review(db):
    r = jlc.check_group(db, group("mpn", ["L1"], mpn="LQW15AN9N9J80"), 1)
    assert r["jlc_match"] == "review"
    assert r["jlc_lcsc"] == "C301"  # in stock for the need, over the 3-in-stock one


def test_unknown_mpn_is_no_result(db):
    r = jlc.check_group(db, group("mpn", ["U1"], mpn="NOT-A-PART-123"), 1)
    assert r["jlc_status"] == "No-result" and r["jlc_match"] == "" and r["jlc_stock"] == 0


def test_generic_cap_prefers_basic(db):
    r = jlc.check_group(db, group("generic", ["C1", "C2"], "100n", "SMD_0402"), 6)
    assert (r["jlc_match"], r["jlc_lcsc"], r["jlc_library"]) == ("package", "C101", "Basic")
    assert r["jlc_status"] == "Available"


def test_generic_package_is_respected(db):
    r = jlc.check_group(db, group("generic", ["C3"], "1u", "SMD_0603"), 3)
    assert r["jlc_lcsc"] == "C103"


def test_generic_resistor_unit_scale(db):
    ohm = jlc.check_group(db, group("generic", ["R1"], "49.9", "SMD_0402"), 3)
    kohm = jlc.check_group(db, group("generic", ["R2"], "49.9k", "SMD_0402"), 3)
    assert (ohm["jlc_lcsc"], kohm["jlc_lcsc"]) == ("C200", "C201")


def test_generic_zero_ohm_short_term(db):
    """'0' is under the trigram minimum: the package/category slice is filtered in Python."""
    r = jlc.check_group(db, group("generic", ["R7"], "0", "SMD_0402"), 3)
    assert r["jlc_lcsc"] == "C202"


def test_generic_inductor_unit_is_h_not_ohm(db):
    r = jlc.check_group(db, group("generic", ["L12"], "2.2u", "SMD_0402"), 3)
    assert r["jlc_lcsc"] == "C302"


def test_generic_with_mpn_as_value_needs_review(db):
    r = jlc.check_group(db, group("generic", ["FB1"], "BLM18PG181SN1D", "SMD_0603"), 3)
    assert (r["jlc_match"], r["jlc_lcsc"]) == ("review", "C400")


def test_generic_no_such_value(db):
    r = jlc.check_group(db, group("generic", ["C9"], "3.3p", "SMD_0402"), 3)
    assert r["jlc_status"] == "No-result"


def test_dnp_and_nopart_are_not_applicable(db):
    for cls in ("dnp", "nopart"):
        r = jlc.check_group(db, group(cls, ["U1"], "XC7A100T"), 3)
        assert r["jlc_status"] == "n/a" and r["jlc_lcsc"] == ""


def test_result_has_every_column(db):
    r = jlc.check_group(db, group("generic", ["C1"], "100n", "SMD_0402"), 1)
    assert set(r) == set(jlc.RESULT_COLS)


def test_offline_without_cache_says_what_to_do(tmp_path):
    with pytest.raises(jlc.JlcError, match="without --offline"):
        jlc.ensure_db(tmp_path, offline=True)
