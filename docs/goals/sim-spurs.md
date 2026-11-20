# sim-spurs: Supply-noise, IF and PLL simulation and the spur frequency plan
Status: proposed
Base: falcon_development
Land: pr

## Goal
Review-plan Phases 6 and 7. The supply-noise path to the VCO, the buck with its replacement
inductor, the IF filter and the PLL loop are simulated with pass limits written beforehand, and
every clock and spur source is placed on a frequency plan against the IF band. It holds when
each report rebuilds for a target set with one command and states pass or fail against its limit.

## Directives
1. sim-01: Supply noise from the bucks to the VCO and its spur level
2. sim-02: Buck converter with the replacement inductor, and the IF filter response
3. sim-03: PLL loop, chirp linearity and PLL spurs
4. sim-04: Frequency plan and spur budget

## Notes
- Written 2026-11-19 before the tool choice. The tools named here (ngspice, Python models) are
  placeholders until fnd-05's verdict; amend before approval. The user has Linux only.
- sim-02 depends on the inductor chosen in par-03.
- Carry-overs from fnd-01 (`docs/surveys/upstream-survey.md`), to be decided later by the user
  (2026-11-19):
  - IF filter vs the firmware's 2 MSPS per channel and 400 kHz HPF (sim-02).
  - PLL modelled at the firmware's 40 MHz PFD, and the corrected one if rf-01 finds it too high (sim-03).
  - Shared 40 MHz TCXO for FPGA and ADC: jitter vs ADC SNR, harmonics as spurs (sim-04).

## Rules
- Every simulated circuit is committed both as a netlist and as an LTspice schematic (`.asc`),
  so the user can open and probe it with `./run --sim-gui ltspice <file>.asc`. The agent draws
  the first version; the user may tidy or modify it, and scripts edit values through spicelib
  without redrawing. The netlist and the `.asc` must describe the same circuit, checked by a test
  that compares their netlists. (User decision 2026-11-20.)
- Every writeup shows the KiCad schematic sheet the simulated circuit comes from, exported with
  `kicad-cli sch export svg`, next to the simulated circuit, naming the board refdes each model
  part stands for.

## Log
