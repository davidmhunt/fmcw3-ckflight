#!/usr/bin/env python3
"""JLCPCB parts-library availability for BOM groups: importable module, CLI for a quick look.

Data source: the parts database that the `bouni/kicad-jlcpcb-tools` plugin downloads
(https://bouni.github.io/kicad-jlcpcb-tools/, "current parts" variant: every JLC part except
long-obsolete ones, about 820k rows, SQLite FTS5). It is downloaded once into a gitignored cache
(`parts/cache/jlcpcb/`, about 830 MB unpacked) and queried locally, so a later run works offline
and gives the same answer every time. No key is needed. See parts/README.md for why this and not
the jlcsearch API.

usage: parts/check_jlc.py [--boards N] [--spares N] [--limit K] [--cache DIR]
                          [--refresh | --offline]

API:
  Db(path)                      .by_lcsc(code) .by_mpn(mpn) .by_mpn_prefix(mpn) .by_value(...)
  ensure_db(cache, offline)     download + unpack if missing -> path of the .db
  parse_price(text) -> [(qty, unit)]    price_at(breaks, qty) -> float|None
  check_group(db, group, need) -> dict  one result per BOM group (RESULT_COLS)

Match confidence (column jlc_match):
  exact    the part's MPN (or LCSC number) equals the one in the BOM line
  package  generic passive: same value and package as the line (tolerance, voltage and
           dielectric are NOT compared; read the description before using it)
  review   a near hit that needs a person: an MPN that only starts with the line's MPN
           (suffix differs), or a part with the same MPN in another case/spacing
  (empty)  nothing found

A group is a dict as built by parts/bom.py. Nothing here writes under kicad/.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "jlcpcb"
URL_STUB = "https://bouni.github.io/kicad-jlcpcb-tools/"
DB_NAME = "current-parts-fts5.db"          # LIBRARY "current-parts" in the plugin's dblib
CHUNK_COUNT_FILE = "chunk_num_current_parts_fts5.txt"

RESULT_COLS = ["jlc_status", "jlc_lcsc", "jlc_library", "jlc_stock", "jlc_unit_price",
               "jlc_price_qty", "jlc_mpn", "jlc_mfr", "jlc_package", "jlc_match", "jlc_url",
               "jlc_query"]
LIB_RANK = {"Basic": 0, "Preferred": 1, "Extended": 2}
# group class -> plugin category used to narrow generic searches
CATEGORY = {"C": "Multilayer Ceramic Capacitors MLCC - SMD/SMT", "R": "Chip Resistor - Surface Mount",
            "L": "Inductors (SMD)", "FB": "Ferrite Beads"}


class JlcError(RuntimeError):
    pass


# ---------------------------------------------------------------- database download

def _get(url, timeout=300):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r
    except (urllib.error.URLError, OSError) as e:
        raise JlcError(f"download failed for {url}: {e}")


def download_db(cache: Path = CACHE, say=print) -> Path:
    """Fetch the split zip like the plugin does (chunk count file, then `<db>.zip.NNN`),
    join and unpack it into `cache`; returns the .db path. Chunks are deleted afterwards."""
    cache.mkdir(parents=True, exist_ok=True)
    with _get(URL_STUB + CHUNK_COUNT_FILE) as r:
        total = int(r.read().decode().strip())
    stub = DB_NAME.replace(".db", ".db.zip.")
    joined = cache / (DB_NAME + ".zip")
    say(f"downloading {total} chunks of {DB_NAME} into {cache} (about 190 MB)")
    with joined.open("wb") as out:
        for i in range(1, total + 1):
            with _get(f"{URL_STUB}{stub}{i:03}") as r:
                shutil.copyfileobj(r, out, 1024 * 1024)
            say(f"  chunk {i}/{total}")
    try:
        with zipfile.ZipFile(joined) as zf:
            member = zf.infolist()[0]
            tmp = cache / (member.filename + ".part")
            with zf.open(member) as src, tmp.open("wb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
    except zipfile.BadZipFile as e:
        raise JlcError(f"downloaded database is not a valid zip: {e}")
    finally:
        joined.unlink(missing_ok=True)
    final = cache / DB_NAME
    tmp.replace(final)
    return final


def ensure_db(cache: Path = CACHE, offline: bool = False, refresh: bool = False, say=print) -> Path:
    path = cache / DB_NAME
    if path.is_file() and not refresh:
        return path
    if offline:
        raise JlcError(f"--offline: no cached JLCPCB database at {path}; run "
                       "parts/check_jlc.py once without --offline")
    return download_db(cache, say)


# ---------------------------------------------------------------- price

def parse_price(text):
    """'1-199:0.025,200-599:0.019,20000-:0.014' -> [(1, 0.025), (200, 0.019), (20000, 0.014)]"""
    out = []
    for part in (text or "").split(","):
        m = re.match(r"\s*(\d+)\s*-\s*\d*\s*:\s*([0-9.]+)", part)
        if m:
            out.append((int(m.group(1)), float(m.group(2))))
    return sorted(out)


def price_at(breaks, qty):
    """Unit price at `qty`: the break with the largest start <= qty, else the smallest break."""
    if not breaks:
        return None
    ok = [b for b in breaks if b[0] <= qty]
    return (ok[-1] if ok else breaks[0])[1]


# ---------------------------------------------------------------- database access

def _phrase(s):
    return '"' + s.replace('"', '""') + '"'


def _stock(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


class Db:
    """Read-only view of the plugin's parts database (FTS5 table `parts`, trigram tokenizer,
    so a MATCH term needs at least 3 characters)."""

    COLS = ["LCSC Part", "First Category", "Second Category", "MFR.Part", "Package",
            "Manufacturer", "Library Type", "Description", "Datasheet", "Price", "Stock"]

    def __init__(self, path):
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

    def _rows(self, where, args, limit=200):
        q = ", ".join(f'"{c}"' for c in self.COLS)
        cur = self.con.execute(f"SELECT {q} FROM parts WHERE {where} LIMIT {int(limit)}", args)
        return [self.record(dict(zip(self.COLS, r))) for r in cur]

    @staticmethod
    def record(r):
        return {"lcsc": r["LCSC Part"], "mpn": r["MFR.Part"], "mfr": r["Manufacturer"],
                "package": r["Package"], "library": r["Library Type"],
                "description": r["Description"] or "", "datasheet": r["Datasheet"] or "",
                "stock": _stock(r["Stock"]), "breaks": parse_price(r["Price"]),
                "category": r["Second Category"]}

    def by_lcsc(self, code):
        code = code.strip().upper()
        if not re.fullmatch(r"C\d+", code):
            return []
        return [r for r in self._rows('"LCSC Part" MATCH ?', (_phrase(code),))
                if r["lcsc"] == code]

    def by_mpn_candidates(self, mpn):
        if len(mpn) < 3:
            return []
        return self._rows('"MFR.Part" MATCH ?', (_phrase(mpn),), limit=500)

    def by_mpn(self, mpn):
        """Rows whose MPN equals `mpn` (case-insensitive, spaces and dashes ignored)."""
        key = _squash(mpn)
        return [r for r in self.by_mpn_candidates(mpn) if _squash(r["mpn"]) == key]

    def by_mpn_prefix(self, mpn):
        """Rows whose MPN starts with `mpn` but is not equal (an ordering-suffix variant)."""
        key = _squash(mpn)
        return [r for r in self.by_mpn_candidates(mpn)
                if _squash(r["mpn"]).startswith(key) and _squash(r["mpn"]) != key]

    def by_value(self, kind, package, term=""):
        """Generic passive candidates: category and package, narrowed by `term` in the
        description when it is at least 3 characters (the trigram index cannot match less; then
        the whole package/category slice is returned and the caller filters)."""
        cat = CATEGORY.get(kind)
        if not (cat and package):
            return []
        where, args = '"Package" MATCH ? AND "Second Category" MATCH ?', [_phrase(package), _phrase(cat)]
        if len(term) >= 3:
            where += ' AND "Description" MATCH ?'
            args.append(_phrase(term))
        rows = self._rows(where, tuple(args), limit=200000)
        return [r for r in rows if r["package"] == package and r["category"] == cat]


def _squash(s):
    return re.sub(r"[\s\-_]", "", s or "").upper()


# ---------------------------------------------------------------- per line

def blank():
    return dict.fromkeys(RESULT_COLS, "")


def fill(res, rec, need, match):
    stock = rec["stock"]
    res.update({
        "jlc_status": "Available" if stock >= need else "Low stock" if stock > 0 else "Out of stock",
        "jlc_lcsc": rec["lcsc"], "jlc_library": rec["library"], "jlc_stock": stock,
        "jlc_unit_price": price_at(rec["breaks"], need), "jlc_price_qty": need,
        "jlc_mpn": rec["mpn"], "jlc_mfr": rec["mfr"], "jlc_package": rec["package"],
        "jlc_match": match, "jlc_url": f"https://www.lcsc.com/product-detail/{rec['lcsc']}.html"})
    return res


def best(recs, need):
    """In stock for `need` first, then Basic > Preferred > Extended, then more stock."""
    return min(recs, key=lambda r: (r["stock"] < need, LIB_RANK.get(r["library"], 3), -r["stock"]))


UNIT = {"C": "F", "L": "H", "FB": "H", "R": "Ω"}


def jlc_value_text(kind, value):
    """Value as the JLC descriptions write it: '100n' -> '100nF', '10k' -> '10kΩ', '3.3n' -> '3.3nH'
    ('u', not 'µ')."""
    import check_digikey as dk
    return dk.value_text(kind, value).replace("Ohm", "Ω").replace("µ", "u")


def search_term(kind, value):
    """Text for the description MATCH: value plus unit for C and L ('1uF'), the bare number
    for R (descriptions put it among other numbers)."""
    text = jlc_value_text(kind, value)
    return text if kind in ("C", "L") else re.sub(r"[kKMΩ]+$", "", text)


_TOKEN = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([pnuµμmkKMG]?)(F|H|Ω)")
_MULT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3, "": 1.0, "k": 1e3,
         "K": 1e3, "M": 1e6, "G": 1e9}


def value_in_description(kind, value, desc):
    """True when the description holds the same value with the right unit (F, H or Ω),
    compared in base units: '16.9kΩ' is not '16.9Ω', '2.2nH' is not '2.2uH'."""
    import check_digikey as dk
    want = dk.to_base(dk.value_text(kind, value))
    if want is None:
        return False
    unit = UNIT[kind]
    for num, pre, u in _TOKEN.findall(desc):
        if u == unit:
            have = float(num) * _MULT[pre]
            if abs(have - want) <= 1e-6 * max(abs(want), 1e-15):
                return True
    return False


def mpn_candidates(group):
    """Part numbers hidden in a generic line: the Value itself when it is not a number
    ('BLM18PG181SN1D') or the text in brackets ('33u (SRR6040A-330M)')."""
    import check_digikey as dk
    value = group["Value"]
    out = [m for m in re.findall(r"\(([^)]+)\)", value)]
    if dk.split_value(value) is None and not out:
        out.append(value)
    return out


def check_group(db, group, need):
    """JLC result for one BOM group: dict with RESULT_COLS. `need` = parts to buy (qty x boards
    plus spares). jlc_status: Available, Low stock, Out of stock, No-result, n/a (dnp, nopart)."""
    import check_digikey as dk
    res = blank()
    cls = group.get("class", "")
    if cls in ("dnp", "nopart"):
        res["jlc_status"] = "n/a"
        return res
    lcsc, mpn = (group.get("LCSC") or "").strip(), (group.get("MPN") or "").strip()
    if lcsc:
        res["jlc_query"] = lcsc
        recs = db.by_lcsc(lcsc)
        if recs:
            return fill(res, recs[0], need, "exact")
    if mpn:
        res["jlc_query"] = mpn
        recs = db.by_mpn(mpn)
        if recs:
            return fill(res, best(recs, need), need, "exact")
        recs = db.by_mpn_prefix(mpn)
        if recs:
            return fill(res, best(recs, need), need, "review")
    elif cls == "generic":
        for cand in mpn_candidates(group):  # a part number typed into the Value field
            res["jlc_query"] = cand
            recs = db.by_mpn(cand)
            if recs:
                return fill(res, best(recs, need), need, "review")
        pre = re.sub(r"[0-9]+$", "", group["refs"][0])
        package = dk.package_code(group["Footprint"])
        if dk.split_value(group["Value"]) is not None and pre in UNIT:
            res["jlc_query"] = f"{jlc_value_text(pre, group['Value'])} {package}".strip()
            recs = [r for r in db.by_value(pre, package, search_term(pre, group["Value"]))
                    if value_in_description(pre, group["Value"], r["description"])]
            if recs:
                return fill(res, best(recs, need), need, "package")
    res["jlc_status"] = "No-result"
    res["jlc_stock"] = 0
    return res


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="JLCPCB parts-library availability for the BOM groups")
    ap.add_argument("--boards", type=int, default=3)
    ap.add_argument("--spares", type=int, default=0, help="extra parts per line")
    ap.add_argument("--limit", type=int, default=0, help="check only the first K lines")
    ap.add_argument("--cache", type=Path, default=CACHE)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--refresh", action="store_true", help="download the database again")
    g.add_argument("--offline", action="store_true", help="use the cache only; never download")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    import bom
    try:
        db = Db(ensure_db(a.cache, a.offline, a.refresh))
        groups = bom.build()
    except JlcError as e:
        raise SystemExit(str(e))
    if a.limit:
        groups = groups[:a.limit]
    print(f"{'refs':28} {'class':8} {'status':12} {'lib':9} {'stock':>8} {'need':>5} "
          f"{'price':>8} {'match':8} lcsc")
    for grp in groups:
        need = grp["qty"] * a.boards + a.spares
        r = check_group(db, grp, need)
        price = "" if r["jlc_unit_price"] in ("", None) else f"{r['jlc_unit_price']:.4f}"
        print(f"{';'.join(grp['refs'])[:28]:28} {grp['class']:8} {r['jlc_status']:12} "
              f"{r['jlc_library']:9} {str(r['jlc_stock']):>8} {need:>5} {price:>8} "
              f"{r['jlc_match']:8} {r['jlc_lcsc']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
