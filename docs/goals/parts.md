# parts: BOM from the schematic with DigiKey and JLCPCB availability, and datasheets
Status: proposed
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

## Notes
- Written 2026-11-19 with goal `foundation`; re-check against `docs/surveys/upstream-survey.md`
  and the foundation layout before approval.
- Needs the user's DigiKey API keys in `.env` (see `docs/setup.md`).

## Log
