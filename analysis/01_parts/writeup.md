---
title: "FMCW3 parts: exact part numbers and open choices"
---

# 1. Question

Does every BOM line of the FMCW3 board have an exact, orderable part number; which lines can
JLCPCB assemble, which must be consigned from DigiKey or soldered by hand; and which choices are
left for the user?

# 2. Inputs and assumptions

{{targets}}

- BOM: `parts/out/bom.csv` and `parts/out/availability.csv`, written by `parts/bom.py` from the
  schematic with `kicad-cli`, for {{fact:boards}} boards (the target `board_quantity`), no spares.
- Part numbers and the datasheet page behind each suffix: `parts/decisions.csv`
  (datasheets in `datasheets/manifest.yaml`).
- Stock and price: the JLCPCB parts database and the DigiKey API, queried 2026-11-21. Stock and
  price move; rerun `parts/bom.py` before ordering.
- Nothing here is decided: every recommendation is labelled and the decisions are the user's.

# 3. Method

`figures.py` reads `parts/out/` and `parts/decisions.csv`, and writes every chart and table below
into `build/`. The option tables of the nine choices are read from `parts/choices.json` (the
step-2 findings, JLC and DigiKey queried the same day; alternatives that the BOM does not list),
and the schematic's own part in each is read from `availability.csv`. `figures.py` stops if a
user-choice row of `decisions.csv` has no choice.
Cost sums unit price times parts needed per line, from the source that stocks the full quantity.
It leaves out the JLC Extended-part fee ({{fact:n_extended}} Extended lines are priced from JLC),
assembly and PCB cost.

# 4. Findings

## Status

The BOM has {{fact:lines}} lines. {{fact:n_assemble}} can be assembled by JLCPCB, {{fact:n_consign}}
are consigned from DigiKey, {{fact:n_hand}} are marked hand-solder and {{fact:n_unresolved}} are
unresolved. Decision rows: {{fact:n_proposed}} refs have a proposed part number,
{{fact:n_user_choice}} are user choices and {{fact:n_for_user}} are for the user to obtain.

![Status summary](build/status_summary.png)

{{table:routes.csv}}

Through-hole parts (CON2, J2) show as unresolved only because they have no part number yet; they
are expected to be hand-soldered. {{fact:n_passive_refs}} generic passive refs have a proposed
MPN with tolerance, voltage and dielectric (C0G for RF and filter capacitors, JLC Basic preferred);
{{fact:n_suffix_rows}} refs carry a datasheet id and page for the suffix decision.

## Suffix decisions: datasheet and page

{{table:suffix_decisions.csv}}

## Every BOM line

Each placed line appears once with its MPN, DigiKey status and JLCPCB status.

{{fact:bom_table}}

## Obsolete or risky parts

{{table:risky.csv}}

## Cost for {{fact:boards}} boards, both sources

{{table:cost.csv}}

The cheapest source per line comes to USD {{fact:cost_mix}} for {{fact:boards}} boards
(USD {{fact:cost_mix_per_board}} per board). {{fact:n_uncovered}} lines are not priced by either
source today. The U30 line is priced as the schematic's C-grade 100T (choice 1 changes it).

# 5. Choices for the user

Each choice lists its options and a recommendation labelled as such. When the project is open in
KiCad, `tools/kicad_ipc.py show --refs REFS` selects the parts of a choice
(U30; U8; J1; L5,L6,L7; U8,U21,U26,U27,U28,U45,P1,P2,U15,CON2,J2; U6; U17,U18,U19; Y2).

![Choice 1](build/choice_fpga.png)

![Choice 2](build/choice_adc.png)

![Choice 3](build/choice_usbc.png)

![Choice 4](build/choice_inductor.png)

![Choice 5](build/choice_assembly.png)

![Choice 6](build/choice_library.png)

![Choice 7](build/choice_tgrade.png)

![Choice 8](build/choice_lmr.png)

![Choice 9](build/choice_y2.png)

## For the user to obtain

Nothing in this list is guessed; each is missing a datasheet or a part number.

{{table:obtain.csv}}

# 6. Open decisions for the user

1. FPGA U30 (XC7A35T or XC7A100T, C or I grade). Recommendation: 100T I grade via JLC if the
   headroom is wanted, else 35T I grade.
2. ADC U8 grade. Recommendation: I grade from DigiKey.
3. USB-C J1 variant. Recommendation: USB4105-GF-A after you confirm the variants.
4. Inductor L5-L7. Recommendation: do not order the SRR6040A-330M; a 33 uH part with Isat above
   5.1 A if the board allows, else a lower value.
5. Parts JLCPCB cannot assemble. Recommendation: consign the ICs and SMA connectors, hand-solder
   CON2 and J2.
6. `kicad/libs/fmcw3.lib`. Recommendation: prune later, never delete.
7. Clock buffer U6 grade. Recommendation: PL133-37TC-R, the one JLC stocks; the grade is yours.
8. Buck U17-U19 variant. Recommendation: LMR51420YFDDCR (1.1 MHz, fixed frequency).
9. Oscillator Y2 package. Recommendation: a 2.5x2.0 mm ECS part if its datasheet shows 40 MHz
   clipped sine, since the schematic's 3.2x2.5 mm part changes the layout.
