"""Tests of tools/check_models.py with fixture files."""
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_models as cm  # noqa: E402

COLS = ["refdes", "mpn", "model_kind", "needed_by", "why", "manifest_id", "option_of"]


def row(**kw):
    r = dict(refdes="U1", mpn="X1", model_kind="s2p", needed_by="sim-01", why="w",
             manifest_id="m1", option_of="")
    r.update(kw)
    return r


def entry(id="m1", **kw):
    e = dict(id=id, kind="vendor-model", title="T", url="https://example.invalid",
             access="form", file="datasheets/files/x.s2p", sha256="", licence="v", commit="no")
    e.update(kw)
    return e


def files(tmp, rows, entries, par07=None):
    n = tmp / "needed.csv"
    with open(n, "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rows)
    m = tmp / "manifest.yaml"
    m.write_text(yaml.safe_dump({"entries": entries}))
    d = tmp / "directives"
    d.mkdir()
    if par07:
        (d / "par-07.md").write_text(f"# par-07: x\nStatus: {par07}\n")
    return ["--needed", str(n), "--manifest", str(m), "--directives", str(d)]


def test_all_covered_passes_and_summarises(tmp_path, capsys):
    rows = [row(manifest_id="a"), row(manifest_id="b"), row(manifest_id="c")]
    ents = [entry("a", sha256="ab" * 32), entry("b"),
            entry("c", title="X: none published at the maker (checked 2026-11-21)")]
    assert cm.main(files(tmp_path, rows, ents)) == 0
    out = capsys.readouterr().out
    assert "1 on file, 1 user-fetch, 1 none published" in out
    assert "OK" in out


def test_row_without_manifest_id_fails(tmp_path, capsys):
    assert cm.main(files(tmp_path, [row(manifest_id="")], [entry()])) == 1
    assert "no manifest entry named" in capsys.readouterr().out


def test_unknown_id_fails(tmp_path, capsys):
    assert cm.main(files(tmp_path, [row(manifest_id="nope")], [entry()])) == 1
    assert "does not exist" in capsys.readouterr().out


def test_wrong_kind_fails(tmp_path, capsys):
    assert cm.main(files(tmp_path, [row()], [entry(kind="datasheet")])) == 1
    assert "not vendor-model" in capsys.readouterr().out


def test_unknown_model_kind_fails(tmp_path):
    assert cm.main(files(tmp_path, [row(model_kind="vhdl")], [entry()])) == 1


def test_placeholder_fails_when_par07_done(tmp_path, capsys):
    args = files(tmp_path, [row(mpn="TBD-par-07")], [entry()], par07="done")
    assert cm.main(args) == 1
    assert "fill the PA row" in capsys.readouterr().out


def test_placeholder_allowed_while_par07_open(tmp_path):
    assert cm.main(files(tmp_path, [row(mpn="TBD-par-07")], [entry()], par07="approved")) == 0


def test_placeholder_allowed_when_par07_absent(tmp_path):
    assert cm.main(files(tmp_path, [row(mpn="TBD-par-07")], [entry()])) == 0


def test_real_repo_files_pass():
    assert cm.main([]) == 0
