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
- Candidates without a datasheet on file are not scored from memory: {{fact:obtain_names}} are
  marked "for the user to obtain".

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

Four findings:

1. Only the TQP5525 is specified over the whole 5.60 to 5.90 GHz band. The Skyworks parts stop at
   5.85 GHz, and their figures are at 5.4 GHz, not 5.8 GHz.
2. Every scored part has about 32 dB typical gain, so the output stays near 24.8 dBm out of the PA
   (about 24.3 dBm at the SMA), 0.7 dB under the 25 dBm target. This shortfall is already in the
   original design; it is not caused by the replacement.
3. The SE5004L and SE5023L share the TQP5525 footprint but not its enable: pin 5 is an analog 2.85 V
   reference, which U30 pin T2 cannot drive. The SE5023L also has pin 1 as VREF where the board
   has GND, and neither datasheet gives a thermal resistance.
4. The current limit is ferrite FB4 (1 A), not the 2 A regulator. The SE5023L has no maximum
   current in its datasheet, so that check cannot be closed.

## Remaining TQP5525 stock

JLC lists C471153 with stock 100 (Extended part); DigiKey does not list it. {{fact:boards}} boards
need {{fact:boards}} parts. It is discontinued, so the stock is a finite pool.

![TQP5525](build/cand_O0.png)

## Candidates

{{fact:n_cands}} candidates were shortlisted. Each figure has its datasheet id and page.

![QPA9501](build/cand_C1.png)

![SE5004L-R](build/cand_C2.png)

![SE5023L-R](build/cand_C3.png)

![AWL9924](build/cand_C4.png)

## Considered and not shortlisted

{{fact:not_shortlisted}}

# 5. Open decisions for the user

1. The U14 part. Recommendation (labelled as such, the decision is yours): for this
   {{fact:boards}}-board build, buy the remaining TQP5525 from JLC (stock 100), since it is the only
   option that covers the whole band by datasheet and needs no change to sheet tx or the layout.
   Before any respin, obtain the QPA9501 datasheet (same maker, band and, per JLC, package),
   compare it in this report, and keep the SE5004L-R as the fallback if its enable and the
   5.85 GHz band limit are acceptable.
2. The datasheets to fetch: QPA9501 (`qorvo-qpa9501-datasheet`) and AWL9924
   (`anadigics-awl9924-datasheet`), listed in `docs/user-fetch.md`.
3. Whether the 0.7 dB gain shortfall matters. Any replacement with the same gain keeps it; a
   higher-gain part, or a driver, would be a different change.
4. Any change a choice needs is yours to make on sheet tx (U14, FB4, the enable from U30 pin T2).
   After your choice, the agent writes the new part into `parts/decisions.csv` for par-04. When the
   project is open in KiCad, `tools/kicad_ipc.py show --refs U14` selects the part.
