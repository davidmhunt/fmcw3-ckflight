# par-01: BOM export from the schematic and automated DigiKey + JLCPCB checks
Status: approved
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
4. `parts/bom.py [--targets NAME] [--boards N] [--offline] [--check]`: the board count defaults
   to `board_quantity` in the target set (`analysis/targets/default.yaml`, loaded through
   `tools/targets.py`); `--boards` overrides it. Writes `parts/out/bom.csv`,
   `availability.csv` (both sources side by side, a per-line verdict: JLC assemble, consign from
   DigiKey, hand-solder, unresolved) and a JLCPCB-format BOM and CPL under `parts/out/jlc/`.
   `--offline` uses the cache; `--check` exits non-zero on a placed part without an MPN.
   The upstream files already in `parts/` (`parts.csv`, `availability.csv`,
   `fields_to_apply.csv`, `manufacturing_check.md`) are inputs to compare against: reuse what
   is still right, move superseded ones to `parts/legacy/` with a line in `parts/README.md`.
5. Tests with recorded API responses (no network, no keys): grouping, classification, DigiKey
   and JLC parsing, verdict logic, quantity scaling with spares.
6. `parts/README.md`: how it works, the columns, how to add keys, what "match confidence" means.
   Add `parts/bom.py`, `parts/check_digikey.py` and `parts/check_jlc.py` to `MANUAL.md` (a new
   "Parts and availability" section) and extend `tests/test_manual.py` to cover `parts/*.py`
   command-line tools.

## Rules
- DigiKey keys are read from `.env` at run time only; never print, log or commit them, and
  never write them into recorded test responses (scrub headers and tokens).
- The JLCPCB parts database cache lives under a gitignored path, never in git.
- The schematic is read headless (`kicad-cli`); nothing under `kicad/` is written.

## Out of scope
- Choosing substitutes or resolving suffixes (par-03).
- Editing the schematic (par-04).
- Ordering anything.

## Allowed commands
- `./run *`

## Log
