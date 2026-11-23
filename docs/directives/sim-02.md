# sim-02: Buck converter with the replacement inductor, and the IF filter response
Status: proposed
Goal: sim-spurs
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_buck_if.py -q && ./run tools/build_report.py analysis/08_buck_if --check
Hardware: none

## Goal
Two checks on parts of the design that are changing or set the usable range: the LMR51420 bucks
with the replacement 33 uH inductor, and the LT6232 IF amplifier and filter response. It holds
when each has a result against a limit written beforehand.

## Steps
1. Buck (U17-U19): from the datasheet design equations, for each rail's load current (the par-11
   load budget, `reports/12_rail_loads.pdf`; amended 2026-11-23: par-11 replaces the lay-02 budget
   and its ripple and saturation check, so this step reuses it and adds output ripple, stability
   and the model cross-check, for the APS0650M330A the user chose): ripple current, peak current versus the chosen inductor's saturation current, output
   ripple, and the stability conditions the datasheet gives. Cross-check one rail with the TI
   model in PSpice for TI if sim-05 found it runs; otherwise give the user a short
   WEBENCH (browser) checklist and record their result.
2. IF chain: netlist the mixer output to ADC input path (JP9-JP12, U45, JP5-JP8) from the
   schematic; AC response, gain, input-referred noise, and output swing versus the LTC2292 input
   range. Compare the passband with the beat-frequency range and the roll-off with Nyquist for
   the target set, using the firmware's numbers as design intent: 40 MSPS, decimate 20 to 2 MSPS
   per channel, 500 samples per 250 us chirp, 400 kHz HPF (survey: `docs/surveys/upstream-survey.md`).
3. Tests: the equations against the datasheet's worked example; the filter corner against a
   hand calculation.
4. Report and deck.

## Acceptance
- Inductor saturation margin is stated per rail with the load current assumed.
- The IF response plot marks the beat-frequency band and Nyquist for the target set, and rebuilds for another set.
- Any result obtained by the user in a GUI or web tool is labelled as such with the date.
- The deck has no more than 20 slides.

## Review
- Open `reports/08_buck_if.pptx`: the saturation-margin table and the IF response slide.

## Out of scope
- Choosing a different regulator. Design changes.

## Rules
- Compare the IF output swing and bias against each board's ADC input (LTC2292 on 2-RX, AD9237 on 1-RX, reusing rx1-02's model), and run the buck with each board's chosen inductor if they differ. (amended 2026-11-22 for the two-board plan)

## Allowed commands
- `./run *`

## Log
