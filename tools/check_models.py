#!/usr/bin/env python3
"""Check that every simulation model the planned analyses need is covered by a manifest.

parts/models_needed.csv lists one row per needed model (columns refdes, mpn, model_kind,
needed_by, why, manifest_id, option_of). Each row's manifest_id must be an entry in
datasheets/manifest.yaml. Exit status is non-zero when

  - a row has an empty manifest_id, or names an id no manifest entry has;
  - a row names an entry whose kind is not `vendor-model`;
  - a row has the MPN `TBD-par-07` while directive par-07 is done (the PA row has to be filled
    once the PA is chosen).

The summary counts the rows by state of their entry:
  on file         a sha256 is pinned (the file was downloaded and hashed)
  user-fetch      no hash yet; the user saves the file (listed in docs/user-fetch.md)
  none published  the entry's title says `none published` or `none found`: the vendor has no
                  model, and the row's entry names the stand-in the analysis will use

  check_models.py [--needed PATH] [--manifest PATH] [--directives DIR]
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NEEDED = "parts/models_needed.csv"
MANIFEST = "datasheets/manifest.yaml"
DIRECTIVES = "docs/directives"
PLACEHOLDER = "TBD-par-07"
KINDS = ("s2p", "snp", "spice", "pspice", "bead")
NONE_RE = re.compile(r"none (published|found)", re.I)


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_entries(path):
    data = yaml.safe_load(Path(path).read_text()) or {}
    return {e["id"]: e for e in data.get("entries") or []}


def directive_status(directives, did):
    """The Status line of docs/directives/<did>.md, or '' when absent."""
    p = Path(directives) / f"{did}.md"
    if not p.is_file():
        return ""
    m = re.search(r"^Status:\s*(\S+)", p.read_text(), re.M)
    return m.group(1) if m else ""


def state(entry):
    if entry.get("sha256"):
        return "on file"
    if NONE_RE.search(str(entry.get("title", ""))):
        return "none published"
    return "user-fetch"


def check(rows, entries, par07_done):
    """Return (problems, counts)."""
    problems = []
    counts = {"on file": 0, "user-fetch": 0, "none published": 0}
    for i, r in enumerate(rows, start=2):
        who = f"{r.get('refdes', '?')} {r.get('mpn', '?')} ({r.get('model_kind', '?')}), line {i}"
        if r.get("model_kind") not in KINDS:
            problems.append(f"{who}: unknown model kind {r.get('model_kind')!r}")
        if r.get("mpn") == PLACEHOLDER and par07_done:
            problems.append(f"{who}: MPN is {PLACEHOLDER} but par-07 is done; fill the PA row")
        mid = (r.get("manifest_id") or "").strip()
        if not mid:
            problems.append(f"{who}: no manifest entry named")
            continue
        e = entries.get(mid)
        if e is None:
            problems.append(f"{who}: manifest id {mid!r} does not exist")
            continue
        if e.get("kind") != "vendor-model":
            problems.append(f"{who}: manifest id {mid!r} is kind {e.get('kind')!r}, not vendor-model")
            continue
        counts[state(e)] += 1
    return problems, counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--needed", default=str(ROOT / NEEDED))
    ap.add_argument("--manifest", default=str(ROOT / MANIFEST))
    ap.add_argument("--directives", default=str(ROOT / DIRECTIVES))
    a = ap.parse_args(argv)
    rows = load_rows(a.needed)
    entries = load_entries(a.manifest)
    done = directive_status(a.directives, "par-07") == "done"
    problems, counts = check(rows, entries, done)
    for p in problems:
        print(f"FAIL {p}")
    print(f"{len(rows)} needed models: {counts['on file']} on file, "
          f"{counts['user-fetch']} user-fetch, {counts['none published']} none published")
    if problems:
        print(f"{len(problems)} problem(s)")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
