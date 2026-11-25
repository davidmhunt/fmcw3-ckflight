"""Tests of parts/final_parts.py (par-13): the --check failures on a fixture, the real record, archive routing."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
sys.path.insert(0, str(ROOT / "tools"))
import build_report as br  # noqa: E402
import final_parts as fp  # noqa: E402

MANIFEST = {"ds-a", "ds-b"}


def row(**kw):
    base = {c: "" for c in fp.COLUMNS}
    base.update(board="2rx", refs="U1", role="role", original_mpn="A", chosen_mpn="A", change="none",
                route="jlc-stock", status="applied", fitted="yes", lcsc="C1")
    base.update(kw)
    return base


def run(rows, inventory=(), placed=None):
    return fp.check(rows, list(inventory), MANIFEST, lambda c: True, placed)


def test_good_fixture_passes():
    rows = [row(), row(refs="U2", change="fields", reason="why", evidence="ds-a p.3")]
    assert run(rows, placed={"2rx": {"U1": False, "U2": False}}) == []


def test_unknown_manifest_id():
    rows = [row(change="fields", reason="why", evidence="ds-a p.3; nope p.1")]
    probs = run(rows)
    assert len(probs) == 1 and "'nope'" in probs[0]


def test_changed_row_citing_pdfs_needs_a_page():
    def go(evidence):
        return fp.check([row(change="fields", reason="why", evidence=evidence)], [], MANIFEST,
                        lambda c: True, None, pdf_ids={"ds-a"})
    probs = go("ds-a; ds-b")
    assert len(probs) == 1 and "no page" in probs[0]
    assert go("ds-a p.2; ds-b") == []
    assert go("ds-b") == []          # a data file has no pages


def test_ref_in_no_row():
    probs = run([row()], placed={"2rx": {"U1": False, "U9": False}})
    assert any("2rx U9" in p and "no row" in p for p in probs)


def test_ref_in_two_rows():
    probs = run([row(), row(role="other")], placed={"2rx": {"U1": False}})
    assert any("2rx U1" in p and "2 rows" in p for p in probs)


def test_change_without_reason_or_evidence():
    probs = run([row(change="design", evidence="ds-a")])
    assert len(probs) == 1 and "no reason" in probs[0]
    probs = run([row(change="design", reason="why")])
    assert len(probs) == 1 and "no evidence" in probs[0]


def test_library_row_without_inventory():
    rows = [row(route="jlc-library", lcsc="C77")]
    assert any("no inventory row" in p for p in run(rows))
    inv = [{"mpn": "A", "lcsc": "C77", "qty": "3", "date": "", "held": "jlc-library", "for": "x"}]
    assert run(rows, inv) == []


def test_real_files_pass(tmp_path, capsys):
    pytest.importorskip("yaml")
    rc = fp.main(["--check", "--offline", "--build", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "final parts record is consistent" in out


def test_archive_key_routes_output(tmp_path):
    a = tmp_path / "01_old"
    a.mkdir()
    (a / "deck.yaml").write_text("archive: true\nslides: []\n")
    b = tmp_path / "02_new"
    b.mkdir()
    (b / "deck.yaml").write_text("slides: []\n")
    out = tmp_path / "reports"
    assert br.is_archived(a) and not br.is_archived(b)
    assert br.output_dir(a, out) == out / "archive"
    assert br.output_dir(b, out) == out
