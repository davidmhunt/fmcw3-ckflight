# par-13: Final parts report for both boards: original vs chosen, and why
Status: awaiting review
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

### 2026-11-25
Commits:
- 6e35ecb par-13 step 2: parts/final_parts.csv, the one parts record for both boards (214 rows: 2rx and 1rx)
- 896add6 par-13 step 3: parts/inventory.csv, the parts bought into the JLC library (ADL5802 x3, YAT-3A+ x10, QPA9501 x8)
- 6631d06 par-13 step 4: parts/final_parts.py --check, the final parts record checks and report tables
- 0c5a354 par-13 step 5: analysis/13_parts_final report and deck from parts/final_parts.csv
- 9d0cc63 par-13 step 6: archive: true in deck.yaml sends old analyses to reports/archive/
- 5a9b2b2 par-13 step 7: tests/test_final_parts.py, the --check failures, the real record and archive routing
- e70b8a1 par-13: page evidence for U14 and FB4, applied/decided status, inventory dates, fallbacks to the user
Notes:
- Step 1 (preconditions), 2026-11-25. Read-only; nothing under kicad/ or kicad-1rx/ touched, nothing committed.
- par-03 is accepted: Status done, "Accepted by user: 2026-11-24 Choices per docs/par-03-choices.md". Precondition met, not blocked.
- par-09 is accepted (2026-11-24, routes per docs/par-03-choices.md); rx1-02 is accepted (2026-11-25, 1-RX choices per rx1- key). Neither awaits review, so no choice goes in as `pending review` and the title slide needs no pending-review line today. par-07 (U14 QPA9501TR13, accepted 2026-11-21) and par-11 (Accept auto, aps0650_ok = 1; its Log shows a blocked/unblocked review cycle that was fixed) are done. If a later directive reopens one, status in final_parts.csv is `pending review`.
- Records read: docs/par-03-choices.md (all keys incl. per-board tgrade, balun, opamp; atten U12 YAT-3A+, FB4 B with fallback A, ldo TPS7A4901DGNR with fallback, CON2 PJ-102AH, J2 C68234, LEDs KT-0603R, mixer U29 ADL5802 both, library A), parts/decisions.csv (53 refs, columns ref,MPN,Manufacturer,LCSC,DigiKey PN,Tolerance,Voltage,Dielectric,DNP,status,datasheet_id,page,reason; some rows still say for-user or user-choice and predate the accepted choices), parts/rx1_changes.csv (87 rows rx1-001.., kinds swap/net/value/new/dnp, board_row links to docs/board-changes.md), docs/board-changes.md (Part changes table with Board column; several rows still read "proposed" although the par-03 note decided them; the line "get a row here once the user decides them" is not yet done for the par-03 choices).
- Gaps for step 2 (final_parts.csv) to resolve from the records, not from memory: decisions.csv rows U3, U8, U12, U21, U30, U26-U28 carry old status/for-user text and must be overridden by the par-03 accept note; board-changes.md status for U30, FB4, U45, U26-U28, U21, SMA, U12, L5-L7, D1-D7, CON2/J2 is stale ("proposed") against the accept note and the par-03-choices table.
- Inventory facts for step 3: ADL5802ACPZ-R7 x3 C657785 2026-11-22 (1-RX U29); YAT-3A+ x10 C5205332 2026-11-24; QPA9501TR13 x8 C2911573 2026-11-24 (docs/par-03-choices.md).
- Open items to carry into the report: U21 fit (par-12 step 5), FB4 in sim-01, LT6232CGN pre-order/restock, rx1-05 simulation, TX 0.7 to 1.7 dB short of 25 dBm, 10 uF X5R derating on 12 V.
Verify: Verify passed: ./run uv run pytest tests/test_final_parts.py -q && ./run parts/final_parts.py --check && ./run tools/build_report.py analysis/13_parts_final --check && ./run tools/build_all.py --check
Independent review: gaps fixed in second review: 1. parts/final_parts.csv, U14 rows (2rx and 1rx) and FB4 rows (2rx and 1rx); report entries in analysis/13_parts_final (entries_rf and entries_power): Acceptance needs evidence given as manifest id and page for every substitution. The PA swap (TQP5525 to QPA9501TR13) and the FB4 bead swap list manifest ids with no page anywhere. The step-4 check only tests that the ids exist, so this was not caught. (evidence: U14 evidence = 'qorvo-qpa9501-datasheet; qorvo-qpa9501-sparams; qorvo-tqp5525-datasheet'. FB4 evidence = 'murata-blm18pg181sn1d-datasheet; murata-blm18kg221sn1d-model'. The built facts.json renders these as '**Evidence (manifest id, page):** 'qorvo-qpa9501-datasheet'; ...' with no page. CON2, U8 (2rx), U12 and U30 also have ids without pages, but each has at least one paged id.) 2. parts/final_parts.csv, status/applied_by columns (131 rows: 66 for 2rx, 65 for 1rx, all change none) and analysis/13_parts_final/writeup.md:32-33 with the counts tables built by figures.py: These rows say status 'applied' with an empty 'applied_by'. The report defines 'applied' as 'written into the board'. None of these parts has an MPN, LCSC or DigiKey field in the schematic: par-04 still has to write them. So the 'Status applied (written into the board)' counts on the counts slide and in the PDF are wrong, and so is the split between applied and decided. Because of this, U22-U25 (LD3920 to LD39200DPUR, a change listed in docs/board-changes.md:31) is also left out of the report entries. (evidence: A headless BOM export of kicad/ (bom.export_rows) gives MPN='' for U1 (row: ADF4158CCPZ-RL7, applied), U22 (LD39200DPUR, applied), U25, U33 and C28. The strings LD39200DPUR, FT2232HL-REEL and ADF4158CCPZ-RL7 do not appear in any kicad/*.kicad_sch. par-04 step 2 writes fields 'for each ref in parts/decisions.csv'. In figures.py, in_entries() drops rows with change none and status applied, so the U22-U25 board-changes row has a CSV row but no report entry.) 3. parts/inventory.csv lines 3-4; writeup.md section 3.3 and line 165; deck.yaml slide 'Inventory' note and the 'Open items (2 of 2)' bullet: The purchase dates of the YAT-3A+ and the QPA9501TR13 are left blank, and the report and deck say these dates are not on record. They are on record. This breaks the 'every number from a file on record' rule, and the report lists a records gap that does not exist. (evidence: docs/par-03-choices.md:33-35: 'YAT-3A+ x 10 (C5205332, 2026-11-24: ...), QPA9501TR13 PA x 8 (U14, C2911573, 2026-11-24; ...)'. inventory.csv has 'YAT-3A+,C5205332,10,,jlc-library,...' and 'QPA9501TR13,C2911573,8,,jlc-library,...'. Commit 896add6 says 'Purchase dates for YAT-3A+ and QPA9501 are not on record'.) 4. parts/final_parts.csv 1rx rows U8 (AD9237BCPZ-40), U26;U27 (HHM1907B1), U45 (LT6231CS8), U6 (PL133-37TC-R); 2rx and 1rx U3, U10: Acceptance needs a fallback in each substitution entry. These substitutions show 'none recorded' as the fallback. The report's open items do not send the missing fallbacks back to the user, as the Out of scope section requires for anything missing from the records. The record does name alternatives for some of them, for example rx1-opamp option A for U45. (evidence: The built entries show '**Alternatives and fallback:** none recorded' for the 1-RX U26/U27 balun, U8 AD9237, U45 LT6231, U3 and U10. writeup.md section 4 lists no missing fallbacks.) 5. Acceptance: not met: Every substitution named in the par-03 accept note, the rx1-02 and par-09 decisions and docs/board-changes.md has a row in parts/final_parts.csv and an entry in the report with its reason, evidence (manifest id and page) and fallback. (evidence: Every named substitution I checked has a CSV row: U30, U8 for both boards, U6 for each board, Y2/R19, L5-L7, U21, FB4, U14, U12, U3, U10, the baluns, U29, U45 for each board, the SMA connectors, LEDs, J2, CON2, J1, U17, the AD9237 decoupling, the straps, and receive chain 2 not fitted. But the U14 and FB4 entries have no page in any evidence id. The board-changes row for U22-U25 (LD3920 to LD39200DPUR) has a row but no report entry, because the row is marked change none and status applied. Several 1-RX substitutions (U8, U26/U27, U45) show 'none recorded' as the fallback.)
