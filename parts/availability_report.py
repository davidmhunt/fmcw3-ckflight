#!/usr/bin/env python3
"""Repeatable parts-availability check for both boards: stock against the build need (par-14).

usage: parts/availability_report.py [--refresh] [--offline] [--boards N] [--spares N] [--check]
                                    [--targets NAME] [--parts parts/final_parts.csv]
                                    [--inventory parts/inventory.csv] [--out parts/out/availability]

Reads parts/final_parts.csv (fitted rows only) and parts/inventory.csv. Need per line is
refs per board x boards (`board_quantity` of the target set, or --boards) plus spares: --spares
(default 2) for parts that are not in the JLC Basic library, none for Basic parts. Per route:

  jlc-stock                  JLC stock (local JLC database, by LCSC number) against the need
  jlc-library                inventory first (parts/inventory.csv, shared between lines that
                             use the same LCSC number, 2rx first), then JLC stock
  jlc-sourcing, hand-solder  DigiKey stock against the need (the JLC sourcing service buys from
                             distributors); answers are cached under parts/cache/digikey/,
                             --offline uses only the cache
  (no route)                 mechanical or not purchasable: status "no part"

Status: short (stock below the need), thin (covers it, but stock - need is below 3 x need, that
is stock under 4 x need), ok, unknown (no data: not in the database, or no DigiKey answer in the
cache). --refresh downloads a fresh copy of the JLC database first.

The JLC database is a daily snapshot that can lag the live site, so short and thin JLC lines are
to be checked on the JLC page (pre-order status is not in the database). Every short or thin
line prints its fallback from final_parts.csv.

Output goes to a new folder parts/out/availability/<YYYY-MM-DD>/ (a second run the same day gets
-2, then -3): lines.csv, summary.json, changes.csv (against the latest earlier snapshot) and
provenance.md. An earlier snapshot is never touched.

--check exits 1 on a malformed input row or a line with no data source (a purchasable line with
no LCSC number for a JLC route, or no MPN and no DigiKey number for a DigiKey route). A planned
part that is not named yet (a `decided` change with no part number, e.g. R19 named by par-12)
is reported as unknown but is not a failure.

API: need_qty(per_board, boards, spares); classify(stock, need); evaluate(row, ctx, ...) -> dict;
     check_inputs(rows, inventory) -> [str]; snapshot_dir(base, date) -> Path;
     previous_snapshot(base, new) -> Path|None; diff_lines(old, new) -> [dict].
Nothing here writes under kicad/ and nothing logs in, quotes or orders: it reads stock data only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))

import final_parts as fp  # noqa: E402

OUT = HERE / "out" / "availability"
LAG_NOTE = ("The JLC database is a daily snapshot that can lag the live site: check every short "
            "and thin JLC line on the JLC page (pre-order status is not in the database).")
THIN_FACTOR = 3
LINE_COLS = ["board", "refs", "role", "chosen_mpn", "lcsc", "route", "per_board", "boards",
             "spares", "need", "source", "library", "jlc_stock", "inventory", "inventory_used",
             "dk_stock", "dk_status", "stock", "status", "fallback", "note"]
STATUS_ORDER = {"short": 0, "thin": 1, "unknown": 2, "ok": 3, "no part": 4}
JLC_ROUTES = ("jlc-stock", "jlc-library")
DK_ROUTES = ("jlc-sourcing", "hand-solder")


# ---------------------------------------------------------------- arithmetic

def need_qty(per_board: int, boards: int, spares: int) -> int:
    return per_board * boards + spares


def classify(stock, need: int) -> str:
    """short: stock < need; thin: covers it with less than 3 x need left; ok; unknown: no data."""
    if stock is None:
        return "unknown"
    if stock < need:
        return "short"
    if stock - need < THIN_FACTOR * need:
        return "thin"
    return "ok"


# ---------------------------------------------------------------- input checks

def check_inputs(rows: list[dict], inventory: list[dict]) -> list[str]:
    """Problems with the input rows and with data sources, one string each (fitted rows only for
    the data-source test)."""
    problems: list[str] = []
    if rows and (missing := [c for c in fp.COLUMNS if c not in rows[0]]):
        return [f"final_parts.csv lacks columns {missing}"]
    for i, r in enumerate(inventory, start=2):
        try:
            if int(r.get("qty", "")) < 0:
                raise ValueError
        except ValueError:
            problems.append(f"inventory.csv line {i}: qty {r.get('qty')!r} is not a whole number")
        if not r.get("lcsc", "").strip():
            problems.append(f"inventory.csv line {i}: no lcsc")
    for i, r in enumerate(rows, start=2):
        where = f"final_parts.csv line {i} ({r['board']} {r['refs'][:30]})"
        for col, allowed in (("board", set(fp.BOARDS)), ("route", fp.ROUTES), ("fitted", fp.FITTED)):
            if r[col] not in allowed:
                problems.append(f"{where}: {col} {r[col]!r} is not one of {sorted(allowed)}")
        if not fp.split_refs(r["refs"]):
            problems.append(f"{where}: no refs")
        if r["fitted"] != "yes":
            continue
        if r["route"] in JLC_ROUTES and not r["lcsc"].strip() and not planned_unnamed(r):
            problems.append(f"{where}: route {r['route']} but no LCSC number: no data source")
        if r["route"] in DK_ROUTES and not (r["chosen_mpn"].strip() or r["digikey_pn"].strip()):
            problems.append(f"{where}: route {r['route']} but no MPN or DigiKey number: no data source")
    return problems


def planned_unnamed(r: dict) -> bool:
    """A change that is decided but whose part is not named yet (no LCSC, no DigiKey number)."""
    return (r["change"] != "none" and r["status"] != "applied" and not r["lcsc"].strip()
            and not r["digikey_pn"].strip())


# ---------------------------------------------------------------- one line

def evaluate(row: dict, boards: int, spares: int, jlc, dk, inv_left: dict) -> dict:
    """One fitted final_parts row -> a lines.csv record.

    `jlc(lcsc) -> {'stock': int, 'library': str} | None`; `dk(row, need) -> (stock|None, status)`;
    `inv_left` {lcsc: qty still unallocated}, updated when a jlc-library line takes inventory."""
    refs = fp.split_refs(row["refs"])
    lcsc = row["lcsc"].strip()
    route = row["route"]
    j = jlc(lcsc) if lcsc else None
    library = j["library"] if j else ""
    extra = 0 if library == "Basic" else spares
    need = need_qty(len(refs), boards, extra)
    out = {"board": row["board"], "refs": row["refs"], "role": row["role"],
           "chosen_mpn": row["chosen_mpn"], "lcsc": lcsc, "route": route, "per_board": len(refs),
           "boards": boards, "spares": extra, "need": need, "source": "", "library": library,
           "jlc_stock": "" if not j else j["stock"], "inventory": "", "inventory_used": 0,
           "dk_stock": "", "dk_status": "", "stock": "", "status": "", "fallback": row["fallback"],
           "note": ""}
    if not route:
        out.update(status="no part", source="none", need=0, spares=0, note="not a purchasable part")
        return out
    stock = None
    if route in JLC_ROUTES:
        out["source"] = "jlc" if route == "jlc-stock" else "inventory+jlc"
        if not lcsc:
            out["note"] = "part not named yet: no LCSC number"
        elif j is None:
            out["note"] = "LCSC number not in the JLC database"
        else:
            stock = j["stock"]
            if route == "jlc-library":
                held = inv_left.get(lcsc, 0)
                out["inventory"] = held
                used = min(need, held)
                inv_left[lcsc] = held - used
                out["inventory_used"] = used
                stock += held
    else:
        out["source"] = "digikey"
        dstock, dstatus = dk(row, need)
        out["dk_stock"] = "" if dstock is None else dstock
        out["dk_status"] = dstatus
        stock = dstock
        if stock is None:
            out["note"] = f"no DigiKey data ({dstatus})"
    out["stock"] = "" if stock is None else stock
    out["status"] = classify(stock, need)
    return out


def sort_key(rec: dict):
    return (STATUS_ORDER.get(rec["status"], 9), rec["board"], rec["refs"])


# ---------------------------------------------------------------- snapshots

def _snap_key(p: Path):
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:-(\d+))?", p.name)
    return (m.group(1), int(m.group(2) or 1)) if m else None


def snapshots(base: Path) -> list[Path]:
    """Existing snapshot folders, oldest first."""
    if not base.is_dir():
        return []
    return sorted((p for p in base.iterdir() if p.is_dir() and _snap_key(p)), key=_snap_key)


def snapshot_dir(base: Path, date: dt.date) -> Path:
    """A new folder name for `date`: <date>, then <date>-2, -3...; never an existing one."""
    path = base / date.isoformat()
    n = 2
    while path.exists():
        path = base / f"{date.isoformat()}-{n}"
        n += 1
    return path


def previous_snapshot(base: Path, new: Path | None = None) -> Path | None:
    """Latest snapshot other than `new` that has a lines.csv."""
    olds = [p for p in snapshots(base) if p != new and (p / "lines.csv").is_file()]
    return olds[-1] if olds else None


def read_lines(path: Path) -> list[dict]:
    with (Path(path) / "lines.csv").open(newline="") as fh:
        return list(csv.DictReader(fh))


def diff_lines(old: list[dict], new: list[dict]) -> list[dict]:
    """Lines whose status or stock changed, plus lines that appeared or disappeared."""
    key = lambda r: (r["board"], r["refs"])  # noqa: E731
    o, n = {key(r): r for r in old}, {key(r): r for r in new}
    out = []
    for k in sorted(set(o) | set(n)):
        a, b = o.get(k), n.get(k)
        if a and b:
            if (a["status"], str(a["stock"])) == (b["status"], str(b["stock"])):
                continue
            what = "changed"
        else:
            what = "new line" if b else "removed line"
        out.append({"board": k[0], "refs": k[1], "change": what,
                    "old_status": a["status"] if a else "", "new_status": b["status"] if b else "",
                    "old_stock": a["stock"] if a else "", "new_stock": b["stock"] if b else "",
                    "need": (b or a)["need"]})
    return out


CHANGE_COLS = ["board", "refs", "change", "old_status", "new_status", "old_stock", "new_stock", "need"]


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summarize(lines: list[dict], jlc_db_date: str, dk_mode: str, boards: int, spares: int,
              previous: str, changes: int) -> dict:
    by_board: dict[str, dict[str, int]] = {}
    for r in lines:
        by_board.setdefault(r["board"], Counter())[r["status"]] += 1
    total = Counter(r["status"] for r in lines)
    return {"jlc_database_date": jlc_db_date, "digikey": dk_mode, "boards": boards,
            "spares": spares, "lines": len(lines), "counts": dict(total),
            "counts_by_board": {b: dict(c) for b, c in sorted(by_board.items())},
            "short": total["short"], "thin": total["thin"], "unknown": total["unknown"],
            "ok": total["ok"], "previous_snapshot": previous, "changes_since_previous": changes,
            "lag_note": LAG_NOTE}


def write_snapshot(base: Path, date: dt.date, lines: list[dict], summary_extra: dict,
                   command: str) -> Path:
    path = snapshot_dir(base, date)
    path.mkdir(parents=True)          # raises if it exists: never overwrite
    prev = previous_snapshot(base, path)
    changes = diff_lines(read_lines(prev), lines) if prev else []
    summary = summarize(lines, summary_extra["jlc_db_date"], summary_extra["dk_mode"],
                        summary_extra["boards"], summary_extra["spares"],
                        prev.name if prev else "", len(changes))
    summary["snapshot"] = path.name
    write_csv(path / "lines.csv", LINE_COLS, lines)
    write_csv(path / "changes.csv", CHANGE_COLS, changes)
    (path / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (path / "provenance.md").write_text(
        f"- command: {command}\n"
        f"- snapshot: {path.name}\n"
        f"- JLC database file date: {summary_extra['jlc_db_date']} (daily snapshot, can lag the live site)\n"
        f"- DigiKey: {summary_extra['dk_mode']}\n"
        f"- boards: {summary_extra['boards']}, spares: {summary_extra['spares']} per non-Basic line\n"
        f"- previous snapshot: {prev.name if prev else 'none'}\n"
        f"- {LAG_NOTE}\n")
    return path


# ---------------------------------------------------------------- command line

def make_dk(offline: bool):
    import bom
    import check_digikey as dkm
    client = None
    if not offline:
        try:
            client = dkm.Client.from_env()
        except dkm.DigiKeyError as e:
            print(f"DigiKey keys not available, using cached answers only: {e}", file=sys.stderr)
    return bom.CachedDigiKey(client), ("cache only" if client is None else "live, cached under parts/cache/digikey/")


def dk_lookup(cdk):
    import check_digikey as dkm

    def look(row, need):
        group = {"class": "mpn", "refs": fp.split_refs(row["refs"]), "MPN": row["chosen_mpn"].strip(),
                 "DigiKey PN": row["digikey_pn"].strip(), "Value": row["chosen_mpn"], "Footprint": "",
                 "LCSC": "", "qty": len(fp.split_refs(row["refs"]))}
        try:
            res = dkm.check_group(cdk, group, need)
        except RuntimeError as e:   # OfflineMiss and DigiKeyError
            return None, "not cached" if "no cached" in str(e) else "error"
        if res["dk_match"] == "exact":
            return int(res["dk_stock"] or 0), res["dk_status"]
        return 0, res["dk_status"]  # DigiKey has no such part
    return look


def jlc_lookup(db):
    def look(lcsc):
        recs = db.by_lcsc(lcsc)
        return {"stock": recs[0]["stock"], "library": recs[0]["library"]} if recs else None
    return look


def print_report(lines: list[dict], summary: dict, path: Path) -> None:
    print(f"snapshot {path.name}: {summary['lines']} lines, {summary['boards']} boards, "
          f"JLC database {summary['jlc_database_date']}, DigiKey {summary['digikey']}")
    for b, c in summary["counts_by_board"].items():
        print(f"  {b}: " + ", ".join(f"{s} {c.get(s, 0)}" for s in STATUS_ORDER))
    flagged = [r for r in lines if r["status"] in ("short", "thin")]
    for r in flagged:
        print(f"{r['status'].upper():6} {r['board']} {r['refs'][:24]:24} {r['chosen_mpn'][:24]:24} "
              f"{r['route']:12} need {r['need']} stock {r['stock']} inventory {r['inventory'] or 0}")
        print(f"       fallback: {r['fallback']}")
    if not flagged:
        print("no short or thin lines")
    unknown = [r for r in lines if r["status"] == "unknown"]
    if unknown:
        print(f"{len(unknown)} unknown line(s) (no data): " +
              "; ".join(f"{r['board']} {r['refs'][:14]}" for r in unknown[:8]) +
              (" ..." if len(unknown) > 8 else ""))
    print(LAG_NOTE)
    print(f"wrote {path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--targets", default="default", help="target set giving board_quantity")
    ap.add_argument("--boards", type=int, default=None, help="override board_quantity")
    ap.add_argument("--spares", type=int, default=2,
                    help="spares per line for parts not in the JLC Basic library (default 2)")
    ap.add_argument("--parts", type=Path, default=fp.PARTS)
    ap.add_argument("--inventory", type=Path, default=fp.INVENTORY)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--cache", type=Path, default=None, help="JLCPCB database cache directory")
    ap.add_argument("--check", action="store_true",
                    help="validate the inputs only: exit 1 on a malformed input row or a line with no "
                         "data source, else exit 0; writes no snapshot")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--refresh", action="store_true", help="download the JLCPCB database again")
    g.add_argument("--offline", action="store_true", help="caches only; never touch the network")
    a = ap.parse_args(argv)

    rows, inventory = fp.load_parts(a.parts), fp.load_inventory(a.inventory)
    problems = check_inputs(rows, inventory)
    for p in problems:
        print(f"input: {p}", file=sys.stderr)
    if problems and (a.check or any("lacks columns" in p for p in problems)):
        return 1
    if a.check:     # validate only: a check run must not add a snapshot (it would become "latest")
        print(f"inputs ok: {sum(r['fitted'] == 'yes' for r in rows)} fitted lines, no snapshot written")
        return 0

    import bom
    import check_jlc as jl
    boards = bom.board_count(a.targets, a.boards)
    cache = a.cache or jl.CACHE
    try:
        db_path = jl.ensure_db(cache, a.offline, a.refresh)
        db = jl.Db(db_path)
    except jl.JlcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    db_date = dt.date.fromtimestamp(db_path.stat().st_mtime).isoformat()
    cdk, dk_mode = make_dk(a.offline)
    dk, jlc = dk_lookup(cdk), jlc_lookup(db)

    inv_left: dict[str, int] = {}
    for r in inventory:
        if r.get("lcsc", "").strip():
            inv_left[r["lcsc"].strip()] = inv_left.get(r["lcsc"].strip(), 0) + int(r["qty"])
    lines = [evaluate(r, boards, a.spares, jlc, dk, inv_left)
             for r in rows if r["fitted"] == "yes"]
    lines.sort(key=sort_key)

    command = "parts/availability_report.py " + " ".join(argv if argv is not None else sys.argv[1:])
    path = write_snapshot(a.out, dt.date.today(), lines,
                          {"jlc_db_date": db_date, "dk_mode": dk_mode, "boards": boards,
                           "spares": a.spares}, command.strip())
    summary = json.loads((path / "summary.json").read_text())
    print_report(lines, summary, path)
    if summary["previous_snapshot"]:
        print(f"{summary['changes_since_previous']} line(s) changed since {summary['previous_snapshot']}"
              f" (see {path / 'changes.csv'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
