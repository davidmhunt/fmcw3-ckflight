# fnd-05: Choose and smoke-test Linux tools for the simulation and RF analyses
Status: approved
Goal: foundation
Node: any
Deliverable: doc
Accept: user
Verify: test -s docs/analysis-tools.md && grep -q '^## Verdict' docs/analysis-tools.md && grep -q '^## Tools the user must obtain' docs/analysis-tools.md && ./run uv run pytest tests/test_sim_smoke.py -q
Hardware: none

## Goal
A tested answer to "which tools, runnable on Linux, replace LTspice, TI WEBENCH, ADIsimPLL and
an EM solver for this review". It holds when `docs/analysis-tools.md` gives a verdict per
analysis backed by a smoke test that was actually run, and lists anything the user must obtain.

## Steps
1. For each need in review-plan Phases 2, 3, 6 and 7, list candidates and how each would run
   (native package, Docker image, Wine, web browser):
   SPICE (ngspice, KiCad's built-in simulator, Qucs-S, LTspice under Wine);
   vendor models (ADI LT6232 and LD3920/LP5907 models in ngspice, TI LMR51420 PSpice model in
   ngspice's PSpice-compatibility mode, ferrite-bead vendor models);
   buck design (TI WEBENCH in a browser, hand calculation from the datasheet equations);
   PLL (ADIsimPLL under Wine, open Python PLL loop-filter and phase-noise models);
   RF cascade and S-parameters (scikit-rf); transmission lines (KiCad calculator, a Python
   script, openEMS for the SMA launch and LO via).
2. Smoke-test each candidate that can run unattended, in a container built from
   `docker/Dockerfile.sim` (kept separate from `fmcw3-tools`): an RC low-pass AC sweep in
   ngspice checked against the formula; one vendor op-amp model loading and running; a scikit-rf
   two-stage cascade checked by hand; an openEMS microstrip line returning about 50 ohm; LTspice
   or ADIsimPLL under Wine starting in batch mode if it can be installed without a GUI. Record
   pass, fail or not attempted, with the error text. Keep the passing cases as
   `tests/test_sim_smoke.py` (skipped with a reason when the sim image is absent).
3. Write `docs/analysis-tools.md`: a table per need (tool, replaces, how it runs, licence, smoke
   result, limits), `## Verdict` (the tool chosen for each later directive in `sim-spurs` and
   `rf-review`), and `## Tools the user must obtain` (anything GUI-only, licensed or
   registration-walled, with the link and what it is needed for).
4. Propose amendments to the `sim-spurs` and `rf-review` directives that follow from the
   verdict, as a list at the end of the doc. Do not edit those directives here.

## Acceptance
- Every tool named in review-plan Phases 3 and 6 (LTspice, TI WEBENCH, TI PSpice model,
  ADIsimPLL, KiCad calculator, openEMS, scikit-rf) has a row with a Linux route or "no route".
- Each "pass" in the table corresponds to a test in `tests/test_sim_smoke.py` or a logged command
  and output in the doc.
- `## Verdict` names exactly one primary tool per analysis and says why.
- `## Tools the user must obtain` is present, even if it says none.

## Review
- Open `docs/analysis-tools.md`, `## Verdict` and `## Tools the user must obtain`: do you accept
  the tool choices, and is anything listed that you cannot or do not want to install.

## Out of scope
- Running the actual board simulations (goal `sim-spurs`).
- Windows virtual machines.

## Allowed commands
- `docker build -t fmcw3-sim* *`
- `./run *`

## Log
