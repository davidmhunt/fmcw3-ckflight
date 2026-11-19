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

## Log
