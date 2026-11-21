# par-05: Ordering BOMs from the schematic that DigiKey and JLCPCB ingest directly
Status: approved
Goal: parts
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests/test_order_bom.py -q && ./run parts/order_bom.py --check && friday result check par-05 --require 'digikey_ingested == 1' --require 'jlc_ingested == 1' --files
Hardware: none

## Goal
The part-number fields written into the schematic in par-04 are enough to order: one command
exports a DigiKey upload file and a JLCPCB assembly BOM and placement file from the schematic
alone, and both services accept them as uploaded, without hand edits, to check final
availability. It holds when the files pass the format tests and the user has uploaded both and
recorded that each service matched every line. (Added 2026-11-21 at the user's request.)

## Steps
1. Find each service's current upload format from its own documentation, downloaded into
   `docs/references/manifest.yaml` and checked against the file:
   - DigiKey: the BOM Manager / myLists upload (CSV or XLSX), with its column names (DigiKey part
     number or manufacturer part number, manufacturer, quantity, customer reference).
   - JLCPCB: the assembly BOM (Comment, Designator, Footprint, LCSC Part #) and the CPL
     (Designator, Mid X, Mid Y, Layer, Rotation) for the assembly quote page.
2. `parts/order_bom.py [--targets NAME] [--boards N] [--check]`: reads only the schematic
   (`kicad-cli sch export bom` with the `MPN`, `Manufacturer`, `DigiKey` and `LCSC` fields) and
   the board (`kicad-cli pcb export pos` for the CPL). It never reads `parts/decisions.csv`.
   Writes `parts/out/order/digikey_bom.csv`, `jlc_bom.csv` and `jlc_cpl.csv`:
   - quantities per board times the target set's `board_quantity`, plus spares;
   - DNP parts left out;
   - parts JLCPCB will not place (hand-solder, for example the SMA connectors) left out of
     the JLC files and kept in the DigiKey file;
   - CPL rotations corrected for JLCPCB where a footprint's zero rotation differs, from a
     committed `parts/jlc_rotations.csv`, each row with a reason.
   `--check` exits non-zero on a placed part missing the fields its service needs, a designator in
   one JLC file and not the other, or a column the format does not allow.
3. `tests/test_order_bom.py`: on a fixture BOM and position export, the column names and order,
   quantity scaling, DNP and hand-solder handling, rotation corrections, and `--check` failures.
4. Live check by the user (the agent never uploads to an account):
   - upload `digikey_bom.csv` to DigiKey BOM Manager;
   - upload `jlc_bom.csv` and `jlc_cpl.csv` (with the Gerbers from a new path, never
     `production/`) to a JLCPCB assembly quote, up to the parts-review page, without ordering;
   - report for each: did it ingest without edits, how many lines matched, which lines did not
     and why, plus screenshots if useful.

   Fix any format issue the services raise and repeat. Then record
   `friday result write par-05 --metric digikey_ingested=<0|1> --metric jlc_ingested=<0|1>
   --metric digikey_unmatched=<n> --metric jlc_unmatched=<n> --file parts/out/order/digikey_bom.csv
   --file parts/out/order/jlc_bom.csv --file parts/out/order/jlc_cpl.csv`.
5. Add `parts/order_bom.py` to `MANUAL.md` (parts section) and `parts/README.md`: how to export
   and upload each file, and what to check on each service's page.

## Rules
- The agent never logs in, uploads, quotes or orders on DigiKey or JLCPCB; the user does.
- Never regenerate or modify `production/`; any Gerbers for the quote go to a new path.
- The schematic and board are read headless; nothing under `kicad/` is written.

## Review
- Read the Log's upload results: both ingested without edits, and the unmatched lines explained.
- Open `parts/out/order/jlc_cpl.csv` next to the JLCPCB placement preview for U30, U8, one connector
  and one 0402 part: rotations and positions look right.

## Out of scope
- Placing an order or paying for a quote.
- Changing parts to fix unmatched lines (a decision for the user, fed back through par-03).

## Allowed commands
- `./run *`
- `friday result write par-05 *`

## Log
