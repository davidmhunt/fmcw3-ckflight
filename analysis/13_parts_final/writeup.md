---
title: "Final parts for the 2-RX and 1-RX boards: original, chosen, why"
---

# 1. Summary

This report lists the parts on both boards, what each substitution replaced, why, which analysis or
datasheet check backs it, the alternatives and the fallback, how the part is bought and which
directive applies it. It is built from one committed record, `parts/final_parts.csv` (one row per
ref group and board), and `parts/inventory.csv` (the parts the user has bought). `parts/final_parts.py
--check` verifies the record against both schematics, the datasheet manifest and the JLC database.
Nothing under `kicad/` or `kicad-1rx/` was changed; the changes are applied by par-04, par-12 and
rx1-03.

**Review status.** Rows pending review: **{{fact:pending_n}}**. par-03 (accepted 2026-11-24, choices in
`docs/par-03-choices.md`), par-09 (2026-11-24) and rx1-02 (2026-11-25) are accepted, so every choice
below is `decided` or `applied`. If a later directive reopens one, its row becomes `pending review` and
the title slide of the deck must say so (the build stops until it does).

The record holds {{fact:rows}} rows: {{fact:rows_2rx}} for the 2-RX (`kicad/`) and {{fact:rows_1rx}}
for the 1-RX (`kicad-1rx/`). The 2-RX has {{fact:refs_2rx}} placed refs, {{fact:fitted_2rx}} fitted
and {{fact:notfit_2rx}} not fitted (upstream DNP); the 1-RX has {{fact:refs_1rx}} placed refs,
{{fact:fitted_1rx}} fitted and {{fact:notfit_1rx}} not fitted. Of the 1-RX refs not fitted,
{{fact:rx1rx2_refs}} are receive chain 2 and its related parts.

## 1.1 Counts, both boards side by side

Routes: `jlc-stock` is bought and placed by JLCPCB; `jlc-library` is bought by the user into the JLC
parts library; `jlc-sourcing` is consigned through JLC global sourcing (2-RX only: the 1-RX has no
consignment); `hand-solder` is bought from DigiKey and soldered by the user. Change classes: `none`
(as on upstream's schematic), `fields` (MPN or ordering fields only), `footprint` (new land pattern or
pin map), `design` (circuit, net or DNP change). Status: `applied` means nothing is left to write (a ref
with no part to buy, or DNP as on upstream's board); `decided` is every placed part whose MPN, LCSC or
DigiKey field is not in the schematic yet, or whose change is not made yet: it waits for par-04
(fields), par-12 (2-RX) or rx1-03 (1-RX). No MPN of the unchanged parts is in a schematic today (a
headless BOM export of `kicad/` shows none for U1, U22, U25, U33 or C28), so they count as `decided`.

{{fact:t_counts}}

## 1.2 What is bought, sourced or hand-soldered

- Bought into the JLC parts library by the user: see section 3.3 (ADL5802ACPZ-R7, YAT-3A+, QPA9501TR13).
- 2-RX JLC sourcing order: section 3.1 ({{fact:sourcing_lines}} lines, {{fact:sourcing_qty}} parts for
  {{fact:n_boards}} boards).
- DigiKey hand-solder order (SMA connectors): section 3.2 ({{fact:handsolder_qty}} connectors for
  {{fact:n_boards}} boards of each type).
- Everything else with a part is a JLC-stock line that JLCPCB buys and places from its own stock;
  par-14 checks its stock against the need.

## 1.3 Both boards, part by part

One line per substituted or decided ref group; `-` means the ref is not on that board, "(not fitted)"
means it is on the board but not fitted. The 1-RX receive chain 2 parts are summarised in section 2.7.

{{fact:t_side}}

## 1.4 Open checks

The open items are collected in section 4; the main ones are the U21 fit (par-12 step 5), the FB4
simulation (sim-01), the LT6232CGN pre-order and the 1-RX start-up simulation (rx1-05).

# 2. Substitutions by group

Each entry gives the original and chosen part, the board or boards, the reason, the evidence (datasheet
manifest id and PDF page, from `datasheets/manifest.yaml`), the analysis behind it, the alternatives
that were considered with the fallback, and the directive that applies it. Where the two boards
differ, the entry shows `2-RX:` and `1-RX:` separately. An evidence id with no page is a data file
(S-parameters or a model), which has no pages; `parts/final_parts.py --check` requires a page for a
changed row that cites datasheet PDFs. "none recorded" means the record names no alternative or analysis;
it is not a claim that none exists. Every substitution with no fallback on record is listed in section
4.1 for the user to answer.

## 2.1 FPGA, ADC and clock

{{fact:t_g_fpga}}

{{fact:entries_fpga}}

## 2.2 Power: inductors, bucks, LDO, FB4

{{fact:t_g_power}}

{{fact:entries_power}}

## 2.3 RF: PA, mixer, baluns, attenuators, SMA

{{fact:t_g_rf}}

{{fact:entries_rf}}

## 2.4 IF op-amp

{{fact:t_g_if}}

{{fact:entries_if}}

## 2.5 Connectors and LEDs

{{fact:t_g_conn}}

{{fact:entries_conn}}

## 2.6 1-RX only: AD9237 and its decoupling

{{fact:t_g_rx1adc}}

{{fact:entries_rx1adc}}

## 2.7 1-RX only: receive chain 2 not fitted

{{fact:t_g_rx1rx2}}

{{fact:entries_rx1rx2}}

## 2.8 1-RX only: straps, bias and rail order

{{fact:t_g_rx1straps}}

{{fact:entries_rx1straps}}

# 3. Sourcing

Quantities are refs per board times `board_quantity` of the target set ({{fact:n_boards}} boards of
each type), without spares; par-14 adds spares and checks stock.

## 3.1 The 2-RX JLC sourcing order

Parts that JLC does not stock, consigned through JLC global sourcing. The 1-RX has none.

{{fact:t_sourcing_2rx}}

## 3.2 The DigiKey hand-solder order

{{fact:t_handsolder}}

## 3.3 Inventory

The parts the user has bought into the JLC parts library (`parts/inventory.csv`). Need is the fitted
`jlc-library` refs times `board_quantity`; spare is bought minus need. Dates are from the file
(`docs/par-03-choices.md` for the 2026-11-24 purchases of the YAT-3A+ and the QPA9501TR13);
{{fact:inventory_missing_dates}} line(s) have no date.

{{fact:t_inventory_need}}

# 4. Open items

These come from the Analysis, Fallback and Reason columns of `parts/final_parts.csv`, the open findings
in `docs/board-changes.md` and the records read for this report. None was decided by the agent.

- **U21 fit (par-12 step 5).** The TPS7A4901DGNR (HVSSOP-8 with thermal pad) goes where the LP2985A-10DBVR
  was; about 3.6 x 5.7 mm is free against about 3.1 x 5.8 mm with no vias, so C85 or C102 may move about
  1 mm. If it does not fit, the record's fallback is re-evaluated with the user: the 2-RX keeps the
  LP2985A-10DBVR (sourced), the 1-RX takes the TPS7A2401DBVR with a divider and a noise check.
- **FB4 in sim-01.** The BLM18KG221SN1D model (fetched by par-08) must be used in the 5 V branch before the
  bead is final; the fallback is the original BLM18PG181SN1D (C82850) if a new resonance with the PA
  decoupling shows up.
- **LT6232CGN pre-order.** JLC showed 2 in stock for 3 boards (pre-order only on 2026-11-24); the user
  buys those 2 and the third comes from a restock or the sourcing order (par-14 watches it).
- **PA.** The QPA9501 supply current at 25.5 dBm and its power at the band edges are not in its
  datasheet; TX is 0.7 to 1.7 dB short of 25 dBm (`docs/board-changes.md`, open findings).
- **1-RX start-up and power-down (rx1-05)**, covering R992, R993, R996 and the AD9237 pins, is planned;
  the bring-up scope capture is lay-03.
- **1-RX baluns (HHM1907B1).** No simulation covers them: amplitude balance 2.5 dB against 2 dB, no
  S-parameter file on record.
- **U12 land pattern.** The YAT-3A+ pattern is 2.70 mm along the path against about 2.56 mm between R11 and
  C300, so the user nudges one part by about 0.2 mm.
- **Through-hole parts.** JLC placement of CON2 and J2 is to be confirmed in the order tool.
- **12 V decoupling.** The 10 uF 25 V X5R 0805 capacitors on 12 V lose about 80 % of their capacitance at
  bias (`docs/board-changes.md`, open findings); a part choice for the user.
- **Records out of date.** `docs/board-changes.md` and `parts/decisions.csv` still show several par-03
  choices as proposed or for-user although the accept note decided them; the par-03 choices have no row
  in `docs/board-changes.md` yet. PL133-37TI-R has no LCSC or DigiKey number in `parts/final_parts.csv`.

Records that name an analysis as planned or not run:

{{fact:t_open_analyses}}

## 4.1 Substitutions with no fallback on record

The records name no fallback for these {{fact:no_fallback_n}} lines. Anything missing goes back to the
user; the agent did not pick one. For the 1-RX a fallback must be in JLC stock (no consignment): the
record's only other U6 and U26/U27 parts are consign-only. Where the record does name one (for
example U45 on the 1-RX: rx1-opamp options C and A) it is in the entry.

{{fact:t_no_fallback}}
