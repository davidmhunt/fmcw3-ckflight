"""Tests of tools/fetch_sources.py with fixture manifests (no network)."""
import hashlib
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import fetch_sources as fs  # noqa: E402

MANS = [("ds.yaml", False), ("ref.yaml", True)]


def entry(**kw):
    e = dict(id="a", kind="datasheet", title="T", url="https://example.invalid/a.pdf",
             access="direct", file="datasheets/files/a.pdf", sha256="", licence="vendor",
             commit="no")
    e.update(kw)
    return e


def write(root, ds=(), ref=()):
    (root / "ds.yaml").write_text(yaml.safe_dump({"entries": list(ds)}))
    (root / "ref.yaml").write_text(yaml.safe_dump({"entries": list(ref)}))


def put(root, rel, data=b"hello"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_empty_manifests_pass(tmp_path):
    write(tmp_path)
    assert fs.check_all(MANS, tmp_path) == []


def test_missing_file_fails(tmp_path):
    write(tmp_path, ds=[entry()])
    assert any("file missing" in p for p in fs.check_all(MANS, tmp_path))


def test_good_file_passes_and_hash_mismatch_fails(tmp_path):
    h = put(tmp_path, "datasheets/files/a.pdf")
    write(tmp_path, ds=[entry(sha256=h)])
    assert fs.check_all(MANS, tmp_path) == []
    write(tmp_path, ds=[entry(sha256="0" * 64)])
    assert any("mismatch" in p for p in fs.check_all(MANS, tmp_path))


def test_reference_needs_verified_item(tmp_path):
    h = put(tmp_path, "docs/references/files/r.pdf")
    r = entry(id="r", kind="paper", file="docs/references/files/r.pdf", sha256=h)
    write(tmp_path, ref=[r])
    assert any("no verified" in p for p in fs.check_all(MANS, tmp_path))
    r["verified"] = [{"page": 3, "item": "Eq. 1", "quote": "f = 1/T"}]
    write(tmp_path, ref=[r])
    assert fs.check_all(MANS, tmp_path) == []


def test_uncommitted_file_must_be_under_files_dir(tmp_path):
    h = put(tmp_path, "datasheets/a.pdf")
    write(tmp_path, ds=[entry(file="datasheets/a.pdf", sha256=h)])
    assert any("files/" in p for p in fs.check_all(MANS, tmp_path))
    write(tmp_path, ds=[entry(file="datasheets/a.pdf", sha256=h, commit="yes")])
    assert fs.check_all(MANS, tmp_path) == []


def test_missing_field_and_bad_access_and_duplicate(tmp_path):
    bad = entry()
    del bad["licence"]
    write(tmp_path, ds=[bad])
    assert any("missing field licence" in p for p in fs.check_all(MANS, tmp_path))
    write(tmp_path, ds=[entry(access="magic")])
    assert any("access must be" in p for p in fs.check_all(MANS, tmp_path))
    h = put(tmp_path, "datasheets/files/a.pdf")
    write(tmp_path, ds=[entry(sha256=h), entry(sha256=h)])
    assert any("duplicate" in p for p in fs.check_all(MANS, tmp_path))


def test_fetch_downloads_direct_records_hash_and_lists_todo(tmp_path):
    write(tmp_path, ds=[
        entry(),
        entry(id="b", access="form", file="datasheets/files/b.pdf", url="https://x.invalid/b"),
        entry(id="c", access="login", file="datasheets/files/c.zip", url="https://x.invalid/c"),
    ])
    calls = []

    def fake(url, dest):
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"data")

    todo = fs.fetch_all(MANS, tmp_path, record=True, opener=fake)
    assert calls == ["https://example.invalid/a.pdf"]
    assert len(todo) == 2 and "https://x.invalid/b" in todo[0] and "(login)" in todo[1]
    a = fs.load(tmp_path / "ds.yaml")[0]
    assert a["sha256"] == hashlib.sha256(b"data").hexdigest()
    # a second fetch downloads nothing
    fs.fetch_all(MANS, tmp_path, opener=fake)
    assert len(calls) == 1
