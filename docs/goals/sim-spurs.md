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
1. sim-05: PSpice for TI under Wine, for TI-encrypted models such as the LMR51420 (moved from
   fnd-08 on 2026-11-20 while TI access is pending; may run earlier if the installer arrives)
2. sim-01: Supply noise from the bucks to the VCO and its spur level
3. sim-02: Buck converter with the replacement inductor, and the IF filter response
4. sim-03: PLL loop, chirp linearity and PLL spurs
5. sim-04: Frequency plan and spur budget

## Notes
- 2026-11-22: the 1-RX board is ordered (rx1-04, about 2026-11-27) before this goal runs, so its findings feed the 1-RX bring-up and gate the 2-RX order (late December).
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
- Two boards (2026-11-22): `kicad/` is the 2-RX board (LTC2292, two receive chains) and `kicad-1rx/` the 1-RX board (AD9237, receive chain 2 not fitted, JLC-stock-only substitutes; its changes are in `parts/rx1_changes.csv`). Analyse a circuit once on `kicad/` and state that it covers both when `parts/rx1_changes.csv` does not touch it; otherwise analyse it per board (`--project kicad-1rx`) and report the two side by side. Findings say which board they apply to.

## Log
