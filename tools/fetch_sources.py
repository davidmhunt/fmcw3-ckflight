#!/usr/bin/env python3
"""Fetch and check the datasheets, vendor models and references the analyses rely on.

Three manifests (YAML, top-level key `entries:`, a list):
  datasheets/manifest.yaml        datasheets and vendor models
  software/manifest.yaml          tool installers (see software/README.md)
  docs/references/manifest.yaml   papers, textbooks, app notes, documents

Entry fields: id, kind, title, url (public), access (direct|form|login), file (path
relative to the repo root), sha256, licence, commit (yes|no). Reference entries also carry
`verified:`, a list of {page, item, quote} read from the downloaded file.

  fetch_sources.py            download `direct` entries, print a to-do list for the rest
  fetch_sources.py --check    fail on a missing file, a hash mismatch, or a reference
                              with no `verified` item
  fetch_sources.py --record   also write the sha256 of files that have none yet

Files with `commit: no` must live under a `files/` directory, which .gitignore covers.
Only a licence that allows redistribution may use `commit: yes`.
"""
import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = [
    ("datasheets/manifest.yaml", False),
    ("software/manifest.yaml", False),
    ("docs/references/manifest.yaml", True),
]
REQUIRED = ("id", "kind", "title", "url", "access", "file", "sha256", "licence", "commit")
ACCESS = ("direct", "form", "login")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    data = yaml.safe_load(Path(path).read_text()) or {}
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        raise ValueError(f"{path}: `entries` must be a list")
    return entries


def commit_flag(entry):
    return str(entry.get("commit")).lower() in ("yes", "true")


def check_entry(entry, is_reference, root=ROOT):
    """Return a list of problem strings for one entry."""
    eid = entry.get("id", "?")
    problems = []
    for key in REQUIRED:
        if key not in entry:
            problems.append(f"{eid}: missing field {key}")
    if problems:
        return problems
    if entry["access"] not in ACCESS:
        problems.append(f"{eid}: access must be one of {ACCESS}")
    if str(entry["commit"]).lower() not in ("yes", "no", "true", "false"):
        problems.append(f"{eid}: commit must be yes or no")
    if not commit_flag(entry) and "files" not in Path(entry["file"]).parts:
        problems.append(f"{eid}: commit: no needs a path under a files/ directory (gitignored)")
    path = root / entry["file"]
    if not path.is_file():
        problems.append(f"{eid}: file missing: {entry['file']}")
    elif not entry["sha256"]:
        problems.append(f"{eid}: no sha256 recorded (run fetch_sources.py --record)")
    elif sha256_of(path) != entry["sha256"]:
        problems.append(f"{eid}: sha256 mismatch for {entry['file']}")
    if is_reference and not entry.get("verified"):
        problems.append(f"{eid}: reference has no verified item")
    return problems


def check_all(manifests, root=ROOT):
    problems = []
    seen = set()
    for rel, is_ref in manifests:
        mpath = root / rel
        if not mpath.is_file():
            problems.append(f"manifest missing: {rel}")
            continue
        for entry in load(mpath):
            if entry.get("id") in seen:
                problems.append(f"{entry.get('id')}: duplicate id")
            seen.add(entry.get("id"))
            problems += check_entry(entry, is_ref, root)
    return problems


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "fetch_sources/1.0"})
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)


def fetch_all(manifests, root=ROOT, record=False, opener=download):
    """Download direct entries that are missing; return the user to-do lines."""
    todo = []
    for rel, _ in manifests:
        mpath = root / rel
        if not mpath.is_file():
            continue
        entries = load(mpath)
        changed = False
        for e in entries:
            path = root / e["file"]
            if not path.is_file():
                if e["access"] == "direct":
                    print(f"fetching {e['id']}: {e['url']}")
                    opener(e["url"], path)
                else:
                    todo.append(
                        f"{e['id']} ({e['access']}): open {e['url']} and save as {e['file']}"
                        f" [{e['title']}; licence: {e['licence']}]")
                    continue
            if record and path.is_file() and not e.get("sha256"):
                e["sha256"] = sha256_of(path)
                print(f"recorded sha256 for {e['id']}: {e['sha256']}")
                changed = True
        if changed:
            mpath.write_text(yaml.safe_dump({"entries": entries}, sort_keys=False, width=100))
    return todo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="verify files, hashes, verified items")
    ap.add_argument("--record", action="store_true", help="record missing sha256 after fetching")
    args = ap.parse_args(argv)
    if args.check:
        problems = check_all(MANIFESTS)
        for p in problems:
            print("FAIL", p)
        print("sources check:", "FAILED" if problems else "ok")
        return 1 if problems else 0
    todo = fetch_all(MANIFESTS, record=args.record)
    if todo:
        print("\nTo do by hand (not downloadable unattended):")
        for t in todo:
            print(" -", t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
