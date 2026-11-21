# sim-05: PSpice for TI under Wine, for TI-encrypted models such as the LMR51420
Status: proposed
Goal: sim-spurs
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests -q && ./run tools/fetch_sources.py --check && friday result check sim-05 --require 'install_tried == 1'
Hardware: none

## Goal
TI's encrypted models, such as the LMR51420 buck (U17-U19), get a route on this machine through
PSpice for TI under Wine, if TI's installer allows it. sim-02 then knows which buck route it
uses. It holds when the trial is recorded as pass or fail, with the error text, and the docs name
the route sim-02 takes. (Moved out of fnd-08 on 2026-11-20 at the user's request while TI account
access is pending. If the installer arrives earlier, this may run earlier.)

## Steps
1. The installer needs a TI account, so it is user-fetch. The user downloads it once from
   https://www.ti.com/tool/PSPICE-FOR-TI (the full Windows installer, not the web stub) and saves
   it at the `ti-pspice-for-ti-installer` path in `software/manifest.yaml`
   (`software/files/ti/pspice-for-ti-installer.zip`). If TI gives an `.exe`, change the entry's
   `file` to its real name. Pin the hash with `./run tools/fetch_sources.py --record`.
2. Install it unattended under xvfb in `fmcw3-sim`, as a separate build stage in
   `docker/Dockerfile.sim` that is skipped when the installer is absent, so the image still
   builds on a fresh clone. Never commit the installer.
3. Check for a batch mode (for example `psp_cmd`).
4. Smoke-test the encrypted LMR51420 model (`slum825`, from `datasheets/manifest.yaml`) in a
   transient run, as a test that is skipped when PSpice is not installed.
5. Record the result with `friday result write sim-05 --metric install_tried=1` plus
   `install`, `batch` and `model_runs` (each 0 or 1) and a `--note` with any error text. If
   there is no batch mode but the GUI works, PSpice is a GUI tool for the user through
   `./run --sim-gui`, with a checklist in `docs/gui-tool-checklists.md`.
6. Update `docs/analysis-tools.md` (PSpice for TI rows and the sim-02 buck route: PSpice if its
   model runs, otherwise the hand-built averaged model plus the user's WEBENCH check) and
   `MANUAL.md` (sections 5 and 6, and the `--sim-gui` route if PSpice is GUI-only).

## Acceptance
- The trial result (install, batch, model runs) is recorded with its error text.
- A fresh clone without the installer still builds `fmcw3-sim` and passes the tests.
- `docs/analysis-tools.md` and `MANUAL.md` name the buck route sim-02 will use.

## Rules
- Never commit an installer, or a model whose licence forbids it.
- Never open X11 access to anyone but your own user; revoke it when the command exits.

## Review
- Read the PSpice for TI rows in `docs/analysis-tools.md` and `MANUAL.md`.
- If PSpice installed, open it with `./run --sim-gui` and look at the LMR51420 smoke run.

## Out of scope
- Running the actual buck analysis (sim-02).
- A Windows virtual machine.

## Allowed commands
- `./run *`
- `docker build -t fmcw3-sim* *`
- `friday result write sim-05 *`

## Log
