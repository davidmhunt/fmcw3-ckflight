#!/usr/bin/env python3
"""DigiKey availability for BOM groups: importable module, CLI for a quick look.

Credentials come from `.env` at the repo root (gitignored; template `.env.example`) or from
DIGIKEY_* environment variables; they are read at run time only and never printed or logged.

usage: parts/check_digikey.py [--boards N] [--spares N] [--bom parts/out/bom.csv] [--limit K]

API (all network access goes through `Client`, whose transport can be replaced in tests):
  load_env(path) -> dict                      require_keys(env, names)
  Client(cid, secret, transport=None)         .search(keywords, limit) -> [product]
  check_group(client, group, need) -> dict    one result per BOM group (see RESULT_COLS)
  parse_product(p, need) -> dict              status, stock, price at quantity, lead time, ...
  parametric_query(group) -> (keywords, spec) generic passive -> search terms and spec
  suggest(products, spec, need) -> product|None   pick the best parametric match

A group is a dict as built by parts/bom.py (keys Value, Footprint, MPN, DigiKey PN, class, refs
and, when known, Tolerance, Voltage, Dielectric). Nothing here writes files under kicad/.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV = HERE.parent / ".env"
BASE = "https://api.digikey.com"

RESULT_COLS = ["dk_status", "dk_lifecycle", "dk_stock", "dk_unit_price", "dk_price_qty",
               "dk_lead_weeks", "dk_datasheet", "dk_url", "dk_mpn", "dk_mfr", "dk_pn",
               "dk_match", "dk_suggested_mpn", "dk_query"]


class DigiKeyError(RuntimeError):
    """An API failure. The message never contains credentials."""


def load_env(path=ENV):
    """KEY=VALUE lines from `path` (if it exists); DIGIKEY_* environment variables win
    (`./run` passes .env into the container that way)."""
    env = {}
    path = Path(path)
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    env.update({k: v for k, v in os.environ.items() if v and k.startswith("DIGIKEY_")})
    return env


def require_keys(env, names=("DIGIKEY_CLIENT_ID", "DIGIKEY_CLIENT_SECRET")):
    missing = [n for n in names if not env.get(n)]
    if missing:
        raise DigiKeyError(f"Missing {', '.join(missing)}: copy .env.example to .env and fill it in "
                           "(see docs/setup.md)")


def http_post(url, data, headers):
    """Default transport: POST, return parsed JSON. Errors carry the status and a body excerpt only."""
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise DigiKeyError(f"HTTP {e.code} from {url}: {e.read().decode(errors='replace')[:300]}")
    except urllib.error.URLError as e:
        raise DigiKeyError(f"network error from {url}: {e.reason}")


class Client:
    def __init__(self, cid, secret, transport=None, delay=0.5):
        self._cid, self._secret = cid, secret
        self._post = transport or http_post
        self._token = None
        self.delay = delay

    @classmethod
    def from_env(cls, path=ENV, **kw):
        env = load_env(path)
        require_keys(env)
        return cls(env["DIGIKEY_CLIENT_ID"], env["DIGIKEY_CLIENT_SECRET"], **kw)

    def token(self):
        if self._token is None:
            body = urllib.parse.urlencode({"client_id": self._cid, "client_secret": self._secret,
                                           "grant_type": "client_credentials"}).encode()
            tok = self._post(f"{BASE}/v1/oauth2/token", body,
                             {"Content-Type": "application/x-www-form-urlencoded"})
            self._token = tok["access_token"]
        return self._token

    def search(self, keywords, limit=10):
        body = json.dumps({"Keywords": keywords, "Limit": limit}).encode()
        resp = self._post(f"{BASE}/products/v4/search/keyword", body, {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token()}",
            "X-DIGIKEY-Client-Id": self._cid,
            "X-DIGIKEY-Locale-Site": "US",
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Currency": "USD",
        })
        if self.delay:
            time.sleep(self.delay)  # stay under the rate limit
        return resp.get("Products", []) or []


# ---------------------------------------------------------------- product parsing

def lifecycle(dk_status):
    """Map DigiKey's ProductStatus to Active / NFND / Obsolete."""
    s = (dk_status or "").lower()
    if s == "active":
        return "Active"
    if "not for new" in s or "last time" in s:
        return "NFND"
    return "Obsolete"  # Obsolete, Discontinued at DigiKey


def _variations(p):
    return p.get("ProductVariations") or []


def best_variation(p):
    """Prefer the cut-tape (single-unit) variant, else the first variation."""
    vs = _variations(p)
    for v in vs:
        if "Cut Tape" in (v.get("PackageType") or {}).get("Name", ""):
            return v
    return vs[0] if vs else {}


def dk_pn(p):
    return best_variation(p).get("DigiKeyProductNumber", "")


def price_at(p, qty):
    """Unit price at `qty`: the break with the largest BreakQuantity <= qty (else the smallest
    break). Returns None when no pricing is listed. Uses the cut-tape variation."""
    breaks = best_variation(p).get("StandardPricing") or p.get("StandardPricing") or []
    breaks = sorted((b for b in breaks if "UnitPrice" in b), key=lambda b: b.get("BreakQuantity", 0))
    if not breaks:
        return None
    ok = [b for b in breaks if b.get("BreakQuantity", 0) <= qty]
    return float((ok[-1] if ok else breaks[0])["UnitPrice"])


def param(p, *names):
    """First parameter value whose ParameterText is one of `names`."""
    for x in p.get("Parameters") or []:
        if x.get("ParameterText") in names:
            return x.get("ValueText", "") or ""
    return ""


def parse_product(p, need):
    """One DigiKey product -> the per-line fields. `need` is the quantity to price at."""
    dk_status = (p.get("ProductStatus") or {}).get("Status", "?")
    stock = p.get("QuantityAvailable") or 0
    lead = p.get("ManufacturerLeadWeeks", "")
    return {
        "dk_lifecycle": lifecycle(dk_status),
        "dk_status": ("Active" if lifecycle(dk_status) == "Active" and stock >= need
                      else "Low stock" if lifecycle(dk_status) == "Active"
                      else lifecycle(dk_status)),
        "dk_stock": stock,
        "dk_unit_price": price_at(p, need),
        "dk_price_qty": need,
        "dk_lead_weeks": lead if lead not in (None, "0", 0) else "",
        "dk_datasheet": p.get("DatasheetUrl", "") or "",
        "dk_url": p.get("ProductUrl", "") or "",
        "dk_mpn": p.get("ManufacturerProductNumber", ""),
        "dk_mfr": (p.get("Manufacturer") or {}).get("Name", ""),
        "dk_pn": dk_pn(p),
    }


# ---------------------------------------------------------------- generic passives

_SI = {"p": "pF", "n": "nF", "u": "µF", "µ": "µF", "m": "mF"}


def split_value(value):
    """'100n' -> (100.0, 'n'); '4.7k' -> (4.7, 'k'); '49.9' -> (49.9, ''). None if not numeric."""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([pnuµmkKM]?)", value.strip())
    if not m:
        m2 = re.fullmatch(r"(\d+)([pnuµkKMR])(\d+)", value.strip())  # 4k7, 2u2
        if not m2:
            return None
        return float(f"{m2.group(1)}.{m2.group(3)}"), m2.group(2)
    return float(m.group(1)), m.group(2)


def _num(x):
    return f"{x:g}"


def value_text(refprefix, value):
    """Human DigiKey-style value: C '100n' -> '100nF', R '10k' -> '10kOhm', L '3.3n' -> '3.3nH'."""
    sv = split_value(value)
    if sv is None:
        return value
    n, s = sv
    if refprefix == "C":
        return f"{_num(n)}{_SI.get(s, 'F')}"
    if refprefix == "L":
        return f"{_num(n)}{s.replace('u', 'µ')}H"
    if refprefix in ("R", "FB"):
        return f"{_num(n)}{s.upper() if s in 'kKM' else ''}Ohm".replace("KOhm", "kOhm")
    return value


def package_code(footprint):
    """'SMD_0402' / 'C_0402_1005Metric' -> '0402'; else ''."""
    m = re.search(r"(?<!\d)(0201|0402|0603|0805|1206|1210|1812|2010|2512)(?!\d)", footprint)
    return m.group(1) if m else ""


def _prefix(ref):
    return re.sub(r"[0-9]+$", "", ref)


def parametric_query(group):
    """Generic passive group -> (keyword string, spec dict). Unspecified parameters stay out of
    the query; the spec records what was searched so the suggestion can say what was assumed."""
    pre = _prefix(group["refs"][0])
    spec = {"kind": pre, "value": value_text(pre, group["Value"]),
            "package": package_code(group["Footprint"]),
            "tolerance": group.get("Tolerance", "") or "",
            "voltage": group.get("Voltage", "") or "",
            "dielectric": group.get("Dielectric", "") or ""}
    words = {"C": "ceramic capacitor", "R": "resistor", "L": "inductor", "FB": "ferrite bead"}
    terms = [spec["value"], spec["package"], words.get(pre, ""), spec["dielectric"],
             spec["voltage"], spec["tolerance"]]
    return " ".join(t for t in terms if t), spec


_MULT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1.0, "k": 1e3, "K": 1e3,
         "M": 1e6}


def to_base(text):
    """'0.1 µF' / '100nF' / '10 kOhms' / '2.2nH' -> base units (float); None if unparseable.
    An 'M' prefix is mega, 'm' milli (resistors in the BOM never use milli)."""
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*([pnuµmkKM]?)(?:F|H|Ohms?|Ω)?\b", text or "")
    return float(m.group(1)) * _MULT[m.group(2)] if m else None


def _norm(s):
    return re.sub(r"[\s,]", "", s or "").lower().replace("µ", "u").replace("ohms", "ohm")


def match_score(p, spec, need):
    """Higher is better; -1 means disqualified (wrong value/package or not Active)."""
    if lifecycle((p.get("ProductStatus") or {}).get("Status", "?")) != "Active":
        return -1
    if spec["package"] and spec["package"] not in param(p, "Package / Case", "Supplier Device Package"):
        return -1
    pval = param(p, "Capacitance", "Resistance", "Inductance")
    if pval:
        want, have = to_base(spec["value"]), to_base(pval)
        if want is None or have is None or abs(have - want) > 1e-6 * abs(want):
            return -1
    score = 0
    if spec["tolerance"] and _norm(spec["tolerance"].lstrip("±")) in _norm(param(p, "Tolerance")):
        score += 2
    if spec["voltage"] and _norm(spec["voltage"]) in _norm(param(p, "Voltage - Rated")):
        score += 2
    if spec["dielectric"] and _norm(spec["dielectric"]) in _norm(param(p, "Temperature Coefficient")):
        score += 2
    if (p.get("QuantityAvailable") or 0) >= need:
        score += 4
    return score


def suggest(products, spec, need):
    """Best Active, in-spec product (highest score, then stock); None if nothing qualifies."""
    scored = [(match_score(p, spec, need), p.get("QuantityAvailable") or 0, p) for p in products]
    scored = [s for s in scored if s[0] >= 0]
    if not scored:
        return None
    return max(scored, key=lambda s: (s[0], s[1]))[2]


# ---------------------------------------------------------------- per line

def blank():
    return dict.fromkeys(RESULT_COLS, "")


def exact_match(products, term):
    t = term.upper()
    for p in products:
        if p.get("ManufacturerProductNumber", "").upper() == t:
            return p
        if any(v.get("DigiKeyProductNumber", "").upper() == t for v in _variations(p)):
            return p
    return None


def check_group(client, group, need):
    """DigiKey result for one BOM group: dict with RESULT_COLS. `need` = parts to buy (qty x
    boards plus spares). dk_status: Active, Low stock, NFND, Obsolete, No-result, Suggested
    (generic: a parametric pick), No-match (generic: nothing qualified), n/a (dnp, nopart)."""
    res = blank()
    cls = group.get("class", "")
    if cls in ("dnp", "nopart"):
        res["dk_status"] = "n/a"
        return res
    if cls == "generic":
        query, spec = parametric_query(group)
        res["dk_query"] = query
        prods = client.search(query, limit=20)
        p = suggest(prods, spec, need)
        if p is None:
            res["dk_status"] = "No-match"
            return res
        res.update(parse_product(p, need))
        res["dk_status"] = "Suggested"
        res["dk_match"] = "parametric"
        res["dk_suggested_mpn"] = p.get("ManufacturerProductNumber", "")
        return res
    term = group.get("MPN") or group.get("DigiKey PN")
    res["dk_query"] = term
    p = exact_match(client.search(term, limit=10), term)
    if p is None:
        res["dk_status"] = "No-result"
        res["dk_stock"] = 0
        return res
    res.update(parse_product(p, need))
    res["dk_match"] = "exact"
    return res


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="DigiKey availability for the BOM groups")
    ap.add_argument("--boards", type=int, default=3)
    ap.add_argument("--spares", type=int, default=0, help="extra parts per line")
    ap.add_argument("--limit", type=int, default=0, help="check only the first K lines")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    import bom
    try:
        client = Client.from_env()
        groups = bom.build()
        if a.limit:
            groups = groups[:a.limit]
        print(f"{'refs':28} {'class':8} {'status':10} {'stock':>8} {'need':>5} {'price':>8}  mpn")
        for g in groups:
            need = g["qty"] * a.boards + a.spares
            r = check_group(client, g, need)
            price = "" if r["dk_unit_price"] in ("", None) else f"{r['dk_unit_price']:.4f}"
            print(f"{';'.join(g['refs'])[:28]:28} {g['class']:8} {r['dk_status']:10} "
                  f"{str(r['dk_stock']):>8} {need:>5} {price:>8}  "
                  f"{r['dk_suggested_mpn'] or r['dk_mpn']}")
    except DigiKeyError as e:
        raise SystemExit(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
