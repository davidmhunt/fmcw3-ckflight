# parts: BOM from the schematic with DigiKey and JLCPCB availability, and datasheets
Status: running
Base: falcon_development
Land: pr

## Goal
Review-plan Phase 1. Every part on the board has an exact orderable part number stored in the
schematic, a known DigiKey and JLCPCB/LCSC status for N boards, and a datasheet that anyone can
fetch. It holds when `./run parts/bom.py --check` reports no placed part without an MPN and the
availability report lists no unresolved line.

Amended 2026-11-22 (the user's decision): two boards come out of this goal, each its own KiCad
project.
- **1-RX** (`kicad-1rx/`): the AD9237BCPZ-40 ADC, receive chain 2 not fitted, and JLCPCB-stocked
  parts only. Its small redesign is analysed and documented before the schematic changes. It is
  ready to order by Friday 2026-11-27.
- **2-RX** (`kicad/`): the full design with the LTC2292IUP#PBF bought through JLC's
  parts-sourcing service by the user, on hand late December or early January.

Both are 3 boards. The goal also holds when the 1-RX order package has been taken by JLCPCB's
quote page with every line in stock (rx1-04).

## Directives
1. par-01: BOM export from the schematic and automated DigiKey + JLCPCB checks
2. par-02: Datasheet manifest and download script for the critical parts
3. par-03: Resolve part numbers and report availability
4. par-06: Datasheets through DigiKey for every BOM part, with a DigiKey link for what still
   fails (added 2026-11-21 at the user's request)
5. par-07: Replacement candidates for the discontinued TQP5525 power amplifier (U14) (added
   2026-11-21 at the user's request)
6. par-08: Simulation models for every part the planned analyses need (added 2026-11-21 at the
   user's request)
7. par-09: JLC sourcing plan for every line JLCPCB cannot place today (added 2026-11-21 at the
   user's request)
8. par-10: Stock watch for hard-to-source parts, ADC first (added 2026-11-21 at the user's
   request)
9. rx1-01: 1-RX KiCad project, and tools that take a project (added 2026-11-22)
10. rx1-02: 1-RX design: AD9237 ADC, RX2 not fitted, JLC-stock-only parts, each change checked
   (added 2026-11-22)
11. par-11: Load budget for the three buck rails and the APS0650M330A inductor check (added
   2026-11-23 at the user's request)
12. par-04: Write MPN, DigiKey and LCSC fields into the schematic symbols (both projects,
   amended 2026-11-22)
13. par-12: Apply the par-03 part changes to the 2-RX schematic: L5-L7, Y2 and R19, and a package
   scan of every placed part (added 2026-11-23 at the user's request)
14. rx1-03: Apply the 1-RX schematic changes in kicad-1rx/ (added 2026-11-22; L5-L7, Y2 and R19
   amended 2026-11-23)
15. par-05: Ordering BOMs from the schematic that DigiKey and JLCPCB ingest directly (added
   2026-11-21 at the user's request; `--project`, amended 2026-11-22)
16. rx1-04: 1-RX fabrication and JLCPCB order package (added 2026-11-22)

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

## Rules
- Prefer parts JLCPCB stocks in enough quantity for `board_quantity`, so JLCPCB buys and places
  them. Consign from DigiKey only when no JLC-stocked part fits, and say why none fits. Rank
  JLC-stocked options first in every comparison and recommendation. (The user, 2026-11-21:
  consignment delays the build a lot compared with ordering through JLCPCB.)
- Record every proposed, chosen or applied change to the upstream board in
  `docs/board-changes.md`: what changed, why, the evidence, the simulation or analysis that
  covers it, and its status. A changed part with no covering simulation must say so. (The user,
  2026-11-21: changes must be simulated and documented.)
- `kicad-1rx/` is under the same CLAUDE.md rules as `kicad/`: check `tools/kicad_ipc.py status
  --project kicad-1rx` before any write, never write while it is open, and layout and part
  choices are the user's.
- 1-RX board: every placed part is in JLCPCB stock for `board_quantity` at the time of the order;
  no consignment and no sourcing service. (The user, 2026-11-22.)
- The firmware repo `davidmhunt/fmcw3-ckflight-fw` is read only in this goal; the 1-RX firmware
  is a later goal there.

## Log
