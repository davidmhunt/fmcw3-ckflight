"""parts/watch.py on a tiny JLC database in the plugin's schema and fake DigiKey answers:
no network, no cache. Fixture rows are invented."""
import csv
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
import check_jlc as jlc  # noqa: E402
import watch  # noqa: E402

PRICE = "1-9:10.0,10-:8.0"
#      LCSC     mpn                 lib         stock
ROWS = [
    ("C1", "LTC2292IUP#PBF", "Extended", "0"),
    ("C2", "LTC2297IUP#PBF", "Extended", "12"),
    ("C3", "LTC2298IUP#PBF", "Extended", "2"),
]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("jlc") / "parts.db"
    con = sqlite3.connect(path)
    con.execute("""CREATE VIRTUAL TABLE parts USING fts5 ('LCSC Part', 'First Category',
        'Second Category', 'MFR.Part', 'Package', 'Solder Joint' UNINDEXED, 'Manufacturer',
        'Library Type', 'Description', 'Datasheet' UNINDEXED, 'Price' UNINDEXED,
        'Stock' UNINDEXED, tokenize="trigram")""")
    for lcsc, mpn, lib, stock in ROWS:
        con.execute("INSERT INTO parts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (lcsc, "ICs", "Analog to Digital Converters", mpn, "QFN-64", 2, "ADI", lib,
                     "ADC", "", PRICE, stock))
    con.commit()
    con.close()
    return jlc.Db(path)


class FakeDk:
    """Stands in for the DigiKey search client: {keywords: [product]}."""

    def __init__(self, answers):
        self.answers = answers

    def search(self, keywords, limit=10):
        if keywords not in self.answers:
            raise RuntimeError(f"no cached DigiKey answer for {keywords!r}")
        return self.answers[keywords]


def product(mpn, stock, status="Active", price=9.5):
    return {"ManufacturerProductNumber": mpn, "QuantityAvailable": stock,
            "ProductStatus": {"Status": status},
            "ProductVariations": [{"DigiKeyProductNumber": "X-ND",
                                   "PackageType": {"Name": "Cut Tape (CT)"},
                                   "StandardPricing": [{"BreakQuantity": 1, "UnitPrice": price}]}]}


def row(**kw):
    r = {"mpn": "LTC2297IUP#PBF", "refdes": "U8", "qty_per_board": "1", "role": "substitute",
         "jlc_lcsc": "", "why_watched": "w", "drop_in": "yes", "evidence_id": "ds",
         "evidence_page": "2;5", "note": ""}
    r.update(kw)
    return r


def test_jlc_stock_covers_need(db):
    res = watch.evaluate(row(), db, FakeDk({"LTC2297IUP#PBF": [product("LTC2297IUP#PBF", 40)]}), 3)
    assert res["need"] == 3 and res["jlc_stock"] == 12 and res["jlc_library"] == "Extended"
    assert res["jlc_can_place"] == "yes"
    assert res["dk_stock"] == 40 and res["dk_lifecycle"] == "Active" and res["dk_unit_price"] == 9.5


def test_stock_below_need_is_not_placeable(db):
    res = watch.evaluate(row(mpn="LTC2298IUP#PBF"), db, None, 3)  # stock 2 < need 3
    assert res["jlc_stock"] == 2 and res["jlc_can_place"] == "no"
    assert watch.evaluate(row(mpn="LTC2298IUP#PBF"), db, None, 2)["jlc_can_place"] == "yes"


def test_stock_zero_and_unknown_part(db):
    assert watch.evaluate(row(mpn="LTC2292IUP#PBF"), db, None, 3)["jlc_can_place"] == "no"
    res = watch.evaluate(row(mpn="NOSUCHPART123"), db, None, 3)
    assert res["jlc_status"] == "No-result" and res["jlc_can_place"] == "no"


def test_qty_per_board_scales_need(db):
    res = watch.evaluate(row(qty_per_board="3"), db, None, 3)  # need 9 > stock 12? no: 9 <= 12
    assert res["need"] == 9 and res["jlc_can_place"] == "yes"
    assert watch.evaluate(row(qty_per_board="5"), db, None, 3)["jlc_can_place"] == "no"  # 15


def test_near_match_never_places(db):
    # LTC2297IUP is only a prefix of the stocked MPN: a review match, not exact
    res = watch.evaluate(row(mpn="LTC2297IUP"), db, None, 1)
    assert res["jlc_match"] == "review" and res["jlc_can_place"] == "no"


def test_digikey_missing_answer_is_not_cached(db):
    res = watch.evaluate(row(), db, FakeDk({}), 3)
    assert res["dk_status"] == "Not-cached" and res["jlc_can_place"] == "yes"


def test_digikey_obsolete(db):
    dk = FakeDk({"LTC2297IUP#PBF": [product("LTC2297IUP#PBF", 5, status="Obsolete")]})
    res = watch.evaluate(row(), db, dk, 3)
    assert res["dk_lifecycle"] == "Obsolete"


def test_validate_accepts_good_rows():
    rows = [row(role="self", drop_in="self", evidence_id="", evidence_page=""),
            row(mpn="B")]
    assert watch.validate(rows) == []


@pytest.mark.parametrize("bad", [
    dict(qty_per_board="0"), dict(qty_per_board="x"), dict(role="other"),
    dict(drop_in="maybe"), dict(mpn=""), dict(refdes=""), dict(why_watched=""),
    dict(jlc_lcsc="679870"), dict(role="self", drop_in="yes"),
])
def test_validate_flags_malformed(bad):
    assert watch.validate([row(**bad)])


@pytest.mark.parametrize("drop_in", ["yes", "pins-only", "no", "unverified"])
def test_validate_substitute_without_evidence(drop_in):
    for missing in ({"evidence_id": ""}, {"evidence_page": ""}):
        probs = watch.validate([row(drop_in=drop_in, **missing)])
        assert any("without evidence" in p for p in probs)


def test_validate_duplicate_and_header():
    assert any("duplicate" in p for p in watch.validate([row(), row()]))
    assert watch.validate([], header=["mpn"])[0].startswith("missing columns")


def test_real_watch_csv_is_well_formed():
    rows = watch.load_watch(watch.WATCH)
    assert rows and watch.validate(rows) == []
    assert any(r["mpn"] == "LTC2292IUP#PBF" and r["refdes"] == "U8" for r in rows)


def test_main_writes_csv_and_check_exit(db, tmp_path, monkeypatch, capsys):
    import bom
    wl = tmp_path / "w.csv"
    cols = watch.WATCH_COLS
    with wl.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row(mpn="LTC2297IUP#PBF"))
        w.writerow(row(mpn="LTC2292IUP#PBF", role="self", drop_in="self",
                       evidence_id="", evidence_page=""))
    monkeypatch.setattr(jlc, "ensure_db", lambda *a, **k: db.con.execute("PRAGMA database_list")
                        .fetchone()[2])
    monkeypatch.setattr(watch, "make_dk", lambda offline: FakeDk({}))
    out = tmp_path / "out.csv"
    assert watch.main(["--offline", "--check", "--boards", "3", "--watch", str(wl),
                       "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "JLC can place now: LTC2297IUP#PBF for U8" in text
    got = list(csv.DictReader(out.open()))
    assert [r["jlc_can_place"] for r in got] == ["yes", "no"]
    assert bom.board_count("default", 3) == 3
    # a substitute with no evidence makes --check fail
    with wl.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row(evidence_id=""))
    assert watch.main(["--offline", "--check", "--boards", "3", "--watch", str(wl),
                       "--out", str(out)]) == 1
