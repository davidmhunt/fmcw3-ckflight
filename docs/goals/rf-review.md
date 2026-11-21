# rf-review: RF level plan and 50 ohm impedance review
Status: proposed
Base: falcon_development
Land: pr

## Goal
Review-plan Phases 2 and 3. The signal level, noise figure and compression margin at every RF
node are known for a chosen target set, and every RF trace's impedance is computed from the real
layout geometry and a real fab stackup. It holds when both reports rebuild for any target set
with one command and list their findings and open decisions.

## Directives
1. rf-01: RF level plan (gain, noise figure, compression) for TX, LO and RX
2. rf-02: Transmission-line impedance from the layout and fab stackup

## Notes
- Written 2026-11-19; re-check against `docs/analysis-tools.md` (fnd-05) and the datasheet
  manifest (par-02) before approval. Needs the user's target set in `analysis/targets/`.
- Carry-overs from fnd-01 (`docs/surveys/upstream-survey.md`), to be decided later by the user
  (2026-11-19):
  - ADF4158 PFD 40 MHz vs a 32 MHz comment in the firmware (rf-01; loop filter in sim-03).
  - IF and ADC numbers from the firmware as design intent (rf-01).
  - One design only, on the JLCPCB stackup (rf-02).
  - Overstress on ADF_DATA and the mixer enable is checked in lay-02.

## Rules
- Every circuit-level simulation (for example the passive checks in rf-01) is committed both as a
  netlist and as an LTspice schematic (`.asc`) that the user can open with `./run --sim-gui
  ltspice <file>.asc`. The agent draws the first version; the user may modify it. A test checks
  that the two describe the same circuit. (User decision 2026-11-20.)
- Every writeup shows the KiCad schematic sheet or board area it analyses, exported with
  `kicad-cli sch export svg` or `kicad-cli pcb export svg`, naming the refdes and nets involved.

## Log
