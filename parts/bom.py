#!/usr/bin/env python3
"""Grouped BOM from the schematic, headless (kicad-cli), with a class per group.

usage: parts/bom.py [--out parts/out/bom.csv] [--decisions parts/decisions.csv]
                    [--schematic kicad/fmcw3.kicad_sch]

Exports every symbol with `kicad-cli sch export bom`, then groups by value, footprint and the
part-number fields (MPN, Manufacturer, LCSC, DigiKey PN). Each group gets a class:

  mpn      every ref carries an MPN (or an LCSC number) in the schematic or in decisions.csv
  generic  no MPN, a passive (C, R, L, FB) whose value and package define it
  dnp      not fitted (value "DNP", or the DNP / exclude-from-BOM attribute)
  nopart   no MPN and not a generic passive (ICs, connectors, crystals): needs a part

`parts/decisions.csv` (written by par-03) holds per-ref part-number fields until they are in
the schematic: columns `ref` plus any of MPN, Manufacturer, LCSC, DigiKey PN, DNP. A schematic
field wins over a decision. A missing decisions file is fine.

API: export_rows(sch) -> [dict]; load_decisions(path) -> {ref: {field: value}};
     merge_decisions(rows, decisions) -> rows; group_rows(rows) -> [group dict];
     classify(group) -> str; build(sch, decisions) -> [group dict]; write_csv(groups, path).
Nothing under kicad/ is written.
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCH = ROOT / "kicad" / "fmcw3.kicad_sch"
DECISIONS = ROOT / "parts" / "decisions.csv"
OUT = ROOT / "parts" / "out" / "bom.csv"

PART_FIELDS = ["MPN", "Manufacturer", "LCSC", "DigiKey PN"]
GROUP_KEYS = ["Value", "Footprint"] + PART_FIELDS
GENERIC_PREFIXES = ("C", "R", "L", "FB")
# kicad-cli field names (the schematic field "DigiKey PN" is exported by its own name)
EXPORT_FIELDS = ["Reference", "Value", "Footprint", "${DNP}", "${EXCLUDE_FROM_BOM}"] + PART_FIELDS
CLASSES = ("mpn", "generic", "dnp", "nopart")


def prefix(ref: str) -> str:
    return re.sub(r"[0-9]+$", "", ref)


def ref_key(ref: str):
    m = re.match(r"^(\D*)(\d+)$", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def footprint_name(fp: str) -> str:
    """'Footprints:SMD_0402' -> 'SMD_0402' (the library prefix is not part of the package)."""
    return fp.split(":", 1)[-1].strip()


def norm_value(value: str) -> str:
    """'3.3K' -> '3.3k'. Only a trailing k is folded: 'M' (mega) and 'm' (milli) stay distinct."""
    return re.sub(r"^(\d+(?:\.\d+)?)K$", r"\1k", value)


def export_rows(sch: Path = SCH) -> list[dict]:
    """One dict per placed symbol: ref, Value, Footprint, DNP (bool) and the part fields."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "raw.csv"
        cmd = ["kicad-cli", "sch", "export", "bom", "--fields", ",".join(EXPORT_FIELDS),
               "--group-by", "", "--ref-range-delimiter", "", "-o", str(out), str(sch)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not out.is_file():
            raise SystemExit(f"kicad-cli bom export failed: {r.stderr.strip() or r.stdout.strip()}")
        return parse_export(out.read_text())


def parse_export(text: str) -> list[dict]:
    rows = []
    for rec in csv.DictReader(text.splitlines()):
        ref = rec["Reference"].strip()
        value = norm_value(rec["Value"].strip())
        dnp_attr = rec.get("DNP", "").strip().lower() in ("dnp", "yes", "1", "true")
        excl = rec.get("EXCLUDE_FROM_BOM", "").strip().lower() in ("excluded", "yes", "1", "true")
        row = {"ref": ref, "Value": value, "Footprint": footprint_name(rec["Footprint"]),
               "DNP": dnp_attr or excl or value.upper() == "DNP"}
        for f in PART_FIELDS:
            row[f] = rec.get(f, "").strip()
        rows.append(row)
    return rows


def load_decisions(path: Path = DECISIONS) -> dict[str, dict]:
    if not path.is_file():
        return {}
    out = {}
    with path.open(newline="") as fh:
        for rec in csv.DictReader(fh):
            ref = (rec.get("ref") or "").strip()
            if ref:
                out[ref] = {k: (v or "").strip() for k, v in rec.items() if k != "ref"}
    return out


def merge_decisions(rows: list[dict], decisions: dict[str, dict]) -> list[dict]:
    """Fill empty part fields from decisions.csv; a schematic value is never overwritten."""
    merged = []
    for row in rows:
        row = dict(row)
        dec = decisions.get(row["ref"], {})
        for f in PART_FIELDS:
            if not row[f] and dec.get(f):
                row[f] = dec[f]
        if dec.get("DNP", "").lower() in ("1", "yes", "true", "dnp"):
            row["DNP"] = True
        merged.append(row)
    return merged


def group_rows(rows: list[dict]) -> list[dict]:
    """Group by value, footprint and part-number fields; refs naturally sorted."""
    groups: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row[k] for k in GROUP_KEYS) + (row["DNP"],)
        g = groups.setdefault(key, {**{k: row[k] for k in GROUP_KEYS}, "DNP": row["DNP"], "refs": []})
        g["refs"].append(row["ref"])
    out = []
    for g in groups.values():
        g["refs"].sort(key=ref_key)
        g["qty"] = len(g["refs"])
        g["class"] = classify(g)
        out.append(g)
    out.sort(key=lambda g: ref_key(g["refs"][0]))
    return out


def classify(g: dict) -> str:
    if g["DNP"]:
        return "dnp"
    if g.get("MPN") or g.get("LCSC") or g.get("DigiKey PN"):
        return "mpn"
    if all(prefix(r) in GENERIC_PREFIXES for r in g["refs"]):
        return "generic"
    return "nopart"


def build(sch: Path = SCH, decisions: Path = DECISIONS) -> list[dict]:
    return group_rows(merge_decisions(export_rows(sch), load_decisions(decisions)))


def write_csv(groups: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["class", "refs", "qty", "value", "footprint", "MPN", "Manufacturer", "LCSC",
                    "DigiKey PN"])
        for g in groups:
            w.writerow([g["class"], ";".join(g["refs"]), g["qty"], g["Value"], g["Footprint"],
                        g["MPN"], g["Manufacturer"], g["LCSC"], g["DigiKey PN"]])


def summary(groups: list[dict]) -> str:
    counts = {c: sum(1 for g in groups if g["class"] == c) for c in CLASSES}
    refs = sum(g["qty"] for g in groups)
    return (f"{len(groups)} groups, {refs} refs; "
            + ", ".join(f"{c} {n}" for c, n in counts.items()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schematic", type=Path, default=SCH)
    ap.add_argument("--decisions", type=Path, default=DECISIONS)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    groups = build(a.schematic, a.decisions)
    write_csv(groups, a.out)
    print(summary(groups))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
