"""Tests of parts/availability_report.py (par-14) on fixture JLC, DigiKey and inventory data."""
import csv
import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
sys.path.insert(0, str(ROOT / "tools"))
import availability_report as ar  # noqa: E402
import final_parts as fp  # noqa: E402

JLC_DB = {
    "C1": {"stock": 1000, "library": "Basic"},
    "C2": {"stock": 1000, "library": "Extended"},
    "C3": {"stock": 5, "library": "Extended"},
}


def jlc(lcsc):
    return JLC_DB.get(lcsc)


def row(**kw):
    base = {c: "" for c in fp.COLUMNS}
    base.update(board="2rx", refs="U1", role="role", original_mpn="A", chosen_mpn="A", change="none",
                route="jlc-stock", status="applied", fitted="yes", lcsc="C2", fallback="use B")
    base.update(kw)
    return base


def ev(r, boards=10, spares=2, dk=None, inv=None):
    dk = dk or (lambda row_, need: (None, "not cached"))
    return ar.evaluate(r, boards, spares, jlc, dk, {} if inv is None else inv)


# ---------------------------------------------------------------- need arithmetic

def test_need_qty():
    assert ar.need_qty(3, 10, 2) == 32
    assert ar.need_qty(1, 1, 0) == 1


def test_need_counts_refs_and_spares():
    rec = ev(row(refs="U1;U2;U3"))
    assert (rec["per_board"], rec["spares"], rec["need"]) == (3, 2, 32)


def test_basic_parts_get_no_spares():
    rec = ev(row(lcsc="C1", refs="R1;R2"))
    assert rec["library"] == "Basic" and rec["spares"] == 0 and rec["need"] == 20


def test_boards_and_spares_arguments():
    rec = ev(row(), boards=4, spares=5)
    assert rec["need"] == 9


# ---------------------------------------------------------------- inventory first

def test_inventory_taken_first_for_jlc_library():
    inv = {"C2": 6}
    rec = ev(row(route="jlc-library"), inv=inv)     # need 12
    assert rec["inventory"] == 6 and rec["inventory_used"] == 6 and inv["C2"] == 0
    assert rec["stock"] == 1006 and rec["source"] == "inventory+jlc"


def test_inventory_capped_at_need_and_shared():
    inv = {"C2": 15}
    a = ev(row(route="jlc-library", refs="U1"), inv=inv)           # need 12
    b = ev(row(route="jlc-library", refs="U2", board="1rx"), inv=inv)
    assert (a["inventory_used"], b["inventory"], b["inventory_used"]) == (12, 3, 3)
    assert inv["C2"] == 0


def test_inventory_ignored_for_jlc_stock_route():
    inv = {"C2": 50}
    rec = ev(row(route="jlc-stock"), inv=inv)
    assert rec["inventory"] == "" and rec["stock"] == 1000 and inv["C2"] == 50


def test_inventory_rescues_a_short_line():
    assert ev(row(lcsc="C3", route="jlc-stock"))["status"] == "short"
    assert ev(row(lcsc="C3", route="jlc-library"), inv={"C3": 100})["status"] == "ok"


# ---------------------------------------------------------------- status boundaries

@pytest.mark.parametrize("stock,need,status", [
    (None, 10, "unknown"),
    (0, 10, "short"),
    (9, 10, "short"),
    (10, 10, "thin"),       # covers it, nothing left
    (39, 10, "thin"),       # 29 left < 30
    (40, 10, "ok"),         # 30 left = 3 x need
    (41, 10, "ok"),
])
def test_classify_boundaries(stock, need, status):
    assert ar.classify(stock, need) == status


def test_unknown_lcsc_and_no_route():
    rec = ev(row(lcsc="C999"))
    assert rec["status"] == "unknown" and "not in the JLC database" in rec["note"]
    rec = ev(row(route="", lcsc=""))
    assert rec["status"] == "no part" and rec["need"] == 0


def test_digikey_routes_use_digikey_stock():
    seen = []

    def dk(r, need):
        seen.append(need)
        return 25, "in stock"
    for route in ("jlc-sourcing", "hand-solder"):
        rec = ev(row(route=route, lcsc="", refs="U1;U2"), dk=dk)    # need 22
        assert rec["source"] == "digikey" and rec["stock"] == 25 and rec["status"] == "thin"
    assert seen == [22, 22]


def test_digikey_no_answer_is_unknown():
    rec = ev(row(route="hand-solder", lcsc=""))
    assert rec["status"] == "unknown" and "no DigiKey data" in rec["note"]


# ---------------------------------------------------------------- snapshot naming

def test_snapshot_naming_never_overwrites(tmp_path):
    day = dt.date(2026, 11, 25)
    lines = [ev(row())]
    extra = {"jlc_db_date": "2026-11-25", "dk_mode": "cache only", "boards": 10, "spares": 2}
    p1 = ar.write_snapshot(tmp_path, day, lines, extra, "cmd")
    first = (p1 / "lines.csv").read_text()
    p2 = ar.write_snapshot(tmp_path, day, lines, extra, "cmd")
    p3 = ar.write_snapshot(tmp_path, day, lines, extra, "cmd")
    assert [p.name for p in (p1, p2, p3)] == ["2026-11-25", "2026-11-25-2", "2026-11-25-3"]
    assert (p1 / "lines.csv").read_text() == first
    for name in ("lines.csv", "summary.json", "changes.csv", "provenance.md"):
        assert (p2 / name).is_file()
    assert ar.snapshots(tmp_path) == [p1, p2, p3]
    assert ar.previous_snapshot(tmp_path, p3) == p2
    assert ar.previous_snapshot(tmp_path, p1) == p3     # latest other than the new one
    assert ar.snapshot_dir(tmp_path, day).name == "2026-11-25-4"


def test_snapshot_ordering_by_date_then_suffix(tmp_path):
    for n in ("2026-11-24", "2026-11-25-2", "2026-11-25", "2026-11-25-10"):
        (tmp_path / n).mkdir()
        (tmp_path / n / "lines.csv").write_text("")
    assert [p.name for p in ar.snapshots(tmp_path)] == [
        "2026-11-24", "2026-11-25", "2026-11-25-2", "2026-11-25-10"]
    assert ar.previous_snapshot(tmp_path).name == "2026-11-25-10"


def test_second_snapshot_records_diff(tmp_path):
    extra = {"jlc_db_date": "d", "dk_mode": "cache only", "boards": 10, "spares": 2}
    p1 = ar.write_snapshot(tmp_path, dt.date(2026, 11, 24), [ev(row(lcsc="C2"))], extra, "c")
    assert (p1 / "changes.csv").read_text().strip().count("\n") == 0
    p2 = ar.write_snapshot(tmp_path, dt.date(2026, 11, 25), [ev(row(lcsc="C3"))], extra, "c")
    import json
    s = json.loads((p2 / "summary.json").read_text())
    assert s["previous_snapshot"] == p1.name and s["changes_since_previous"] == 1
    assert s["short"] == 1 and s["counts_by_board"] == {"2rx": {"short": 1}}
    with (p2 / "changes.csv").open(newline="") as fh:
        ch = list(csv.DictReader(fh))
    assert ch[0]["old_status"] == "ok" and ch[0]["new_status"] == "short"


# ---------------------------------------------------------------- diff

def rec(refs, status, stock, board="2rx", need=12):
    return {"board": board, "refs": refs, "status": status, "stock": stock, "need": need}


def test_diff_lines():
    old = [rec("U1", "ok", 100), rec("U2", "thin", 15), rec("U3", "ok", 50), rec("U9", "ok", 1)]
    new = [rec("U1", "ok", 100), rec("U2", "short", 5), rec("U3", "ok", 60), rec("U4", "ok", 7)]
    d = {r["refs"]: r for r in ar.diff_lines(old, new)}
    assert set(d) == {"U2", "U3", "U4", "U9"}
    assert (d["U2"]["change"], d["U2"]["old_status"], d["U2"]["new_status"]) == ("changed", "thin", "short")
    assert (d["U3"]["old_stock"], d["U3"]["new_stock"]) == (50, 60)    # same status, stock moved
    assert d["U4"]["change"] == "new line" and d["U9"]["change"] == "removed line"


def test_diff_compares_stock_as_text_and_keys_by_board():
    assert ar.diff_lines([rec("U1", "ok", "100")], [rec("U1", "ok", 100)]) == []
    d = ar.diff_lines([rec("U1", "ok", 1)], [rec("U1", "ok", 1, board="1rx")])
    assert {r["change"] for r in d} == {"new line", "removed line"}


# ---------------------------------------------------------------- --check failures

def good_rows():
    return [row(), row(refs="U2", route="hand-solder", lcsc="", chosen_mpn="X1")]


def test_check_inputs_good():
    assert ar.check_inputs(good_rows(), [{"lcsc": "C2", "qty": "3"}]) == []


def test_check_inputs_failures():
    p = ar.check_inputs([row(lcsc="")], [])
    assert len(p) == 1 and "no LCSC number" in p[0]
    p = ar.check_inputs([row(route="hand-solder", lcsc="", chosen_mpn="", digikey_pn="")], [])
    assert len(p) == 1 and "no MPN or DigiKey number" in p[0]
    assert any("route" in x for x in ar.check_inputs([row(route="bogus")], []))
    assert any("board" in x for x in ar.check_inputs([row(board="3rx")], []))
    assert any("no refs" in x for x in ar.check_inputs([row(refs="")], []))
    assert any("qty" in x for x in ar.check_inputs([], [{"lcsc": "C1", "qty": "x"}]))
    assert any("qty" in x for x in ar.check_inputs([], [{"lcsc": "C1", "qty": "-1"}]))
    assert any("no lcsc" in x for x in ar.check_inputs([], [{"lcsc": " ", "qty": "1"}]))
    assert "lacks columns" in ar.check_inputs([{"board": "2rx"}], [])[0]


def test_check_inputs_ignores_unfitted_and_planned_unnamed():
    assert ar.check_inputs([row(lcsc="", fitted="no")], []) == []
    planned = row(lcsc="", change="design", status="decided")
    assert ar.check_inputs([planned], []) == []
    assert ar.check_inputs([row(lcsc="", change="design", status="applied")], []) != []


def write_csv(path, cols, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def test_main_check_exits_1_on_bad_row_without_writing(tmp_path, capsys):
    parts, inv, out = tmp_path / "p.csv", tmp_path / "i.csv", tmp_path / "out"
    write_csv(parts, fp.COLUMNS, [row(lcsc="")])
    write_csv(inv, fp.INV_COLUMNS, [])
    rc = ar.main(["--offline", "--check", "--parts", str(parts), "--inventory", str(inv),
                  "--out", str(out)])
    assert rc == 1 and not out.exists()
    assert "no LCSC number" in capsys.readouterr().err


def test_main_check_on_good_input_writes_no_snapshot(tmp_path, capsys):
    parts, inv, out = tmp_path / "p.csv", tmp_path / "i.csv", tmp_path / "out"
    write_csv(parts, fp.COLUMNS, [row()])
    write_csv(inv, fp.INV_COLUMNS, [])
    rc = ar.main(["--offline", "--check", "--parts", str(parts), "--inventory", str(inv),
                  "--out", str(out)])
    assert rc == 0 and not out.exists()
    assert "no snapshot written" in capsys.readouterr().out


def test_main_check_exits_1_on_malformed_inventory(tmp_path):
    parts, inv, out = tmp_path / "p.csv", tmp_path / "i.csv", tmp_path / "out"
    write_csv(parts, fp.COLUMNS, [row()])
    write_csv(inv, fp.INV_COLUMNS, [{"mpn": "A", "lcsc": "C2", "qty": "many"}])
    rc = ar.main(["--offline", "--check", "--parts", str(parts), "--inventory", str(inv),
                  "--out", str(out)])
    assert rc == 1 and not out.exists()
