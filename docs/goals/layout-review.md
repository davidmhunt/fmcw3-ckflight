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
- Written 2026-11-19; re-check against the post-restructure baseline in `checks/` before approval.
- Design changes proposed here are collected for a later design-change goal; none are made here.
- Carry-overs from fnd-01 (`docs/surveys/upstream-survey.md`), to be decided later by the user
  (2026-11-19):
  - Overstress history on FPGA pin M2 (adf_data) and the mixer enable: protection (lay-02).
  - A new fab package is needed before any order: `production/` is the 35T build.

## Log
