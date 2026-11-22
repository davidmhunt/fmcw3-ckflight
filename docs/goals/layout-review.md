# layout-review: ERC/DRC triage, layout checks, testability and bring-up plan
Status: proposed
Base: falcon_development
Land: pr

## Goal
Review-plan Phases 4 and 5. Every ERC/DRC item is explained and either scheduled for a fix or
justified for exclusion, the layout is checked against each critical part's datasheet, and there
is a decided list of test points plus a bring-up procedure. It holds when the three reports
build and each ends with a list of proposed design changes for the user to accept or reject.

## Directives
1. lay-01: ERC/DRC triage with a disposition for every violation type
2. lay-02: Layout checks against datasheets (decoupling, thermal vias, grounding, bucks)
3. lay-03: Testability review and bring-up procedure

## Notes
- 2026-11-22: the 1-RX board is ordered (rx1-04, about 2026-11-27) before this goal runs, so its findings feed the 1-RX bring-up and gate the 2-RX order (late December).
- Written 2026-11-19; re-check against the post-restructure baseline in `checks/` before approval.
- Design changes proposed here are collected for a later design-change goal; none are made here.
- Carry-overs from fnd-01 (`docs/surveys/upstream-survey.md`), to be decided later by the user
  (2026-11-19):
  - Overstress history on FPGA pin M2 (adf_data) and the mixer enable: protection (lay-02).
  - A new fab package is needed before any order: `production/` is the 35T build.

## Rules
- Two boards (2026-11-22): `kicad/` is the 2-RX board (LTC2292, two receive chains) and `kicad-1rx/` the 1-RX board (AD9237, receive chain 2 not fitted, JLC-stock-only substitutes; its changes are in `parts/rx1_changes.csv`). Analyse a circuit once on `kicad/` and state that it covers both when `parts/rx1_changes.csv` does not touch it; otherwise analyse it per board (`--project kicad-1rx`) and report the two side by side. Findings say which board they apply to.

## Log
