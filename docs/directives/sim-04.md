# sim-04: Frequency plan and spur budget
Status: proposed
Goal: sim-spurs
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_freq_plan.py -q && ./run tools/build_report.py analysis/10_spurs --check
Hardware: none

## Goal
Every clock and spur source on the board placed on one frequency plan and checked against the
IF band and against offsets from the carrier, for any target set. It holds when the report lists
each source with its frequency, coupling path, predicted location and a risk rating.

## Steps
1. `analysis/10_spurs/sources.yaml`: each source with its frequency taken from a datasheet or
   the firmware and cited: buck switching frequency (fitted LMR51420 variant), reference
   oscillator Y2, PFD frequency, ADC sample rate, FPGA clocks, USB crystal Y1 and the FT2232
   60 MHz clock, PA and VCO harmonics.
2. `freq_plan.py`: IF band from the target set (maximum beat frequency); every harmonic and
   mixing product that lands in the IF band or aliases into it at the ADC; sidebands on the
   carrier at each source frequency. Tests on a small hand-worked plan.
3. Bring in the levels: supply-ripple FM spurs (sim-01), PLL spurs and phase noise (sim-03),
   TX-to-RX leakage and compression (rf-01). Rank each spur: in band or not, estimated level
   where one can be estimated, and what it would look like in the range FFT or a SAR image. Y2 (40 MHz) clocks both the FPGA
   and the ADC: estimate the ADC SNR limit from its jitter at the maximum IF.
4. TX harmonics: there is no filter between the coupler and the TX SMA; state the expected
   harmonic levels from the PA datasheet and what a filter footprint would need. Regulatory
   limits are cited, not interpreted.
5. Report and deck, ending with the bench captures that would confirm each prediction
   (terminated-TX capture, spectrum sweep around the carrier) and the proposed design changes.

## Acceptance
- Every source row cites where its frequency comes from.
- The in-band list rebuilds for a different target set and changes accordingly.
- Each spur with an estimated level names the directive and figure the level comes from.
- Proposed changes are listed separately from findings.
- The deck has no more than 20 slides.

## Review
- Open `reports/10_spurs.pptx`: the frequency-plan chart, the in-band list, and the TX filter slide.

## Out of scope
- Regulatory compliance statements. Design changes. Bench measurement.

## Rules
- Work out the jitter-limited SNR for each board's ADC (LTC2292 and AD9237); the clock plan is shared. (amended 2026-11-22 for the two-board plan)

## Allowed commands
- `./run *`

## Log
