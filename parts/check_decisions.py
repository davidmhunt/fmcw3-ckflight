#!/usr/bin/env python3
"""Exit 0 only when every placed BOM line has a decision row (par-03).

usage: parts/check_decisions.py [--bom parts/out/bom.csv] [--decisions parts/decisions.csv]

A placed line is a bom.csv line whose class is not `dnp` (not fitted) or `nopart` (pads, vias,
mounting holes, the coupler drawn as a footprint). Every ref of a placed line must have a row in
decisions.csv; the row's status may be `proposed`, `user-choice` (the user's list of choices) or
`for-user` (something to obtain). Also fails on a decision row for a ref that is not in the BOM,
and on a row with no status.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOT_PLACED = {"dnp", "nopart"}
STATUSES = {"proposed", "user-choice", "for-user"}


def check(bom: Path, decisions: Path) -> list[str]:
    with bom.open(newline="") as f:
        lines = list(csv.DictReader(f))
    with decisions.open(newline="") as f:
        rows = {r["ref"]: r for r in csv.DictReader(f)}
    problems = []
    all_refs = set()
    for line in lines:
        refs = [r for r in line["refs"].split(";") if r]
        all_refs.update(refs)
        if line["class"] in NOT_PLACED:
            continue
        for ref in refs:
            if ref not in rows:
                problems.append(f"{ref}: placed ({line['value']}, {line['footprint']}) has no decision row")
    for ref, row in rows.items():
        if ref not in all_refs:
            problems.append(f"{ref}: decision row for a ref not in the BOM")
        if row["status"] not in STATUSES:
            problems.append(f"{ref}: status {row['status']!r} is not one of {sorted(STATUSES)}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bom", type=Path, default=ROOT / "parts/out/bom.csv")
    ap.add_argument("--decisions", type=Path, default=ROOT / "parts/decisions.csv")
    args = ap.parse_args()
    problems = check(args.bom, args.decisions)
    for p in problems:
        print(p)
    print("decisions cover every placed line" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
