# par-12: Apply the par-03 part changes to the 2-RX schematic (L5-L7 to APS0650M330A first)
Status: approved
Goal: parts
Node: any
Deliverable: code
Accept: user
Verify: ./run checks/run_checks.sh && ./run checks/run_checks.sh --project kicad-1rx && ./run parts/bom.py --offline --check && ./run uv run pytest tests/test_par03_changes.py -q
Hardware: none

## Goal
`kicad/` carries the part changes the user chose in par-03 that are more than field edits, so the
user can update the 2-RX PCB. par-04 writes fields only. The first such change is L5-L7: the user
chose the Coilank APS0650M330A (33 uH, 7.7 x 6.6 mm, JLC C47327223) on 2026-11-23, in place of the
SRR6040A-330M, for both boards. It holds when every netlist difference from the par-04 state is a
row of `parts/par03_changes.csv`, the new footprint matches the datasheet land pattern, and ERC
has no error type above the baseline.

## Steps
1. Preconditions. Stop with `blocked` if par-03 is not accepted, par-04 is not done, or par-11 does
   not have `aps0650_ok == 1`. Run `./run --native tools/kicad_ipc.py status` and
   `status --project kicad-1rx`; if either does not print `closed`, stop and ask the user to close
   KiCad.
2. `parts/par03_changes.csv`: one row per ref for every par-03 choice the user accepted that changes
   a symbol, value or footprint (read the accept note in the par-03 Log). Columns as
   `parts/rx1_changes.csv`. Today that is L5, L6, L7 (footprint and fields); add any others the
   accept note names.
3. Footprint `APS0650` in the project footprint library of `kicad/` and of `kicad-1rx/` (the same
   file content in both), from the land pattern in coilank-aps1040m330a-datasheet p.1 (the APS
   series sheet; APS0650 row: F 8.4, G 3.5, H 3.6 mm, body A 6.6, B 7.7 max, C 5.0 max). Pads
   along Y with pad 1 at -Y, as the current `fmcw3:SRR6040A`, so Update PCB keeps the
   orientation. Courtyard 0.25 mm around the larger of body and pads; silk and fab outlines on
   the body.
4. Fit check, headless, on both boards: place the new footprint at each of L5, L6 and L7's
   current position and rotation and report the clearance to the board edge and to every
   neighbouring courtyard, and the pad overlap with the current copper. Report any overlap; do not
   move parts (placement is the user's).
5. Apply in `kicad/` only: the footprint field of L5-L7 to the new footprint, and the `MPN`,
   `Manufacturer`, `LCSC` (C47327223) and `DigiKey` fields (DigiKey: say if none). Then the other
   rows of step 2. `kicad-1rx/` gets the same L5-L7 change in rx1-03.
6. `tests/test_par03_changes.py`: export the netlist headless and check that every difference from
   the par-04 netlist is a row of `parts/par03_changes.csv`, every row is present, and the
   footprint's pads match the datasheet numbers of step 3.
7. ERC on `kicad/`; explain or fix any new error type. Update the L5-L7 rows of
   `docs/board-changes.md` (status `applied (<commit>)`, the par-11 load result, the fit check).
8. Ask the user to open `kicad/` and run Update PCB from Schematic, then check the step 4 fit and
   reconnect the pads. Placement and routing are theirs.

## Review
- Open `kicad/` sheet `power`: L5-L7 footprint and fields.
- Open the footprint `APS0650` in the footprint editor and compare its pads with the datasheet p.1.
- Read the step 4 fit check and the netlist-test result in the Log.

## Out of scope
- Writing `kicad-1rx/` schematics (rx1-03); only the shared footprint file is written there.
- Placement and routing (the user).
- Changes the user did not accept in par-03.

## Rules
- Write `kicad/` and `kicad-1rx/` files only right after `status` (with and without
  `--project kicad-1rx`) prints `closed`.
- Only the changes in `parts/par03_changes.csv`; no other symbol, value, footprint, wire or
  position change.

## Allowed commands
- `./run *`

## Log
