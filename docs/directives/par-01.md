# par-01: BOM export from the schematic and automated DigiKey + JLCPCB checks
Status: proposed
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_bom.py tests/test_digikey.py tests/test_jlc.py -q && ./run parts/bom.py --boards 5 --offline
Hardware: none

## Goal
One command produces the grouped BOM from the schematic and checks every line against DigiKey
and the JLCPCB parts library for `--boards N`. It holds when the tests pass on recorded
responses and a live run writes `parts/out/availability.csv` with a status on every line.

## Steps
1. `parts/bom.py`: export with `kicad-cli sch export bom` from `kicad/fmcw3.kicad_sch`, group by
   value, footprint and part-number fields, classify each group (`mpn`, `generic`, `dnp`,
   `nopart`), merge decisions from `parts/decisions.csv` (par-03) until the fields are in the
   schematic. Confirm the group and ref counts against `production/bom.csv` (84 groups, 370 refs)
   and explain any difference.
2. DigiKey: refactor `parts/check_digikey.py` into an importable module reading `.env`; per line
   return status, stock, price at quantity, lead time, lifecycle, datasheet URL. Generic passives
   get a parametric search (value, package, tolerance, voltage, dielectric) and a suggested MPN.
3. JLCPCB: `parts/check_jlc.py`. Use the open parts data that the `bouni/kicad-jlcpcb-tools`
   plugin uses (its downloadable parts database) or the `jlcsearch` API; pick whichever works
   unattended today and record why. Per line: LCSC number, stock, Basic/Preferred/Extended,
   price, and match confidence (exact MPN, same package, or needs review). Cache the database
   outside git. Record whether the plugin itself installs on KiCad 10 for GUI use.
4. `parts/bom.py --boards N [--offline] [--check]`: writes `parts/out/bom.csv`,
   `availability.csv` (both sources side by side, a per-line verdict: JLC assemble, consign from
   DigiKey, hand-solder, unresolved) and a JLCPCB-format BOM and CPL under `parts/out/jlc/`.
   `--offline` uses the cache; `--check` exits non-zero on a placed part without an MPN.
5. Tests with recorded API responses (no network, no keys): grouping, classification, DigiKey
   and JLC parsing, verdict logic, quantity scaling with spares.
6. `parts/README.md`: how it works, the columns, how to add keys, what "match confidence" means.

## Out of scope
- Choosing substitutes or resolving suffixes (par-03).
- Editing the schematic (par-04).
- Ordering anything.

## Allowed commands
- `./run *`

## Log
