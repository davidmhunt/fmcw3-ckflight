# sim-01: Supply noise from the bucks to the VCO and its spur level
Status: proposed
Goal: sim-spurs
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_supply_noise.py -q && ./run tools/build_report.py analysis/07_supply_noise --check
Hardware: none

## Goal
The ripple that reaches the HMC431 VCO supply (and the PLL and IF amp supplies), and the FM spur
level it causes, compared with a limit set beforehand. It holds when the report states the limit,
the simulated ripple and spur level, and pass or fail.

## Steps
1. Write the limit first, in `analysis/07_supply_noise/limits.yaml`: tolerable spur level in dBc
   from the target set, converted to ripple at VCO VCC using the HMC431 pushing figure.
2. Netlist the 3V0 branch from the schematic: buck output ripple source (amplitude and
   frequency from the LMR51420 datasheet and sim-02 when available), LP5907 modelled by its PSRR
   and output impedance curves, ferrite beads from vendor models, capacitors with ESR and ESL.
   Same for 3V3A (PLL, IF amp) and 5V (mixer, PA).
3. Run AC and transient simulations with the tool chosen in fnd-05, scripted from
   `analysis/07_supply_noise/`; check for bead-capacitor resonance peaks; sweep capacitor
   tolerance and bead model spread. Tests check the netlists against hand-calculated corner
   frequencies.
4. Convert ripple to FM sideband level (review plan formula) and compare with the limit.
5. Report and deck, with the caveat that layout parasitics are not modelled and the bench
   measurement that would confirm it.

## Acceptance
- The limit is stated before the results and is derived from a datasheet figure with its page.
- Every model (LDO PSRR, bead, capacitor ESR/ESL) cites its source.
- Each of the three rails has a transfer-function plot and a pass or fail.
- The deck has no more than 20 slides.

## Review
- Open `reports/07_supply_noise.pptx`: the limit slide, the result per rail, any resonance peak.

## Out of scope
- Digital rails. Layout parasitic extraction. Design changes.

## Allowed commands
- `./run *`

## Log
