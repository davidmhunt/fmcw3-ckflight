# lay-01: ERC/DRC triage with a disposition for every violation type
Status: proposed
Goal: layout-review
Node: any
Deliverable: slides
Accept: user
Verify: checks/run_checks.sh && ./run uv run python analysis/04_erc_drc/triage.py --check && ./run tools/build_report.py analysis/04_erc_drc --check
Hardware: none

## Goal
Every ERC and DRC violation in the current reports has a written disposition: fix (and how),
exclude (and why), or ignore (and why). It holds when `triage.py --check` finds no violation
type or error-severity item without a disposition.

## Steps
1. `analysis/04_erc_drc/triage.py`: load fresh ERC/DRC JSON, group by type, severity, sheet or
   layer, and join with `dispositions.csv` (type or item, disposition, reason, owner, proposed
   change). `--check` exits non-zero on an undisposed type or error.
2. Fill `dispositions.csv`. Examine individually: every error; `pin_to_pin` (U40 WP/HOLD);
   `power_pin_not_driven` (GND); the 6 `isolated_copper` islands; the 4 `clearance` items on
   coupler Z1 (compare the footprint geometry with the intended 15 dB coupler); the
   `solder_mask_bridge` items against JLCPCB's minimum mask web; library-link items left after
   fnd-02.
3. Check the design rules in `kicad/fmcw3.kicad_pro` against JLCPCB's published 6-layer
   capabilities (track/space, via drill and annular ring, mask web) and list any rule looser
   than the fab's limit.
4. Report and deck: counts by type with a chart, the disposition table, board or schematic
   image for each individually examined item, and the list of proposed fixes.

## Acceptance
- Every violation type present in the current reports has a row in the disposition table.
- Every error-severity item is discussed individually with its location.
- Each "exclude" or "ignore" gives a reason a reviewer can check; each "fix" names sheet or layer and refdes.
- The fab-rule comparison cites JLCPCB's capability page and date.
- The deck has no more than 20 slides.

## Review
- Open `reports/04_erc_drc.pptx`: the proposed-fixes slide and the Z1 coupler slide. Accept or
  reject each proposed fix in your acceptance note.

## Out of scope
- Applying fixes or exclusions to the project files.

## Rules
- Triage both projects, each against its own baseline (`checks/baseline.json`, `checks/baseline-1rx.json`); the design-rule check against JLCPCB's limits is shared. (amended 2026-11-22 for the two-board plan)

## Allowed commands
- `./run *`

## Log
