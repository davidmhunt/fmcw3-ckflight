#!/usr/bin/env python3
"""Stock watch for hard-to-source parts: can JLCPCB place them now?

usage: parts/watch.py [--offline] [--refresh] [--check] [--targets NAME] [--boards N]
                      [--watch parts/watch.csv] [--out parts/out/watch.csv] [--cache DIR]
                      [--project DIR]

Reads parts/watch.csv (one row per watched MPN, see parts/README.md), then for each row prints
  - JLC stock and library type (the local JLCPCB parts database; --refresh downloads a fresh copy),
  - DigiKey stock, unit price and lifecycle (parts/check_digikey.py; answers are cached under
    parts/cache/digikey/, --offline uses only the cache),
  - "JLC can place now" when the JLC stock of an exact match covers qty_per_board x boards.
and writes parts/out/watch.csv. Boards default to board_quantity of the target set.

--check exits 1 on a malformed watch row (bad quantity, role or drop_in value, duplicate line)
or on a drop-in row without evidence (a substitute needs evidence_id and evidence_page).

A "JLC can place now" line for a `self` row means the part the board is designed around is now
JLC-placeable: move that line from consignment to JLC. For a `substitute` row it only means the
substitute is in stock: read drop_in and note first; choosing it is a design decision.

API: load_watch(path) -> [row]; validate(rows) -> [problem]; evaluate(row, db, dk, boards) -> dict;
     can_place(jlc, need) -> bool. Nothing here writes under kicad/, and the agent never quotes or
     orders at JLCPCB or DigiKey: this only reads their public stock data.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

WATCH = HERE / "watch.csv"
OUT = HERE / "out" / "watch.csv"
WATCH_COLS = ["mpn", "refdes", "qty_per_board", "role", "jlc_lcsc", "why_watched", "drop_in",
              "evidence_id", "evidence_page", "note"]
EXTRA_COLS = ["need", "jlc_can_place"]
ROLES = ("self", "substitute")
DROP_IN = ("self", "yes", "pins-only", "no", "unverified")
PLACE_MSG = "JLC can place now"


def load_watch(path=WATCH):
    with Path(path).open(newline="") as f:
        return [{k: (v or "").strip() for k, v in r.items() if k is not None}
                for r in csv.DictReader(f)]


def validate(rows, header=None):
    """Problems found in the watch rows, as strings; empty when well formed."""
    bad = []
    if header is not None:
        missing = [c for c in WATCH_COLS if c not in header]
        if missing:
            return [f"missing columns: {', '.join(missing)}"]
    seen = set()
    for i, r in enumerate(rows, 2):  # line 1 is the header
        where = f"line {i} ({r.get('mpn') or '?'})"
        if not r.get("mpn"):
            bad.append(f"{where}: empty mpn")
        if not r.get("refdes"):
            bad.append(f"{where}: empty refdes")
        try:
            if int(r.get("qty_per_board", "")) < 1:
                raise ValueError
        except ValueError:
            bad.append(f"{where}: qty_per_board must be an integer of at least 1")
        if r.get("role") not in ROLES:
            bad.append(f"{where}: role must be one of {', '.join(ROLES)}")
        if r.get("drop_in") not in DROP_IN:
            bad.append(f"{where}: drop_in must be one of {', '.join(DROP_IN)}")
        if not r.get("why_watched"):
            bad.append(f"{where}: empty why_watched")
        if r.get("role") == "self" and r.get("drop_in") != "self":
            bad.append(f"{where}: a self row has drop_in 'self'")
        if r.get("role") == "substitute":
            if r.get("drop_in") == "self":
                bad.append(f"{where}: a substitute row cannot have drop_in 'self'")
            elif not (r.get("evidence_id") and r.get("evidence_page")):
                bad.append(f"{where}: drop-in row without evidence "
                           "(evidence_id and evidence_page)")
        lcsc = r.get("jlc_lcsc", "")
        if lcsc and not (lcsc[0] in "Cc" and lcsc[1:].isdigit()):
            bad.append(f"{where}: jlc_lcsc {lcsc!r} is not an LCSC number (C123)")
        key = (r.get("mpn"), r.get("refdes"))
        if key in seen:
            bad.append(f"{where}: duplicate mpn and refdes")
        seen.add(key)
    return bad


def can_place(jlc, need):
    """True when JLC holds an exact match in stock for `need` (a near match never counts)."""
    return (jlc.get("jlc_match") == "exact" and isinstance(jlc.get("jlc_stock"), int)
            and jlc["jlc_stock"] >= need > 0)


def evaluate(row, db, dk, boards):
    """One watch row -> the row plus need, jlc_* and dk_* results. `db` is a check_jlc.Db (or
    None: not checked), `dk` a search client for check_digikey (or None: not checked)."""
    import check_digikey as dkm
    import check_jlc as jl
    need = int(row["qty_per_board"]) * boards
    group = {"class": "mpn", "refs": row["refdes"].split(";"), "MPN": row["mpn"],
             "LCSC": row.get("jlc_lcsc", ""), "DigiKey PN": "", "Value": row["mpn"],
             "Footprint": "", "qty": int(row["qty_per_board"])}
    if db is None:
        jlc = jl.blank()
        jlc["jlc_status"] = "Not-checked"
    else:
        jlc = jl.check_group(db, group, need)
    if dk is None:
        res = dkm.blank()
        res["dk_status"] = "Not-checked"
    else:
        try:
            res = dkm.check_group(dk, group, need)
        except RuntimeError as e:  # OfflineMiss and DigiKeyError both end here
            res = dkm.blank()
            res["dk_status"] = "Not-cached" if "no cached" in str(e) else "Error"
            if res["dk_status"] == "Error":
                res["dk_query"] = str(e)[:120]
    out = dict(row)
    out.update(need=need, jlc_can_place="yes" if can_place(jlc, need) else "no")
    out.update(jlc)
    out.update(res)
    return out


def make_dk(offline):
    """Cached DigiKey search; live only when not offline and the keys are present."""
    import bom
    import check_digikey as dkm
    client = None
    if not offline:
        try:
            client = dkm.Client.from_env()
        except dkm.DigiKeyError as e:
            print(f"DigiKey keys not available, using cached answers only: {e}", file=sys.stderr)
    return bom.CachedDigiKey(client)


def fmt_price(v):
    return "" if v in ("", None) else f"{float(v):.2f}"


def show(results):
    print(f"{'mpn':20} {'refdes':10} {'role':10} {'drop_in':10} {'jlc':>7} {'lib':9} "
          f"{'dk':>7} {'dk$':>7} {'life':9} need  verdict")
    for r in results:
        verdict = PLACE_MSG if r["jlc_can_place"] == "yes" else ""
        print(f"{r['mpn'][:20]:20} {r['refdes'][:10]:10} {r['role']:10} {r['drop_in']:10} "
              f"{str(r['jlc_stock']):>7} {r['jlc_library']:9} {str(r['dk_stock']):>7} "
              f"{fmt_price(r['dk_unit_price']):>7} {(r['dk_lifecycle'] or r['dk_status']):9} "
              f"{r['need']:>4}  {verdict}")


def write_out(results, path):
    import check_digikey as dkm
    import check_jlc as jl
    cols = WATCH_COLS + EXTRA_COLS + jl.RESULT_COLS + dkm.RESULT_COLS
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Can JLCPCB place the watched parts now?")
    ap.add_argument("--targets", default="default", help="target set giving board_quantity")
    ap.add_argument("--boards", type=int, help="override board_quantity")
    ap.add_argument("--watch", type=Path, default=WATCH)
    ap.add_argument("--out", type=Path, default=None,
                    help="default: parts/out/watch.csv, or parts/out/<tag>/watch.csv for "
                         "--project kicad-<tag>")
    import bom
    bom.add_project_arg(ap)
    ap.add_argument("--cache", type=Path, default=None, help="JLCPCB database cache directory")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on a malformed row or a drop-in row without evidence")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--refresh", action="store_true", help="download the JLCPCB database again")
    g.add_argument("--offline", action="store_true", help="caches only; never touch the network")
    a = ap.parse_args(argv)
    a.out = a.out or bom.project_from(a).parts_out / "watch.csv"

    with a.watch.open(newline="") as f:
        header = csv.DictReader(f).fieldnames or []
    rows = load_watch(a.watch)
    problems = validate(rows, header)
    if problems:
        for p in problems:
            print(f"watch: {p}", file=sys.stderr)
        if a.check:
            return 1
    if "missing columns" in "".join(problems):
        return 1

    import check_jlc as jl
    boards =bom.board_count(a.targets, a.boards)
    try:
        db = jl.Db(jl.ensure_db(a.cache or jl.CACHE, a.offline, a.refresh))
    except jl.JlcError as e:
        raise SystemExit(str(e))
    dk = make_dk(a.offline)
    results = [evaluate(r, db, dk, boards) for r in rows]
    print(f"watch list: {len(results)} lines, {boards} boards")
    show(results)
    write_out(results, a.out)
    ready = sorted({r["refdes"] for r in results if r["jlc_can_place"] == "yes"})
    for r in results:
        if r["jlc_can_place"] == "yes":
            kind = "the designed part" if r["role"] == "self" else f"a {r['drop_in']} substitute"
            print(f"{PLACE_MSG}: {r['mpn']} for {r['refdes']} ({kind}, JLC stock "
                  f"{r['jlc_stock']}, need {r['need']}, {r['jlc_library']} {r['jlc_lcsc']})")
    if not ready:
        print("no watched part is JLC-placeable at this quantity")
    print(f"wrote {a.out}")
    return 1 if (a.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
