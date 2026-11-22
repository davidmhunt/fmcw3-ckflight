# lay-02: Layout checks against datasheets (decoupling, thermal vias, grounding, bucks)
Status: proposed
Goal: layout-review
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_layout_extract.py -q && ./run tools/build_report.py analysis/05_layout --check
Hardware: none

## Goal
The checks ERC/DRC cannot do, made from the board file and compared with each critical part's
datasheet layout guidance. It holds when the `05_layout` report gives a pass, concern or fail
with evidence for each check and each critical part.

## Steps
1. `analysis/05_layout/extract.py` (tested on small fixture boards): per IC power pin, the
   decoupling capacitors on that net with value and distance to the pin; per exposed pad, the
   via count and drill; per RF net, ground-plane continuity on L2/L5 under the trace; buck
   switch-node copper area and its distance to RF and IF nets; distance between the RX and TX
   SMA launches.
2. Compare with the datasheets (via par-02) for U1, U10, U14, U11/U16, U9/U13, U29, U45, U8,
   U17-U19 and the LDOs: recommended decoupling, pad via pattern, layout notes. Record page
   references. Overstress history (survey: `docs/surveys/upstream-survey.md`): the FPGA `adf_data` pin M2 burned once and the
   mixer may have (firmware 82e9b33, 0498d51); check drive levels, series resistance and ESD on
   ADF_DATA and the enable lines (mix_en J4, pa_en T2) against each receiver's absolute maximum,
   and propose protection as an open decision.
3. Power tree: confirm the rail map of the review plan from the netlist, with the load current
   budget per rail from datasheet typical and maximum currents, and regulator headroom and
   dissipation.
4. Report and deck: one slide per check with an annotated board crop, a summary matrix (part by
   check), and the proposed changes. Measurements come from the board file read headless; when
   the project is open in KiCad, `tools/kicad_ipc.py show` selects the parts and nets of each
   check so the user can follow along (fnd-06).

## Acceptance
- Each critical part in step 2 has a row in the summary matrix with a result for each check and a datasheet page.
- Every "concern" or "fail" has a board image and a measured number.
- The power budget table sums to a 12 V input current and names its assumptions.
- The deck has no more than 25 slides.

## Review
- Open `reports/05_layout.pptx`: the summary matrix, then each "fail" slide beside the board in KiCad.

## Out of scope
- Layout edits.
- Thermal simulation.

## Rules
- On 1-RX also check the AD9237 (U8) decoupling, exposed-pad vias and grounding against its datasheet, and every footprint `parts/rx1_changes.csv` changes; the rest is checked once on `kicad/`. (amended 2026-11-22 for the two-board plan)

## Allowed commands
- `./run *`

## Log
