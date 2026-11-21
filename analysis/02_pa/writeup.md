---
title: "U14 power amplifier: replacing the discontinued TQP5525"
---

# 1. Question

Qorvo has discontinued the TQP5525 used as U14 (sheet tx), the user's report of 2026-11-21 in
`parts/decisions.csv`. Which replacement meets the board's own requirements, and what would each
one cost the board in changes? The choice is the user's.

# 2. Inputs and assumptions

{{targets}}

- Band and TX power are the `default` target set values (both `set`): {{fact:fmin}} to
  {{fact:fmax}} GHz and {{fact:pout}} dBm at the antenna. Boards: {{fact:boards}} (assumed).
- U14's connections are read headless from the schematic netlist (`kicad-cli`, sheet tx); nothing
  under `kicad/` was changed. The drive level, the output loss and the supply are in the table below.
- Every candidate number cites a datasheet manifest id and page (`datasheets/manifest.yaml`; page
  numbers equal PDF pages), the JLC parts database or the DigiKey API, both read on 2026-11-21.
  Stock and price move: recheck before ordering.
- The 0.5 dB loss from U14 to the SMA is an assumption (a printed coupler has no datasheet; its
  ideal through loss is 0.14 dB). PAT1220 is rated only DC to 3 GHz, so the drive at 5.8 GHz is
  an estimate.
- All five options now have a datasheet on file, including the QPA9501 (Rev J) with its measured
  s2p file and the AWL9924 (Rev 2.1); a candidate without a datasheet would not be scored from
  memory. Options are ranked JLC-stocked first (the parts goal rule, 2026-11-21: JLCPCB buys and
  places them, consigning from DigiKey delays the build).

{{table:requirements.csv}}

# 3. Method

The candidates came from the DigiKey Product Information API (RF amplifiers, status Active,
supply range including 5 V or the one 3.3 V part, band reaching 5.6 to 5.9 GHz, P1dB at least
30 dBm) and the JLC parts database. Each datasheet went through the sources pipeline (par-06) and
was read from the file. The "buy the remaining TQP5525" option is always included.

FMCW is a constant-envelope signal, so P1dB and Psat at 5.8 GHz are the comparison, not the WLAN
EVM power in the datasheets. Required output is 25 dBm plus 0.5 dB of loss, 25.5 dBm; drive is
about -7.2 dBm typical, so the gain needed is about 32.7 dB. Dissipation is the supply voltage
(5.0 V) times current, minus 0.355 W of RF output. A candidate "fits the supply" when its current
at about 26 dBm out is within the 2 A LD39200 and the 1 A ferrite FB4 in the U14 branch (rating
derated at temperature).

# 4. Findings

## Comparison

{{table:comparison.csv}}

![Comparison](build/comparison.png)

Ranking: JLC-stocked options first (1 QPA9501, 2 TQP5525, 3 SE5004L-R), then DigiKey-only options
(4 SE5023L-R, 5 AWL9924). Within a group the order is the agent's, by lifecycle and fit. A JLC-stocked
part that fits exists (QPA9501, TQP5525), so no consignment from DigiKey is needed; the DigiKey-only
parts are listed for completeness and would need board changes anyway.

Five findings:

1. QPA9501 against the TQP5525 (qorvo-qpa9501-datasheet, Rev J, 2020). (a) Band: operational
   range 4900-5900 MHz (p1, p2), so 5.90 GHz is its top edge. Gain is stated at 5800 MHz only
   (29.5 / 32 / 36 dB, p2) and P1dB at 5800 MHz is +29.5 min / +33 typ dBm (p2); the datasheet
   gives nothing at 5.60 or 5.90 GHz and Psat is not given. The measured s2p (a 2015 Agilent
   E5071C sweep, bias and temperature not stated) reads |S21| 30.9 to 31.3 dB over 5.60-5.90 GHz
   (30.9 dB at 5.8 GHz), about 1 dB under the datasheet typ and inside its 29.5-36 dB window; it
   shows the shape, not a guarantee. (b) Pins: 2, 3, 4, 5, 7, 9, 10, 11-20 are the TQP5525's
   functions and match the board's U14 nets; pin 1 is NC and "can be grounded or N/C" (p6), so
   the board's GND on pin 1 is allowed. Body 4.0 x 4.0 mm, 0.50 mm pitch, 0.25 mm leads, 2.50 mm
   paddle (p7) equal the U14 footprint, read headless from `kicad/fmcw3.kicad_pcb`
   (QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias: 0.825 x 0.25 pads, 2.5 x 2.5 paddle with 9
   vias). The datasheet's via pattern (0.25 mm finished holes) is different from the board's 9
   vias; that is a layout detail for the user. Enable (1.8 V high, 0.45 V low, p2) and the eval
   board's R4 27.4 k, R7 27 ohm, R5/R6 2 ohm (p4) equal the board's R304, R302, R305. (c)
   Lifecycle: DigiKey Active with stock 12947 (API, 2026-11-21); the datasheet states none and
   Qorvo's own status is not on file, so beyond DigiKey it is unknown.
2. Only the TQP5525 and QPA9501 are specified up to 5.90 GHz; the QPA9501 only at 5.8 GHz for
   gain and P1dB. The Skyworks parts stop at 5.85 GHz and their figures are at 5.4 GHz. The
   AWL9924 states gain at 5.5-5.85 GHz only.
3. Every viable part has about 32 dB typical gain, so the output stays near 24.8 dBm out of the PA
   (about 24.3 dBm at the SMA), 0.7 dB under the 25 dBm target. This shortfall is already in the
   original design; it is not caused by the replacement. The AWL9924 (29 dB typ at 5.5-5.85 GHz,
   P1dB 25 min / 27 typ dBm) would be 3.7 dB short.
4. The SE5004L and SE5023L share the TQP5525 footprint but not its enable: pin 5 is an analog 2.85 V
   reference, which U30 pin T2 cannot drive. The SE5023L also has pin 1 as VREF where the board
   has GND, and neither datasheet gives a thermal resistance. The AWL9924 is a 3.3 V part (4.5 V
   abs max) in a 24-pin package: it needs a different rail and a new footprint.
5. The current limit is ferrite FB4 (1 A), not the 2 A regulator. The QPA9501 datasheet gives
   Icc 520 mA typ / 650 mA max at 22 dBm average only, not at 25.5 dBm, so the FB4 margin at the
   target power is open; the SE5023L has no maximum current, so its check cannot be closed.

## Remaining TQP5525 stock

JLC lists C471153 with stock 100 (Extended part); DigiKey does not list it. {{fact:boards}} boards
need {{fact:boards}} parts. It is discontinued, so the stock is a finite pool.

![TQP5525](build/cand_O0.png)

## Candidates

{{fact:n_cands}} candidates were shortlisted. Each figure has its datasheet id and page.

![QPA9501](build/cand_C1.png)

![QPA9501 gain](build/qpa9501_s21.png)

![SE5004L-R](build/cand_C2.png)

![SE5023L-R](build/cand_C3.png)

![AWL9924](build/cand_C4.png)

## Considered and not shortlisted

{{fact:not_shortlisted}}

# 5. Open decisions for the user

1. The U14 part. Recommendation (labelled as such, the decision is yours): for this
   {{fact:boards}}-board build, order the QPA9501TR13 through JLC (C2911573, stock 20, so
   {{fact:boards}} boards are covered). It is active at DigiKey, specified to 5.9 GHz, and
   matches the TQP5525's pinout, footprint, 1.8 V enable and detector network, so sheet tx and
   the layout need no change. Fallback: the remaining TQP5525 from JLC (C471153, stock 100),
   a known part that is discontinued. Check first: the QPA9501 datasheet gives no current at
   25.5 dBm (Icc 650 mA max at 22 dBm) and no gain or P1dB at 5.60 or 5.90 GHz, so the FB4 (1 A)
   margin and the band edges have no datasheet number behind them. The
   SE5004L-R is JLC-stocked too but needs an enable change and stops at 5.85 GHz.
2. Whether the 0.7 dB gain shortfall matters. Any replacement with the same gain keeps it; a
   higher-gain part, or a driver, would be a different change.
3. Any change a choice needs is yours to make on sheet tx (U14, FB4, the enable from U30 pin T2).
   After your choice, the agent writes the new part into `parts/decisions.csv` for par-04. When the
   project is open in KiCad, `tools/kicad_ipc.py show --refs U14` selects the part.
