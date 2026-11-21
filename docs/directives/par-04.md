# par-04: Write MPN, DigiKey and LCSC fields into the schematic symbols
Status: approved
Goal: parts
Node: any
Deliverable: code
Accept: user
Verify: ./run checks/run_checks.sh && ./run parts/bom.py --offline --check && ./run uv run pytest tests/test_apply_fields.py -q
Hardware: none

## Goal
The schematic is the single source of part numbers. It holds when the BOM exported from the
schematic alone has an MPN on every placed part and the netlist is unchanged.

## Steps
1. Stop with `blocked` if par-03 is not accepted. Export the netlist to `runs/par-04/before/`.
2. `parts/apply_fields.py`: for each ref in `parts/decisions.csv` (with the user's par-03
   choices applied), build the field set `MPN`, `Manufacturer`, `DigiKey`, `LCSC`. Field edits
   only: no symbol, value, footprint, wire or position change. Dry-run mode prints the diff per
   ref. One backend: it edits the `.kicad_sch` files directly, and only when
   `./run --native tools/kicad_ipc.py status` prints `closed`; otherwise it refuses. (Amended
   2026-11-21 at the user's request: KiCad 10 has no schematic API (fnd-06 trial), so the IPC
   `set-fields` path waits for KiCad 11.) Tested on a copy of one sheet: fields added, every
   other byte of the S-expression unchanged apart from the new field nodes.
3. Apply. If status is not `closed`, stop and ask the user to close KiCad. Apply, then export the
   netlist again and diff against step 1 (must be equal apart from the new fields). Run
   `./run checks/run_checks.sh`. Ask the user to reopen KiCad and spot-check (see Review).
4. Remove the `parts/decisions.csv` merge path from `parts/bom.py` so the schematic is the only
   source; keep the CSV as the record of why. Re-run the BOM and commit `parts/out/`.

## Review
- Open sheets `rx`, `tx`, `mixer`, `power` and `fpga` in KiCad: spot-check the new fields on
  U1, U10, U14, U29, U30, U8, L5 and a few 0402 capacitors (C1, C48).
- Read the netlist-equality result in the Log.

## Out of scope
- Value, footprint or part changes that alter the design (a later design-change goal).
- Updating `production/`.

## Rules
- Never write `kicad/*.kicad_sch` while KiCad has the project open; `status` must print `closed`
  immediately before the write.
- Field edits only: no value, symbol, footprint, wire or position change.

## Allowed commands
- `./run *`

## Log
