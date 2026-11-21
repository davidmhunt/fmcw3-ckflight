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


def test_unfetched_login_entry_is_pending_until_hash_pinned(tmp_path):
    e = entry(access="login", file="software/files/ti/x.zip")
    write(tmp_path, ds=[e])
    assert fs.check_all(MANS, tmp_path) == []
    assert [p["id"] for p in fs.pending_all(MANS, tmp_path)] == ["a"]
    write(tmp_path, ds=[entry(access="login", file="software/files/ti/x.zip", sha256="0" * 64)])
    assert any("file missing" in p for p in fs.check_all(MANS, tmp_path))
    assert fs.pending_all(MANS, tmp_path) == []


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


def test_real_manifests_include_software_and_it_is_gitignored():
    root = Path(__file__).resolve().parent.parent
    assert ("software/manifest.yaml", False) in fs.MANIFESTS
    entries = fs.load(root / "software/manifest.yaml")
    ids = {e["id"]: e for e in entries}
    assert {"ti-pspice-for-ti-installer", "adi-ltspice-installer"} <= set(ids)
    assert ids["ti-pspice-for-ti-installer"]["file"].startswith("software/files/")
    # the installer moved out of the datasheets manifest
    assert "ti-pspice-for-ti-installer" not in {
        e["id"] for e in fs.load(root / "datasheets/manifest.yaml")}
    assert "software/files/" in (root / ".gitignore").read_text().split()
    for e in entries:
        assert not fs.commit_flag(e)


def test_software_manifest_entry_checks(tmp_path):
    h = put(tmp_path, "software/files/ti/x.zip")
    mans = [("sw.yaml", False)]
    e = entry(id="sw", kind="tool-installer", access="login", file="software/files/ti/x.zip",
              sha256=h)
    (tmp_path / "sw.yaml").write_text(yaml.safe_dump({"entries": [e]}))
    assert fs.check_all(mans, tmp_path) == []
    e["file"] = "software/x.zip"
    (tmp_path / "sw.yaml").write_text(yaml.safe_dump({"entries": [e]}))
    assert any("files/" in p for p in fs.check_all(mans, tmp_path))


def test_add_good_entry_appends_with_hash_and_keeps_comments(tmp_path):
    (tmp_path / "ds.yaml").write_text("# keep me\nentries: []\n")
    mans = [("ds.yaml", False)]

    def fake(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"pdf")

    ok, msg = fs.add_entry("https://x.invalid/n.pdf", "n", "datasheet", "N part (U1)",
                           "datasheets/files/n.pdf", licence="ADI", manifest="ds.yaml",
                           root=tmp_path, opener=fake, manifests=mans)
    assert ok, msg
    assert "# keep me" in (tmp_path / "ds.yaml").read_text()
    (e,) = fs.load(tmp_path / "ds.yaml")
    assert e["sha256"] == hashlib.sha256(b"pdf").hexdigest()
    assert (e["licence"], e["commit"], e["access"], e["url"]) == (
        "ADI", "no", "direct", "https://x.invalid/n.pdf")
    assert fs.check_all(mans, tmp_path) == []


def test_add_duplicate_id_refused_without_download(tmp_path):
    write(tmp_path, ds=[entry()])
    calls = []
    ok, msg = fs.add_entry("https://x.invalid/b.pdf", "a", "datasheet", "T",
                           "datasheets/files/b.pdf", manifest="ds.yaml", root=tmp_path,
                           opener=lambda u, d: calls.append(u), manifests=MANS)
    assert not ok and "already exists" in msg and calls == []
    assert len(fs.load(tmp_path / "ds.yaml")) == 1


def test_add_dead_link_reported_and_nothing_appended(tmp_path):
    write(tmp_path)

    def dead(url, dest):
        raise OSError("HTTP Error 404: Not Found")

    ok, msg = fs.add_entry("https://x.invalid/gone.pdf", "g", "datasheet", "T",
                           "datasheets/files/g.pdf", manifest="ds.yaml", root=tmp_path,
                           opener=dead, manifests=MANS)
    assert not ok and "download failed" in msg and "404" in msg
    assert fs.load(tmp_path / "ds.yaml") == []


def test_add_commit_no_outside_files_dir_refused(tmp_path):
    write(tmp_path)
    ok, msg = fs.add_entry("https://x.invalid/a", "z", "datasheet", "T", "datasheets/z.pdf",
                           manifest="ds.yaml", root=tmp_path, opener=lambda u, d: None,
                           manifests=MANS)
    assert not ok and "files/" in msg


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


def test_failed_download_becomes_pending_row_and_run_continues(tmp_path):
    write(tmp_path, ds=[
        entry(id="dead", url="https://x.invalid/dead.pdf", file="datasheets/files/dead.pdf"),
        entry(id="ok", url="https://x.invalid/ok.pdf", file="datasheets/files/ok.pdf"),
        entry(id="form", access="form", file="datasheets/files/form.pdf",
              url="https://x.invalid/form"),
    ])

    def fake(url, dest):
        if "dead" in url:
            raise OSError("HTTP Error 403: Forbidden")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"ok")

    todo = fs.fetch_all(MANS, tmp_path, record=True, opener=fake, today="2026-11-21")
    assert any("dead" in t and "403" in t for t in todo)
    by_id = {e["id"]: e for e in fs.load(tmp_path / "ds.yaml")}
    assert by_id["dead"]["fetch_error"] == "HTTP Error 403: Forbidden (2026-11-21)"
    assert by_id["ok"]["sha256"] == hashlib.sha256(b"ok").hexdigest()
    # not failed, listed as pending; the file for "dead" is still missing
    assert fs.check_all(MANS, tmp_path) == []
    assert {e["id"] for e in fs.pending_all(MANS, tmp_path)} == {"dead", "form"}
    rows = fs.write_user_fetch(MANS, tmp_path)
    assert len(rows) == 2
    text = (tmp_path / "docs" / "user-fetch.md").read_text()
    assert "https://x.invalid/dead.pdf" in text and "`datasheets/files/dead.pdf`" in text
    assert "403" in text and "./run tools/fetch_sources.py --record" in text
    assert "ok.pdf" not in text


def test_fetch_and_record_keep_manifest_comments(tmp_path):
    text = (
        "# header comment\nentries:\n"
        "- id: a\n  kind: datasheet\n  # entry comment\n  title: T\n  url: https://x.invalid/a\n"
        "  access: direct\n  file: datasheets/files/a.pdf\n  sha256: ''\n  licence: v\n"
        "  commit: 'no'\n"
        "- id: dead\n  kind: datasheet\n  title: T\n  url: https://x.invalid/d\n"
        "  access: direct\n  file: datasheets/files/d.pdf\n  sha256: ''\n  licence: v\n"
        "  commit: 'no'\n# trailing comment\n")
    (tmp_path / "ds.yaml").write_text(text)
    (tmp_path / "ref.yaml").write_text("entries: []\n")

    def fake(url, dest):
        if "/d" in url:
            raise OSError("HTTP Error 403: Forbidden")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x")

    fs.fetch_all(MANS, tmp_path, record=True, opener=fake, today="2026-11-21")
    out = (tmp_path / "ds.yaml").read_text()
    for c in ("# header comment", "# entry comment", "# trailing comment"):
        assert c in out
    by_id = {e["id"]: e for e in fs.load(tmp_path / "ds.yaml")}
    assert by_id["a"]["sha256"] == hashlib.sha256(b"x").hexdigest()
    assert by_id["dead"]["fetch_error"].startswith("HTTP Error 403")
    # a saved file clears the error and keeps the comments
    put(tmp_path, "datasheets/files/d.pdf", b"saved")
    fs.fetch_all(MANS, tmp_path, record=True, opener=fake)
    out = (tmp_path / "ds.yaml").read_text()
    assert "# entry comment" in out and "fetch_error" not in out


PDF = b"%PDF-1.7 fake"


def dk_opener(calls, bodies):
    """Fake opener: `bodies` maps a URL to bytes or an exception."""
    def fake(url, dest):
        calls.append(url)
        body = bodies[url]
        if isinstance(body, Exception):
            raise body
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
    return fake


def dk_entry(**kw):
    return entry(id="d", digikey="MPN1", file="datasheets/files/digikey/mpn1.pdf",
                 url="https://maker.invalid/d.pdf", **kw)


def product(ds="https://dk.invalid/d.pdf"):
    return {"ProductUrl": "https://www.digikey.com/p/d", "DatasheetUrl": ds}


def test_digikey_url_downloaded_and_hash_recorded(tmp_path):
    write(tmp_path, ds=[dk_entry()])
    calls = []
    fs.fetch_all(MANS, tmp_path, record=True, lookup=lambda m: product(),
                 opener=dk_opener(calls, {"https://dk.invalid/d.pdf": PDF}))
    assert calls == ["https://dk.invalid/d.pdf"]
    (e,) = fs.load(tmp_path / "ds.yaml")
    assert e["sha256"] == hashlib.sha256(PDF).hexdigest() and "digikey_url" not in e
    assert fs.check_all(MANS, tmp_path) == []


def test_protocol_relative_digikey_url_becomes_https(tmp_path):
    write(tmp_path, ds=[dk_entry()])
    calls = []
    fs.fetch_all(MANS, tmp_path, lookup=lambda m: product("//dk.invalid/d.pdf"),
                 opener=dk_opener(calls, {"https://dk.invalid/d.pdf": PDF}))
    assert calls == ["https://dk.invalid/d.pdf"]
    assert (tmp_path / "datasheets/files/digikey/mpn1.pdf").is_file()


def test_html_page_instead_of_pdf_is_refused(tmp_path):
    write(tmp_path, ds=[dk_entry()])
    calls = []
    fs.fetch_all(MANS, tmp_path, lookup=lambda m: product(), today="2026-11-21",
                 opener=dk_opener(calls, {"https://dk.invalid/d.pdf": b"<html>blocked</html>",
                                          "https://maker.invalid/d.pdf": b"<html>no</html>"}))
    assert not (tmp_path / "datasheets/files/digikey/mpn1.pdf").exists()
    (e,) = fs.load(tmp_path / "ds.yaml")
    assert "not a PDF" in e["fetch_error"]


def test_no_api_result_falls_back_to_entry_url(tmp_path):
    write(tmp_path, ds=[dk_entry()])
    calls = []
    fs.fetch_all(MANS, tmp_path, record=True, lookup=lambda m: None,
                 opener=dk_opener(calls, {"https://maker.invalid/d.pdf": PDF}))
    assert calls == ["https://maker.invalid/d.pdf"]
    (e,) = fs.load(tmp_path / "ds.yaml")
    assert e["sha256"] and "fetch_error" not in e


def test_api_error_falls_back_to_entry_url(tmp_path):
    write(tmp_path, ds=[dk_entry()])

    def boom(m):
        raise RuntimeError("Missing DIGIKEY_CLIENT_ID")

    calls = []
    fs.fetch_all(MANS, tmp_path, lookup=boom,
                 opener=dk_opener(calls, {"https://maker.invalid/d.pdf": PDF}))
    assert calls == ["https://maker.invalid/d.pdf"]


def test_both_fail_gives_pending_row_with_digikey_product_link(tmp_path):
    write(tmp_path, ds=[dk_entry()])
    calls = []
    fs.fetch_all(MANS, tmp_path, lookup=lambda m: product(), today="2026-11-21",
                 opener=dk_opener(calls, {"https://dk.invalid/d.pdf": OSError("HTTP Error 403"),
                                          "https://maker.invalid/d.pdf": OSError("HTTP Error 404")}))
    assert calls == ["https://dk.invalid/d.pdf", "https://maker.invalid/d.pdf"]
    (e,) = fs.load(tmp_path / "ds.yaml")
    assert e["digikey_url"] == "https://www.digikey.com/p/d"
    assert fs.check_all(MANS, tmp_path) == []
    assert [p["id"] for p in fs.pending_all(MANS, tmp_path)] == ["d"]
    fs.write_user_fetch(MANS, tmp_path)
    text = (tmp_path / "docs" / "user-fetch.md").read_text()
    assert "https://www.digikey.com/p/d" in text and "403" in text and "404" in text


def test_api_keys_never_in_output_or_manifest(tmp_path, capsys):
    secret = "S3CRET-VALUE-XYZ"
    dk = fs._dk_module()

    def transport(url, data, headers):
        if url.endswith("/token"):
            return {"access_token": "TOKEN-ABC"}
        return {"Products": [dict(product(), ManufacturerProductNumber="MPN1")]}

    client = dk.Client("CID-123", secret, transport=transport, delay=0)
    lookup = fs.make_lookup(client, cache=tmp_path / "cache")
    write(tmp_path, ds=[dk_entry()])
    fs.fetch_all(MANS, tmp_path, lookup=lookup, today="2026-11-21",
                 opener=dk_opener([], {"https://dk.invalid/d.pdf": OSError("HTTP Error 403"),
                                       "https://maker.invalid/d.pdf": OSError("HTTP Error 404")}))
    out = capsys.readouterr()
    blob = out.out + out.err + (tmp_path / "ds.yaml").read_text() + "".join(
        p.read_text() for p in (tmp_path / "cache").iterdir())
    for key in (secret, "CID-123", "TOKEN-ABC"):
        assert key not in blob


def test_saved_file_plus_record_removes_pending_row(tmp_path):
    write(tmp_path, ds=[entry(id="dead", file="datasheets/files/dead.pdf")])

    def dead(url, dest):
        raise OSError("HTTP Error 404: Not Found")

    fs.fetch_all(MANS, tmp_path, opener=dead, today="2026-11-21")
    assert len(fs.write_user_fetch(MANS, tmp_path)) == 1
    h = put(tmp_path, "datasheets/files/dead.pdf", b"saved by hand")
    fs.fetch_all(MANS, tmp_path, record=True, opener=dead)
    (e,) = fs.load(tmp_path / "ds.yaml")
    assert e["sha256"] == h and "fetch_error" not in e
    assert fs.check_all(MANS, tmp_path) == []
    assert fs.write_user_fetch(MANS, tmp_path) == []
    assert "Nothing pending" in (tmp_path / "docs" / "user-fetch.md").read_text()


def test_from_bom_adds_uncovered_mpns_once(tmp_path):
    (tmp_path / "parts" / "out").mkdir(parents=True)
    (tmp_path / "parts" / "out" / "availability.csv").write_text(
        "refs,MPN,dk_url\nC1;C2,CL05B104KO5NNNC,https://dk.invalid/p\nU1,ADF4158CCPZ-RL7,\nR1,,\n")
    (tmp_path / "parts" / "decisions.csv").write_text("ref,MPN\nU9,MPZ2012S101AT000\n")
    covered = entry(id="adf", title="ADI ADF4158", file="datasheets/files/adi/adf4158.pdf",
                    sha256="0" * 64)
    pend = entry(id="tdk", title="TDK MPZ2012S101AT000 bead", access="form",
                 file="datasheets/files/tdk/x.pdf")
    write(tmp_path, ds=[covered, pend])
    added, patched = fs.from_bom("ds.yaml", tmp_path, MANS, fs.BOM_FILES)
    assert added == ["dk-cl05b104ko5nnnc"] and patched == ["tdk"]
    got = {e["id"]: e for e in fs.load(tmp_path / "ds.yaml")}
    assert got["tdk"]["digikey"] == "MPZ2012S101AT000"
    new = got["dk-cl05b104ko5nnnc"]
    assert (new["digikey"], new["commit"], new["url"]) == (
        "CL05B104KO5NNNC", "no", "https://dk.invalid/p")
    assert new["file"] == "datasheets/files/digikey/cl05b104ko5nnnc.pdf"
    assert "C1, C2" in new["title"]
    assert fs.from_bom("ds.yaml", tmp_path, MANS, fs.BOM_FILES) == ([], [])
    assert len(fs.load(tmp_path / "ds.yaml")) == 3
