# sim-03: PLL loop, chirp linearity and PLL spurs
Status: proposed
Goal: sim-spurs
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_pll.py -q && ./run tools/build_report.py analysis/09_pll --check
Hardware: none

## Goal
A model of the ADF4158 loop as built: loop bandwidth, phase margin, settling and chirp
linearity, phase noise, and the reference and fractional spur locations across the chirp. It
holds when the report gives these for the target set's chirp and compares them with limits.

## Steps
1. Extract the loop from the schematic: loop-filter components, the VTUNE drive stage (U7 and
   the 10 V supply), VCO gain from the HMC431 datasheet, charge-pump current and PFD frequency
   from the firmware register settings (fnd-01 survey: 40 MHz). If rf-01 finds that above the
   ADF4158 maximum, model both 40 MHz and the corrected PFD.
2. [heavy] `analysis/09_pll/pll_model.py`: linear loop model (open and closed loop, phase
   margin), time-domain response to the frequency ramp (linearity error and settling after
   flyback), phase-noise budget (reference, PFD/charge pump, VCO, filter resistors), and
   integer-boundary and fractional spur frequencies as the chirp sweeps. Tested against a
   textbook third-order loop example. Heavy because: an active loop filter with a ramp input
   and a noise budget is a numerical model that has to be derived and validated, not looked up.
3. If fnd-05 found a route to ADIsimPLL on Linux, give the user a checklist to cross-check loop
   bandwidth and phase margin there and record the comparison.
4. Report and deck: loop plots, linearity error versus the range-resolution target, the spur map
   over the chirp band, phase noise at the IF offsets of interest.

## Acceptance
- Every loop component value cites its refdes and the schematic; register-derived values cite the firmware file.
- The model's test case and its reference result are named.
- Chirp linearity error is stated in Hz and as an effect on range resolution for the target set.
- The deck has no more than 20 slides.

## Review
- Open `reports/09_pll.pptx`: the assumptions slide (chirp settings), phase margin, and the spur map.

## Out of scope
- Changing the loop filter. Bench measurement.

## Allowed commands
- `./run *`

## Log
