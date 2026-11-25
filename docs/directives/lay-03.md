# lay-03: Testability review and bring-up procedure
Status: proposed
Goal: layout-review
Node: any
Deliverable: slides
Accept: user
Verify: test -s docs/bring-up.md && ./run tools/build_report.py analysis/06_testability --check
Hardware: none

## Goal
A decided view of how each stage of the board will be tested when it arrives: what access
exists, what to add before ordering, and a step-by-step bring-up procedure with pass limits. It
holds when the report lists every rail and stage with its access point and `docs/bring-up.md`
gives an expected value for every step.

## Steps
1. From the netlist and board, list existing access: jumpers JP1-JP12, header J2, SMAs, LEDs,
   and any pad usable as a probe point on each rail, MUXOUT and VTUNE. Verify the review plan's
   table rather than copying it.
2. Gaps: per rail and per RF stage, say how it would be measured today and what is missing.
   Propose additions (rail test pads or 0 ohm links, u.FL or rotatable 0402 taps on LO and PA
   output, MUXOUT and VTUNE pads) with board location candidates and the cost of each in area
   and RF risk.
3. `docs/bring-up.md`: ordered steps, each with equipment, where to probe, expected value and
   tolerance (from the power budget of lay-02 and the level plan of rf-01), and what to do on
   failure. Include the equipment list with the frequency range each item needs.
4. Report and deck: access map on a board image, gap list with a recommendation per item,
   bring-up flow, equipment list.

## Acceptance
- Every regulator output rail and every RF stage has a row: existing access, gap, proposal.
- Each bring-up step has an expected value with a source (datasheet, level plan or power budget).
- Each proposed addition names a net and a candidate board location.
- The deck has no more than 20 slides.

## Review
- Open `reports/06_testability.pptx`: decide add or skip for each proposed test point.
- Read `docs/bring-up.md` against the equipment you actually have.

## Out of scope
- Adding test points to the design.
- Any bench measurement (no board exists yet).

## Rules
- Write the bring-up procedure in two variants, 1-RX (one channel, AD9237 straps, receive chain 2 not fitted) and 2-RX, sharing the common steps; test points cover both. (amended 2026-11-22 for the two-board plan)
- 1-RX bring-up checks the receive gain early: a known-level 5.8 GHz tone into RF1 against the expected IF amplitude, because the TDK balun at U26 and U27 is not simulated. (amended 2026-11-23)

- 1-RX bring-up measures the rail order at the first power-on, before the ADC is used: 3V8, 3V0, 3V3A, 1V8 and 3V3D together, and the AD9237 VIN+, CLK and PDWN, triggered on 3V8; pass when 3V3A, 1V8 and 3V3D start only after 3V0 and no ADC pin goes above 3V0 + 0.3 V; compare with the rx1-05 waveforms and give the probe point for each signal. Repeat for power-off. (amended 2026-11-25, the user's choice in the rx1-02 review)

## Allowed commands
- `./run *`

## Log
