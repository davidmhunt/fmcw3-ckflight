---
title: "FMCW3 sourcing plan: lines JLCPCB cannot place today"
---

# 1. Question

For every BOM line that JLCPCB cannot assemble today (verdict not "JLC assemble", or JLC stock
below twice the need), which routes get the part onto the board, ranked JLC-first, and what does
each cost for {{fact:boards}} boards, how long does it take, and what work does it cause?

# 2. Inputs and assumptions

{{targets}}

- Stock and price: JLCPCB parts database dated {{fact:jlc_db}}; DigiKey API queried
  {{fact:dk_date}}. Both move; rerun `parts/bom.py` before ordering.
- Need = parts per board times {{fact:boards}} boards, no spares. Costs are parts only: no JLC
  Extended-part setup fee, no shipping, no assembly.
- Datasheets were read through the sources pipeline; each route cites its manifest id and PDF
  page. A row marked "listing only" has no datasheet on file and is not a rating claim.
- Substitutes are classified drop-in (fields only), footprint or layout change (a change for the
  user), or design change (names the analysis: rf-01, sim-01, sim-02, sim-spurs).
- Nothing is decided and no schematic or layout is edited: a chosen substitute reaches the
  schematic only through par-04.

# 3. Method

`figures.py` holds the par-09 findings (runs/par-09/notes.md, steps 1 to 4) as data and computes
each route's cost as unit price times quantity. Routes are ranked JLC-first per line: JLC stock
(the same part), a JLC-stocked substitute, JLC's parts-sourcing service, consignment from
DigiKey, hand soldering. The consignment lead time is the DigiKey lead plus shipping to JLC.

JLC parts-sourcing service (pages `jlcpcb-global-sourcing-howto`,
`jlcpcb-global-sourcing-terms` and `jlcpcb-pcba-parts-sourcing-instruction` in
`docs/references/manifest.yaml`, downloaded 2026-11-21, last updated Sep 09 2026):

- JLCPCB buys the part from a global distributor into the user's parts library, for JLCPCB
  assembly orders only; the parts are not shipped to the user, so the service does not serve
  hand soldering.
- Lead time: {{fact:svc_lead}}; the two pages disagree and both are quoted.
- Fees stated: no shipping; customs duty 3-30 % on some kinds (attenuators are named);
  commodity inspection 20 USD per kind plus a shared 3C fee for connectors; a loose-part fee of
  0.017 USD per pin (at most 0.078 per part) for parts not on tape; baking 8 USD per 48 h if
  advised.
- Not stated on any page: a service fee and the unit price. Both appear only in the logged-in
  Parts Manager, so they are for the user to confirm; the sourcing-service costs below use the
  DigiKey price as a stand-in and say so. Whether JLC lists each MPN is also for the user to
  confirm in the Parts Manager search.

# 4. Findings

## Summary

{{table:summary.csv}}

The routes for every line follow: {{fact:n_lines}} lines, {{fact:n_routes}} routes.

## Routes per line

{{fact:routes_md}}

## ADC U8: scope of a redesign

The LTC2292 pin-compatible family (LTC2290-LTC2299, 64-pin 9x9 QFN) is at JLC stock 0 and has no
rows for LTC2294, 2295 and 2299; no pin-compatible dual ADC is in JLC stock. The JLC-stocked
dual ADCs differ in footprint (VQFN-24, TSSOP-16 or VQFN-64), in the FPGA bank-35 and bank-34
pins (12 parallel data pins, OFA, OFB, OE and SHDN are released; a serial part needs SCLK, CS,
CONVST and one or two data pins; a 1.8 V part needs a 1.8 V bank or level shifters), in the data
interface (a 40 MHz multiplexed parallel bus becomes serial words at 1 to 5 MSPS), and in
firmware (`adc.vhd` and the decimate-by-20 FIR in `davidmhunt/fmcw3-ckflight-fw` change, and the
anti-alias rejection moves to the analogue U45 stage). The analyses it needs are sim-02 (IF
chain and Nyquist), sim-01 (supplies) and sim-spurs (the 40 MHz ADC clock tone leaves the IF
band). That is a new hardware-design directive; it is not proposed here. The ADS7853 was
rejected: 1 MSPS per channel is below the 2 MSPS per channel the design uses.

# 5. Recommendation (labelled as such, the decision is yours)

{{fact:recommendation}}

# 6. Changes recorded

Each proposed substitute is a choice option in `parts/choices.json` and each proposed or
recommended change is a row in `docs/board-changes.md` with status `proposed`. None has a
covering simulation yet; the rows name the analysis each would need.
