#!/usr/bin/env bash
# ERC + DRC on kicad/ against checks/baseline.json. Exit 0 only if error counts are
# not above baseline, and DRC has 0 unconnected items and 0 schematic-parity issues.
# Warning counts are reported but never compared (DRC jitters run to run).
# Usage: checks/run_checks.sh [--record]   (--record rewrites baseline and reports)
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cd "$root/kicad"
kicad-cli sch erc --format json -o "$tmp/erc.json" fmcw3.kicad_sch >/dev/null
kicad-cli pcb drc --format json -o "$tmp/drc.json" fmcw3.kicad_pcb >/dev/null
python3 - "$tmp" "$root/checks" "${1:-}" <<'P'
import json, sys, collections, shutil
tmp, chk, mode = sys.argv[1:4]
erc = json.load(open(f"{tmp}/erc.json")); drc = json.load(open(f"{tmp}/drc.json"))
def count(vs):
    c = collections.Counter(); t = collections.Counter()
    for v in vs:
        c[v["severity"]] += 1; t[f'{v["severity"]}:{v["type"]}'] += 1
    return dict(c), dict(sorted(t.items()))
ev = [v for s in erc["sheets"] for v in s["violations"]]
ec, et = count(ev); dc, dt = count(drc["violations"])
cur = {"erc": {"errors": ec.get("error", 0), "by_type": et},
       "drc": {"errors": dc.get("error", 0), "by_type": dt,
               "unconnected_items": len(drc["unconnected_items"]),
               "schematic_parity": len(drc["schematic_parity"])}}
if mode == "--record":
    json.dump(cur, open(f"{chk}/baseline.json", "w"), indent=2); open(f"{chk}/baseline.json", "a").write("\n")
    shutil.copy(f"{tmp}/erc.json", f"{chk}/erc.json"); shutil.copy(f"{tmp}/drc.json", f"{chk}/drc.json")
    print("recorded", json.dumps(cur)); sys.exit(0)
base = json.load(open(f"{chk}/baseline.json")); bad = []
if cur["erc"]["errors"] > base["erc"]["errors"]: bad.append(f'ERC errors {cur["erc"]["errors"]} > {base["erc"]["errors"]}')
if cur["drc"]["errors"] > base["drc"]["errors"]: bad.append(f'DRC errors {cur["drc"]["errors"]} > {base["drc"]["errors"]}')
if cur["drc"]["unconnected_items"]: bad.append(f'DRC unconnected items {cur["drc"]["unconnected_items"]}')
if cur["drc"]["schematic_parity"]: bad.append(f'DRC schematic parity {cur["drc"]["schematic_parity"]}')
print(f'ERC errors {cur["erc"]["errors"]} (baseline {base["erc"]["errors"]}), DRC errors {cur["drc"]["errors"]} (baseline {base["drc"]["errors"]}), '
      f'unconnected {cur["drc"]["unconnected_items"]}, parity {cur["drc"]["schematic_parity"]}')
print("warnings (informational): ERC", sum(v for k,v in et.items() if k.startswith("warning")), "DRC", sum(v for k,v in dt.items() if k.startswith("warning")))
if bad: print("FAIL: " + "; ".join(bad)); sys.exit(1)
print("PASS")
P
