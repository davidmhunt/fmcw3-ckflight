# parts: BOM from the schematic with DigiKey and JLCPCB availability, and datasheets
Status: blocked: par-03
Base: falcon_development
Land: pr

## Goal
Review-plan Phase 1. Every part on the board has an exact orderable part number stored in the
schematic, a known DigiKey and JLCPCB/LCSC status for N boards, and a datasheet that anyone can
fetch. It holds when `./run parts/bom.py --check` reports no placed part without an MPN and the
availability report lists no unresolved line.

## Directives
1. par-01: BOM export from the schematic and automated DigiKey + JLCPCB checks
2. par-02: Datasheet manifest and download script for the critical parts
3. par-03: Resolve part numbers and report availability
4. par-04: Write MPN, DigiKey and LCSC fields into the schematic symbols
5. par-05: Ordering BOMs from the schematic that DigiKey and JLCPCB ingest directly (added
   2026-11-21 at the user's request)

## Notes
- Written 2026-11-19 with goal `foundation`; re-check against `docs/surveys/upstream-survey.md`
  and the foundation layout before approval.
- Needs the user's DigiKey API keys in `.env` (see `docs/setup.md`).
- Carry-overs from fnd-01 (`docs/surveys/upstream-survey.md`), to be decided later by the user
  (2026-11-19):
  - FPGA XC7A35T vs XC7A100T: price, stock and 35T pin validity (par-03).
  - `production/` is the as-ordered 35T build (R26/R28/R31/R38 = 500 ohm, now 1k); any new order
    needs a new fab package at a new path.
  - `kicad/libs/fmcw3.lib` (retired part ideas) is kept until this goal is done, then reconsidered (par-03).

## Decisions (re-check against foundation, 2026-11-21)
- par-02 fills the existing sources pipeline (`datasheets/manifest.yaml`,
  `tools/fetch_sources.py`) instead of adding a second manifest and script.
- par-04 writes the schematic fields by file edit with KiCad closed; KiCad 10 has no schematic
  API, so the IPC `set-fields` path waits for KiCad 11.
- The DigiKey keys are in `.env`. The board count comes from the target set's `board_quantity`
  (the user set it to 3 in `default.yaml` on 2026-11-21); `--boards` overrides it.
- New command-line tools go into `MANUAL.md` (repo rule).

## Log
