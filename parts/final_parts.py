#!/usr/bin/env python3
"""Check the one parts record for both boards and write the report tables (par-13).

usage: parts/final_parts.py [--check] [--parts parts/final_parts.csv]
                            [--inventory parts/inventory.csv] [--manifest datasheets/manifest.yaml]
                            [--build analysis/13_parts_final/build] [--offline]

Loads parts/final_parts.csv (one row per ref group and board, `2rx` = kicad/, `1rx` = kicad-1rx/)
and parts/inventory.csv, and checks:

  evidence       every id in a row's `evidence` ("id p.N; id2") exists in datasheets/manifest.yaml
  lcsc           every `lcsc` exists in the local JLC database (parts/cache/jlcpcb/)
  refs           every ref placed on a board (headless BOM export of its schematic, merged with
                 parts/decisions.csv like parts/bom.py) is in exactly one row for that board, a
                 row names no ref the board lacks, and DNP parts sit in rows with `fitted` no
                 (and fitted parts in rows with `fitted` yes). Rows not yet `applied` are planned
                 changes (applied_by rx1-03, par-12): the board may still differ, so their
                 fitted flag is not compared and a new ref (C992, R990...) need not exist yet
  change         a row whose `change` is not `none` has a `reason` and an `evidence`, and if the
                 evidence cites datasheet PDFs at least one carries a page ("id p.N"); ids of
                 data files (S-parameters, models) have no pages
  status         `applied` means nothing is left to write (no part to buy, or DNP as upstream):
                 a part whose MPN/LCSC is not yet in the schematic is `decided`, applied_by par-04
  library        a `jlc-library` row has an inventory row for its `lcsc`
  columns        the required columns exist and `board`, `change`, `route`, `status`, `fitted`
                 hold only the allowed values

Exit 1 on any failure. Without --check the problems are still printed but the exit is 0.
Either way it writes CSV tables for analysis/13_parts_final/ into --build: by_route.csv,
by_change.csv, by_status.csv, substitutions.csv (change not none), side_by_side.csv (one line per
role with both boards' chosen part), inventory.csv. Nothing under kicad/ or kicad-1rx/ is written.

API: load_parts(path) -> [dict]; load_inventory(path) -> [dict]; manifest_ids(path) -> set;
     evidence_ids(text) -> [id]; check(rows, inventory, manifest, lcsc_exists, placed) -> [str];
     placed_refs(project) -> {ref: dnp bool}; write_tables(rows, inventory, build).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
sys.path.insert(0, str(ROOT / "tools"))

PARTS = ROOT / "parts" / "final_parts.csv"
INVENTORY = ROOT / "parts" / "inventory.csv"
MANIFEST = ROOT / "datasheets" / "manifest.yaml"
BUILD = ROOT / "analysis" / "13_parts_final" / "build"
BOARDS = {"2rx": "kicad", "1rx": "kicad-1rx"}

COLUMNS = ["board", "refs", "role", "original_mpn", "chosen_mpn", "manufacturer", "lcsc",
           "digikey_pn", "change", "route", "reason", "evidence", "analysis", "fallback",
           "applied_by", "status", "fitted"]
INV_COLUMNS = ["mpn", "lcsc", "qty", "date", "held", "for"]
CHANGES = {"none", "fields", "footprint", "design"}
ROUTES = {"jlc-stock", "jlc-library", "jlc-sourcing", "hand-solder", ""}
STATUSES = {"decided", "pending review", "applied"}
FITTED = {"yes", "no"}


def load_parts(path: Path = PARTS) -> list[dict]:
    with Path(path).open(newline="") as fh:
        return list(csv.DictReader(fh))


def load_inventory(path: Path = INVENTORY) -> list[dict]:
    with Path(path).open(newline="") as fh:
        return list(csv.DictReader(fh))


def manifest_ids(path: Path = MANIFEST) -> set[str]:
    import yaml
    data = yaml.safe_load(Path(path).read_text())
    return {e["id"] for e in data.get("entries", []) if e.get("id")}


def evidence_ids(text: str) -> list[str]:
    """'id-a p.5; id-b' -> ['id-a', 'id-b']: a trailing page ('p.5', 'p.5-7', 'p.5,7') is dropped."""
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if part:
            out.append(re.sub(r"\s+pp?\.?\s*\S*$", "", part))
    return out


def split_refs(text: str) -> list[str]:
    return [r.strip() for r in (text or "").split(";") if r.strip()]


def placed_refs(project: str) -> dict[str, bool]:
    """{ref: dnp} for every symbol of the project's schematic, headless (kicad-cli)."""
    import bom
    import project as pj
    proj = pj.resolve_or_exit(project)
    rows = bom.merge_decisions(bom.export_rows(proj.sch), bom.load_decisions(bom.DECISIONS))
    return {r["ref"]: bool(r["DNP"]) for r in rows}


def manifest_pdf_ids(path: Path = MANIFEST) -> set[str]:
    """Manifest ids whose file is a PDF (the only ones that have pages to cite)."""
    import yaml
    data = yaml.safe_load(Path(path).read_text())
    return {e["id"] for e in data.get("entries", [])
            if e.get("id") and str(e.get("file", "")).lower().endswith(".pdf")}


def has_page(part: str) -> bool:
    return bool(re.search(r"\s+pp?\.?\s*\S+$", part.strip()))


def check(rows: list[dict], inventory: list[dict], manifest: set[str], lcsc_exists,
          placed: dict[str, dict[str, bool]] | None, pdf_ids: set[str] | None = None) -> list[str]:
    """Problems found, one string each. `lcsc_exists(code) -> bool`; `placed` is
    {board: {ref: dnp}} (None skips the ref checks); `pdf_ids` is the set of manifest ids that are
    PDFs (None skips the page check)."""
    problems: list[str] = []
    if rows and (missing := [c for c in COLUMNS if c not in rows[0]]):
        return [f"final_parts.csv lacks columns {missing}"]
    inv_lcsc = {r["lcsc"].strip() for r in inventory if r.get("lcsc", "").strip()}
    for i, r in enumerate(rows, start=2):
        where = f"final_parts.csv line {i} ({r['board']} {r['refs'][:30]})"
        for col, allowed in (("board", set(BOARDS)), ("change", CHANGES), ("route", ROUTES),
                             ("status", STATUSES), ("fitted", FITTED)):
            if r[col] not in allowed:
                problems.append(f"{where}: {col} {r[col]!r} is not one of {sorted(allowed)}")
        for ev in evidence_ids(r["evidence"]):
            if ev not in manifest:
                problems.append(f"{where}: evidence id {ev!r} is not in datasheets/manifest.yaml")
        lcsc = r["lcsc"].strip()
        if lcsc and not lcsc_exists(lcsc):
            problems.append(f"{where}: lcsc {lcsc} is not in the JLC database")
        if r["change"] != "none":
            if not r["reason"].strip():
                problems.append(f"{where}: change {r['change']} has no reason")
            if not r["evidence"].strip():
                problems.append(f"{where}: change {r['change']} has no evidence")
            elif pdf_ids is not None:
                parts = [p.strip() for p in r["evidence"].split(";") if p.strip()]
                pdfs = [p for p in parts if evidence_ids(p)[0] in pdf_ids]
                if pdfs and not any(has_page(p) for p in pdfs):
                    problems.append(f"{where}: change {r['change']} cites datasheet PDFs but no page "
                                    f"({'; '.join(pdfs)[:80]}): give 'id p.N'")
        if r["route"] == "jlc-library" and (not lcsc or lcsc not in inv_lcsc):
            problems.append(f"{where}: jlc-library row has no inventory row for lcsc {lcsc or '(none)'}")
    if placed is not None:
        for board, refs in placed.items():
            seen: dict[str, list[dict]] = {}
            for r in rows:
                if r["board"] == board:
                    for ref in split_refs(r["refs"]):
                        seen.setdefault(ref, []).append(r)
            for ref, dnp in sorted(refs.items()):
                got = seen.get(ref, [])
                if not got:
                    problems.append(f"{board} {ref}: placed on the board but in no row")
                elif len(got) > 1:
                    problems.append(f"{board} {ref}: in {len(got)} rows")
                elif got[0]["status"] != "applied" and got[0]["change"] != "none":
                    continue    # a planned change (rx1-03, par-12): the board may still differ
                elif dnp and got[0]["fitted"] != "no":
                    problems.append(f"{board} {ref}: DNP on the board but its row says fitted {got[0]['fitted']}")
                elif not dnp and got[0]["fitted"] == "no":
                    problems.append(f"{board} {ref}: fitted on the board but its row says fitted no")
            for ref in sorted(set(seen) - set(refs)):
                if (any(r["status"] == "applied" or r["change"] == "none" for r in seen[ref])
                        or not any(r["applied_by"] for r in seen[ref])):
                    problems.append(f"{board} {ref}: in a row but not placed on the board")
    return problems


# ---------------------------------------------------------------- report tables

def _write(path: Path, header: list[str], lines: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(lines)


def _count_by(rows: list[dict], key: str, order: list[str] | None = None) -> list[list]:
    """[value, 2rx rows, 2rx refs, 1rx rows, 1rx refs] per value of `key` (fitted parts only count
    toward route; `fitted` no rows are their own value)."""
    vals = sorted({r[key] for r in rows}, key=lambda v: (order.index(v) if order and v in order else 99, v))
    out = []
    for v in vals:
        line = [v or "(none)"]
        for b in BOARDS:
            sel = [r for r in rows if r["board"] == b and r[key] == v]
            line += [len(sel), sum(len(split_refs(r["refs"])) for r in sel)]
        out.append(line)
    return out


def write_tables(rows: list[dict], inventory: list[dict], build: Path = BUILD) -> list[Path]:
    build = Path(build)
    head = ["value", "2rx_rows", "2rx_refs", "1rx_rows", "1rx_refs"]
    fitted = [r for r in rows if r["fitted"] == "yes"]
    out = []

    def emit(name, header, lines):
        _write(build / name, header, lines)
        out.append(build / name)

    emit("by_route.csv", ["route"] + head[1:], _count_by(fitted, "route", ["jlc-stock", "jlc-library",
                                                                           "jlc-sourcing", "hand-solder"]))
    emit("by_change.csv", ["change"] + head[1:], _count_by(rows, "change", ["none", "fields", "footprint", "design"]))
    emit("by_status.csv", ["status"] + head[1:], _count_by(rows, "status", ["applied", "decided", "pending review"]))
    emit("not_fitted.csv", ["board", "refs", "role", "change", "reason"],
         [[r["board"], r["refs"], r["role"], r["change"], r["reason"]] for r in rows if r["fitted"] == "no"])
    subs = [r for r in rows if r["change"] != "none"]
    cols = ["board", "refs", "role", "original_mpn", "chosen_mpn", "manufacturer", "lcsc", "change", "route",
            "reason", "evidence", "analysis", "fallback", "applied_by", "status", "fitted"]
    emit("substitutions.csv", cols, [[r[c] for c in cols] for r in subs])

    # side by side: one line per (role, original, chosen) with the refs on each board
    keyed: dict[tuple, dict] = {}
    for r in rows:
        k = (r["role"], r["original_mpn"], r["chosen_mpn"])
        keyed.setdefault(k, {}).setdefault(r["board"], []).extend(split_refs(r["refs"]))
    emit("side_by_side.csv", ["role", "original_mpn", "chosen_mpn", "2rx_refs", "1rx_refs"],
         [[*k, ";".join(v.get("2rx", [])), ";".join(v.get("1rx", []))] for k, v in keyed.items()])
    emit("inventory.csv", INV_COLUMNS, [[r.get(c, "") for c in INV_COLUMNS] for r in inventory])
    return out


# ---------------------------------------------------------------- command line

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when a check fails")
    ap.add_argument("--parts", type=Path, default=PARTS)
    ap.add_argument("--inventory", type=Path, default=INVENTORY)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--build", type=Path, default=BUILD)
    ap.add_argument("--offline", action="store_true",
                    help="never download the JLC database (it is only used when cached anyway)")
    a = ap.parse_args(argv)

    import check_jlc as jl
    rows, inventory = load_parts(a.parts), load_inventory(a.inventory)
    try:
        db = jl.Db(jl.ensure_db(jl.CACHE, offline=a.offline))
    except jl.JlcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    placed = {b: placed_refs(d) for b, d in BOARDS.items()}
    problems = check(rows, inventory, manifest_ids(a.manifest), lambda c: bool(db.by_lcsc(c)), placed,
                     manifest_pdf_ids(a.manifest))
    for p in problems:
        print(p)
    tables = write_tables(rows, inventory, a.build)
    c = Counter(r["board"] for r in rows)
    print(f"{len(rows)} rows ({c['2rx']} 2rx, {c['1rx']} 1rx), {len(inventory)} inventory rows; "
          f"wrote {len(tables)} tables in {a.build}")
    print("final parts record is consistent" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems and a.check else 0


if __name__ == "__main__":
    sys.exit(main())
