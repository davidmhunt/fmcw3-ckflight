# par-04: Write MPN, DigiKey and LCSC fields into the schematic symbols
Status: proposed
Goal: parts
Node: any
Deliverable: code
Accept: user
Verify: checks/run_checks.sh && ./run parts/bom.py --offline --check && ./run uv run pytest tests/test_apply_fields.py -q
Hardware: none

## Goal
The schematic is the single source of part numbers. It holds when the BOM exported from the
schematic alone has an MPN on every placed part and the netlist is unchanged.

## Steps
1. Stop with `blocked` if par-03 is not accepted or a KiCad process is running. Export the
   netlist to `runs/par-04/before/`.
2. `parts/apply_fields.py`: for each ref in `parts/decisions.csv` (with the user's par-03
   choices applied), set symbol fields `MPN`, `Manufacturer`, `DigiKey`, `LCSC` in the sheet
   files under `kicad/`. Field edits only: no symbol, value, footprint, wire or position change.
   Dry-run mode prints the diff per ref. Tested on a copy of one sheet.
3. Apply, then export the netlist again and diff against step 1 (must be equal apart from the
   new fields). Run `checks/run_checks.sh`.
4. Remove the `parts/decisions.csv` merge path from `parts/bom.py` so the schematic is the only
   source; keep the CSV as the record of why. Re-run the BOM and commit `parts/out/`.

## Review
- Open sheets `rx`, `tx`, `mixer`, `power` and `fpga` in KiCad: spot-check the new fields on
  U1, U10, U14, U29, U30, U8, L5 and a few 0402 capacitors (C1, C48).
- Read the netlist-equality result in the Log.

## Out of scope
- Value, footprint or part changes that alter the design (a later design-change goal).
- Updating `production/`.

## Allowed commands
- `./run *`

## Log
