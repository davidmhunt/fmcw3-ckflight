#!/usr/bin/env python3
"""Grouped BOM from the schematic, headless (kicad-cli), with a class per group.

usage: parts/bom.py [--targets NAME] [--boards N] [--spares N] [--offline] [--check]
                    [--out parts/out/bom.csv] [--decisions parts/decisions.csv]
                    [--schematic kicad/fmcw3.kicad_sch] [--pcb kicad/fmcw3.kicad_pcb]

Writes parts/out/bom.csv, availability.csv (JLC and DigiKey side by side with a verdict per
line: JLC assemble, consign from DigiKey, hand-solder, unresolved; also not fitted, no part)
and parts/out/jlc/bom.csv + cpl.csv in JLCPCB's formats. Boards default to board_quantity in
the target set (tools/targets.py); --boards overrides. --offline uses the caches only;
--check exits 1 when a placed part has no MPN.

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


# ---------------------------------------------------------------- step 4: availability and JLC files

PCB = ROOT / "kicad" / "fmcw3.kicad_pcb"
OUT_DIR = ROOT / "parts" / "out"
DK_CACHE = ROOT / "parts" / "cache" / "digikey"   # gitignored with the rest of parts/cache/
LEGACY_PARTS = ROOT / "parts" / "legacy" / "parts.csv"
VERDICTS = ("JLC assemble", "consign from DigiKey", "hand-solder", "unresolved",
            "not fitted", "no part")
# footprints that are not a purchasable part: RF vias, solder pads, mounting holes, printed coupler
MECHANICAL = re.compile(r"RF_via|SolderPad|MountingHole|Directional_Coupler", re.I)
THROUGH_HOLE = re.compile(r"PinHeader|Pin_Header|BarrelJack|_THT|_TH\b|DIP|Socket", re.I)


def board_count(targets: str = "default", override: int | None = None) -> int:
    """Boards to buy for: `override`, else `board_quantity` of the target set."""
    if override is not None:
        if override < 1:
            raise SystemExit("--boards must be at least 1")
        return override
    sys.path.insert(0, str(ROOT / "tools"))
    import targets as tg
    try:
        return int(tg.value(tg.load(targets), "board_quantity"))
    except tg.TargetError as e:
        raise SystemExit(str(e))


def need_qty(qty: int, boards: int, spares: int = 0) -> int:
    """Parts to buy for a line: refs per board times boards, plus `spares` extra per line."""
    return qty * boards + spares


def is_mechanical(g: dict) -> bool:
    return g["class"] == "nopart" and bool(MECHANICAL.search(g["Footprint"] + " " + g["Value"]))


def is_through_hole(g: dict) -> bool:
    return bool(THROUGH_HOLE.search(g["Footprint"]))


def verdict(g: dict, jlc: dict, dk: dict, need: int) -> tuple[str, str]:
    """(verdict, reason) for one line from the two sources' results.

    not fitted       dnp line
    no part          via, solder pad, mounting hole, printed coupler: nothing to buy
    JLC assemble     JLC has it in stock for `need` with an exact or same-package match
    consign from DigiKey   not on JLC, DigiKey has it in stock (JLC assembles consigned parts)
    hand-solder      as above, but a through-hole line: solder it by hand
    unresolved       no part number, no stock, or only a near match that needs review
    """
    if g["class"] == "dnp":
        return "not fitted", "DNP"
    if is_mechanical(g):
        return "no part", "not a purchasable part"
    if g["class"] == "nopart":
        return "unresolved", "no MPN in the schematic or decisions.csv"
    jlc_ok = (jlc.get("jlc_status") == "Available" and jlc.get("jlc_match") in ("exact", "package"))
    if jlc_ok:
        return "JLC assemble", f"{jlc['jlc_library']} {jlc['jlc_lcsc']} ({jlc['jlc_match']})"
    dk_stock = dk.get("dk_stock")
    dk_ok = (dk.get("dk_status") in ("Active", "Suggested") and isinstance(dk_stock, int)
             and dk_stock >= need)
    if dk_ok:
        how = "hand-solder" if is_through_hole(g) else "consign from DigiKey"
        return how, f"DigiKey {dk.get('dk_pn') or dk.get('dk_mpn')} stock {dk_stock}"
    why = []
    if jlc.get("jlc_match") == "review":
        why.append(f"JLC near match {jlc.get('jlc_mpn')} needs review")
    elif jlc.get("jlc_status") in ("Low stock", "Out of stock", "No-result"):
        why.append(f"JLC {jlc['jlc_status']}")
    else:
        why.append("JLC not checked")
    why.append(f"DigiKey {dk.get('dk_status') or 'not checked'}")
    return "unresolved", "; ".join(why)


class CachedDigiKey:
    """DigiKey search with an on-disk cache of the response bodies (parts/cache/digikey/, never
    in git; bodies hold no credentials). Without a live client every miss raises OfflineMiss."""

    class OfflineMiss(RuntimeError):
        pass

    def __init__(self, client=None, cache: Path = DK_CACHE):
        self.client, self.cache = client, cache

    def search(self, keywords, limit=10):
        import hashlib
        import json
        path = self.cache / (hashlib.sha1(f"{keywords}|{limit}".encode()).hexdigest() + ".json")
        if path.is_file():
            return json.loads(path.read_text())
        if self.client is None:
            raise self.OfflineMiss(f"no cached DigiKey answer for {keywords!r}")
        products = self.client.search(keywords, limit)
        self.cache.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(products))
        return products


def dk_result(client, g: dict, need: int) -> dict:
    import check_digikey as dk
    if client is None:
        res = dk.blank()
        res["dk_status"] = "n/a" if g["class"] in ("dnp", "nopart") else "Not-checked"
        return res
    try:
        return dk.check_group(client, g, need)
    except CachedDigiKey.OfflineMiss:
        res = dk.blank()
        res["dk_status"] = "Not-cached"
        return res
    except dk.DigiKeyError as e:
        res = dk.blank()
        res["dk_status"] = "Error"
        res["dk_query"] = str(e)[:120]
        return res


def jlc_result(db, g: dict, need: int) -> dict:
    import check_jlc as jl
    if db is None:
        res = jl.blank()
        res["jlc_status"] = "n/a" if g["class"] in ("dnp", "nopart") else "Not-checked"
        return res
    return jl.check_group(db, g, need)


def availability_rows(groups: list[dict], boards: int, spares: int, db, client) -> list[dict]:
    rows = []
    for g in groups:
        need = need_qty(g["qty"], boards, spares)
        j, d = jlc_result(db, g, need), dk_result(client, g, need)
        v, why = verdict(g, j, d, need)
        rows.append({"verdict": v, "reason": why, "class": g["class"], "refs": ";".join(g["refs"]),
                     "qty": g["qty"], "need": need, "value": g["Value"],
                     "footprint": g["Footprint"], "MPN": g["MPN"], "Manufacturer": g["Manufacturer"],
                     "LCSC": g["LCSC"], "DigiKey PN": g["DigiKey PN"], **j, **d})
    return rows


def availability_cols() -> list[str]:
    import check_digikey as dk
    import check_jlc as jl
    return (["verdict", "reason", "class", "refs", "qty", "need", "value", "footprint", "MPN",
             "Manufacturer", "LCSC", "DigiKey PN"] + jl.RESULT_COLS + dk.RESULT_COLS)


def write_availability(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=availability_cols())
        w.writeheader()
        w.writerows(rows)


def jlc_assembled(rows: list[dict]) -> list[dict]:
    """Lines JLC places: assemble or consigned, plus unresolved lines (listed with a blank LCSC
    number, like production/bom.csv, so JLC's own tool flags them). Not fitted, no-part and
    hand-solder lines stay out."""
    return [r for r in rows if r["verdict"] in ("JLC assemble", "consign from DigiKey", "unresolved")]


def write_jlc_bom(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for r in jlc_assembled(rows):
            lcsc = r["LCSC"] or (r["jlc_lcsc"] if r["verdict"] == "JLC assemble" else "")
            w.writerow([r["value"], ", ".join(r["refs"].split(";")), r["footprint"], lcsc])


def export_pos(pcb: Path = PCB) -> str:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "pos.csv"
        cmd = ["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
               "--side", "both", "-o", str(out), str(pcb)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not out.is_file():
            raise SystemExit(f"kicad-cli pos export failed: {r.stderr.strip() or r.stdout.strip()}")
        return out.read_text()


def cpl_rows(pos_text: str, refs: set[str]) -> list[list]:
    """kicad-cli position rows -> JLC CPL rows [Designator, Mid X, Mid Y, Layer, Rotation] for the
    refs in `refs`. Coordinates are in KiCad's board frame (the same as production/positions.csv
    up to the origin); JLC's per-package rotation corrections are not applied."""
    out = []
    for rec in csv.DictReader(pos_text.splitlines()):
        ref = rec["Ref"].strip()
        if ref in refs:
            out.append([ref, rec["PosX"], rec["PosY"], rec["Side"].strip().lower(), rec["Rot"]])
    out.sort(key=lambda r: ref_key(r[0]))
    return out


def write_cpl(rows: list[list], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(rows)


def missing_mpn(groups: list[dict]) -> list[dict]:
    """Placed parts that name no part: nopart lines that are real parts (not vias, pads, holes)."""
    return [g for g in groups if g["class"] == "nopart" and not is_mechanical(g)]


def compare_legacy(groups: list[dict], path: Path = LEGACY_PARTS) -> str:
    """One line comparing the ref set with the upstream parts.csv kept in parts/legacy/."""
    if not path.is_file():
        return ""
    with path.open(newline="") as fh:
        old = {r for rec in csv.DictReader(fh) for r in rec["refs"].split(";")}
    new = {r for g in groups for r in g["refs"]}
    return (f"vs legacy parts.csv: {len(old)} refs then, {len(new)} now; "
            f"only then: {','.join(sorted(old - new, key=ref_key)) or '-'}; "
            f"only now: {','.join(sorted(new - old, key=ref_key)) or '-'}")


def verdict_summary(rows: list[dict]) -> str:
    return ", ".join(f"{v} {sum(1 for r in rows if r['verdict'] == v)}" for v in VERDICTS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schematic", type=Path, default=SCH)
    ap.add_argument("--pcb", type=Path, default=PCB)
    ap.add_argument("--decisions", type=Path, default=DECISIONS)
    ap.add_argument("--out", type=Path, default=OUT, help="bom.csv; the other files go beside it")
    ap.add_argument("--targets", default="default", help="target set giving board_quantity")
    ap.add_argument("--boards", type=int, default=None, help="boards to buy for (overrides targets)")
    ap.add_argument("--spares", type=int, default=0, help="extra parts per line")
    ap.add_argument("--offline", action="store_true",
                    help="use the caches only (JLC database, DigiKey answers); never touch the network")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when a placed part has no MPN")
    a = ap.parse_args(argv)
    boards = board_count(a.targets, a.boards)
    groups = build(a.schematic, a.decisions)
    write_csv(groups, a.out)
    print(summary(groups))
    print(f"wrote {a.out}")
    legacy = compare_legacy(groups)
    if legacy:
        print(legacy)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_digikey as dk
    import check_jlc as jl
    db = None
    try:
        db = jl.Db(jl.ensure_db(jl.CACHE, a.offline))
    except jl.JlcError as e:
        print(f"JLC not checked: {e}", file=sys.stderr)
    client = None
    try:
        client = CachedDigiKey(None if a.offline else dk.Client.from_env())
    except dk.DigiKeyError as e:
        print(f"DigiKey: {e}; using cached answers only", file=sys.stderr)
        client = CachedDigiKey(None)
    rows = availability_rows(groups, boards, a.spares, db, client)
    out_dir = a.out.parent
    write_availability(rows, out_dir / "availability.csv")
    write_jlc_bom(rows, out_dir / "jlc" / "bom.csv")
    placed = {r for row in jlc_assembled(rows) for r in row["refs"].split(";")}
    write_cpl(cpl_rows(export_pos(a.pcb), placed), out_dir / "jlc" / "cpl.csv")
    print(f"{boards} boards, {a.spares} spares per line: {verdict_summary(rows)}")
    print(f"wrote {out_dir / 'availability.csv'}, {out_dir / 'jlc' / 'bom.csv'}, "
          f"{out_dir / 'jlc' / 'cpl.csv'}")
    bad = missing_mpn(groups)
    if bad:
        refs = sum(g["qty"] for g in bad)
        print(f"{len(bad)} lines ({refs} refs) are placed parts without an MPN")
        if a.check:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
