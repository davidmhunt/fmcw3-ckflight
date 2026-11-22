"""rx1-02 step 7: parts/rx1_changes.csv, the rx1- keys of parts/choices.json and the Board rows of
docs/board-changes.md agree (generator: analysis/11_board_1rx/rx1_changes.py).
"""
import csv
import importlib.util
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("rx1_changes", ROOT / "analysis/11_board_1rx/rx1_changes.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

CSV = ROOT / "parts" / "rx1_changes.csv"
DOC = ROOT / "docs" / "board-changes.md"


def doc_rows():
    """Part-changes table of docs/board-changes.md: Ref cell -> dict of columns."""
    rows = {}
    head = None
    for line in DOC.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if cells[0] == "Ref":
            head = cells
            continue
        if head and len(cells) == len(head) and not set(cells[0]) <= {"-"}:
            rows[cells[0]] = dict(zip(head, cells))
    return rows


def test_csv_is_current():
    got = list(csv.DictReader(CSV.open(newline="")))
    assert got == rc.changes(), "run ./run python3 analysis/11_board_1rx/rx1_changes.py"


def test_choices_json_is_current():
    data = json.loads(rc.CHOICES.read_text())
    got = {k: v for k, v in data["choices"].items() if k.startswith("rx1-")}
    assert got == rc.choices()
    assert rc.CHOICES.read_text() == rc.format_choices(rc.merged_choices())


def test_every_row_has_fields_and_a_check():
    rows = list(csv.DictReader(CSV.open(newline="")))
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert r["kind"] in {"swap", "value", "dnp", "new", "net", "fields"}, r
        assert r["status"] in {"decided", "proposed", "option"}, r
        assert r["refs"] and r["check"] and r["evidence"] and r["board_row"], r
        if r["status"] == "option":
            assert r["choice"].startswith("rx1-"), r


def test_option_rows_name_a_choice_key_in_choices_json():
    keys = set(json.loads(rc.CHOICES.read_text())["choices"])
    for r in csv.DictReader(CSV.open(newline="")):
        if r["choice"]:
            assert r["choice"] in keys, r


def test_every_change_has_a_board_changes_row_naming_its_check():
    rows = doc_rows()
    for r in csv.DictReader(CSV.open(newline="")):
        d = rows.get(r["board_row"])
        assert d is not None, f"{r['id']}: no docs/board-changes.md row {r['board_row']!r}"
        assert d["Board"] in {"1-RX", "both"}, (r["board_row"], d["Board"])
        assert d["Covered by"], r["board_row"]
    for label in rc.BOARD_ROWS:
        assert label in rows, label


def test_every_part_row_has_a_board_value():
    for ref, d in doc_rows().items():
        assert d["Board"] in {"1-RX", "2-RX", "both"}, (ref, d["Board"])


def test_cited_manifest_ids_exist():
    ids = {e["id"] for e in (yaml.safe_load((ROOT / "datasheets/manifest.yaml").read_text()) or {})["entries"]}
    texts = [r["evidence"] for r in csv.DictReader(CSV.open(newline="")) if r["evidence"] != "none on file"]
    for ch in rc.choices().values():
        texts += [row[3] for row in ch["rows"]] + [ch["consequence"]]
    cited = set()
    for t in texts:
        cited |= set(re.findall(r"([a-z][a-z0-9]*(?:-[a-z0-9.]+)+) p\.\d", t))
    assert cited
    assert not cited - ids, sorted(cited - ids)
