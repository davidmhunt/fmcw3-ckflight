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

## Log
