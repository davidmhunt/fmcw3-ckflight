# par-13: Final parts report for both boards: original vs chosen, and why
Status: approved
Goal: parts
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_final_parts.py -q && ./run parts/final_parts.py --check && ./run tools/build_report.py analysis/13_parts_final --check && ./run tools/build_all.py --check
Hardware: none

## Goal
One polished report and deck for a design review: the parts on both boards, what each
substitution replaced, why, what analysis or check backs it, its fallback, how it is bought and
which directive applies it. It holds when `reports/13_parts_final.pdf` and its deck build from a
single committed parts record, every substitution in the par-03 accept note, the rx1-02 and par-09
decisions and `docs/board-changes.md` appears with its reason and evidence, and the earlier parts
decks build into `reports/archive/`. (Added 2026-11-24 at the user's request: condense the
par-03, par-07, par-09, par-11 and rx1-02 decks into one.)

## Steps
1. Preconditions. Stop with `blocked` if par-03 is not accepted. Read the par-03 accept note,
   `docs/par-03-choices.md`, `parts/decisions.csv`, `parts/rx1_changes.csv`,
   `docs/board-changes.md` and the Logs of par-07, par-09, par-11 and rx1-02. Where rx1-02 or
   par-09 is still awaiting review, their choices go in as `pending review`, and the report says
   so on its title slide.
2. `parts/final_parts.csv`, the one committed record both reports read. One row per placed ref
   group and board (`2rx`, `1rx`), columns: `board`, `refs`, `role`, `original_mpn`,
   `chosen_mpn`, `manufacturer`, `lcsc`, `digikey_pn`, `change` (`none`, `fields`, `footprint`,
   `design`), `route` (`jlc-stock`, `jlc-library` (bought by the user into the JLC parts
   library), `jlc-sourcing`, `hand-solder`), `reason`, `evidence` (manifest ids with pages),
   `analysis` (directive or analysis folder, e.g. par-11, sim-01 planned), `fallback`,
   `applied_by` (par-04, par-12, rx1-03), `status` (`decided`, `pending review`, `applied`),
   `fitted` (no for DNP parts). Passives that did not change may be one row per value class with
   their refs, as `parts/decisions.csv` groups them.
3. `parts/inventory.csv`: parts the user has bought, one row each: `mpn`, `lcsc`, `qty`, `date`,
   `held` (`jlc-library`, `digikey`, `on-hand`), `for` (board and refs). Today: ADL5802ACPZ-R7 x 3
   (1-RX U29), YAT-3A+ x 10 (U12, both), QPA9501TR13 x 8 (U14, both). The user adds rows as they
   buy; par-14 reads it.
4. `parts/final_parts.py [--check]`: loads both files and checks them: every `evidence` id exists
   in `datasheets/manifest.yaml`; every `lcsc` exists in the local JLC database; every ref placed
   on either board (headless netlist of `kicad/` and `kicad-1rx/`) is in exactly one row for that
   board, DNP parts with `fitted` no; every row with `change` other than `none` has a `reason`
   and `evidence`; every `jlc-library` row has an inventory row. Exit 1 on any failure. It also
   writes `analysis/13_parts_final/build/` tables (CSV) for the report.
5. `analysis/13_parts_final/` (`writeup.md`, `deck.yaml`, `figures.py`), built with
   `./run tools/build_report.py analysis/13_parts_final`. Sections:
   - summary: both boards side by side, counts by route and by change class, what is bought,
     sourced or hand-soldered, and the open checks;
   - one entry per substitution, grouped (FPGA, ADC and clock; power: inductors, bucks, LDO, FB4;
     RF: PA, mixer, baluns, attenuators, SMA; IF op-amp; connectors and LEDs; 1-RX only: AD9237,
     receive chain 2 not fitted, straps), each with original and chosen part, board(s), reason,
     the analysis or datasheet check behind it, the alternatives considered and why they lost,
     the fallback, and the directive that applies it;
   - sourcing: the 2-RX JLC sourcing order, the DigiKey hand-solder order, the inventory;
   - open items: U21 fit (par-12 step 5), FB4 in sim-01, LT6232CGN pre-order, anything else in
     the records still open.
   The deck has no more than 20 slides; the full per-substitution table is in the PDF.
6. Archive: `deck.yaml` gets an optional `archive: true` key; `tools/build_all.py` and
   `tools/build_report.py` write an archived analysis to `reports/archive/` instead of `reports/`.
   Set it on `00_baseline`, `01_parts`, `02_pa`, `03_sourcing`, `11_board_1rx` and
   `12_rail_loads`. Their sources stay in place, so every directive's Verify still passes.
   `reports/README.md` lists the two current parts reports (13 and 14) first, then the archive.
   Update `MANUAL.md` (the `archive` key) and the report tests.
7. `tests/test_final_parts.py`: on a fixture, the `--check` failures of step 4 (unknown manifest
   id, ref in no row or two rows, change without reason, library row without inventory); on the
   real files, `--check` passes; the archive key routes output to `reports/archive/`.

## Acceptance
- Every substitution named in the par-03 accept note, the rx1-02 and par-09 decisions and
  `docs/board-changes.md` has a row in `parts/final_parts.csv` and an entry in the report with its
  reason, evidence (manifest id and page) and fallback.
- Both boards are covered side by side; 1-RX-only changes and DNP parts are marked.
- The report states which choices are pending review, if any.
- The deck has no more than 20 slides; earlier parts decks build into `reports/archive/`.

## Review
- Open `reports/13_parts_final_ppt.pdf` and `reports/13_parts_final.pdf`: check that each
  substitution reads correctly (original, chosen, why, fallback) and that nothing you decided is
  missing.
- Open `parts/final_parts.csv` and `parts/inventory.csv`: the record the reports are built from.

## Out of scope
- Schematic or board edits (par-04, par-12, rx1-03).
- New part decisions: anything missing from the records goes back to the user.
- Live stock checks (par-14).

## Rules
- Never write `kicad/` or `kicad-1rx/`; read them headless only.
- Every number in the report comes from a file on record (manifest id and page, or an analysis
  folder); nothing from memory.
- Never commit `reports/*.pdf` or `*.pptx`, in `reports/archive/` too.

## Allowed commands
- `./run *`

## Log
