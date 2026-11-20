# fnd-08: LTspice GUI from the sim container, and PSpice for TI under Wine
Status: blocked: step 2: Did the LTspice window open and did the plot work on your screen (the MIT-SHM error may have broken rendering)? If not, I recommend a step 1 fix: add '--ipc=host' (or disable MIT-SHM) to the --sim-gui docker command and its test, then re-run. If it did work, tell me and I will write 'friday result write fnd-08 --metric sim_gui_shown=1' (otherwise =0).
Goal: foundation
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests -q && ./run --sim python3 -m pytest tests/test_sim_smoke.py -q && friday result check fnd-08 --require 'sim_gui_shown == 1' --files
Hardware: none

## Goal
You can open the container's LTspice (and the other Wine GUI tools in `fmcw3-sim`) on your own
desktop. TI's encrypted models, such as the LMR51420 buck, get a route on this machine through
PSpice for TI under Wine, if TI's installer allows it. It holds when you have seen LTspice open
from `./run --sim-gui` and the PSpice trial is recorded as pass or fail with its error text.

## Steps
1. `./run --sim-gui <cmd>` runs a command in `fmcw3-sim` with an X11 display on your desktop.
   The session is X11 (`DISPLAY=:1`). The command:
   - mounts `/tmp/.X11-unix` and passes `DISPLAY`;
   - grants access only to your own user (`xhost +SI:localuser:<user>`, revoked when the
     command exits), never `xhost +`;
   - runs as your uid, like `./run`.

   Add `./run --sim-gui ltspice [file]` as a shortcut that starts LTspice under Wine, opening an
   `.asc` or `.net` file from the repo if one is given. `--print` shows the docker command
   without running it. `tests/test_run_sim_gui.py` checks that docker command. Document it in
   `docs/setup.md` and `docs/analysis-tools.md`.
2. Live check with you. Run `./run --sim-gui ltspice tests/sim/` on an existing smoke-test
   netlist, ask you to confirm that the LTspice window opened and the plot works, then run
   `friday result write fnd-08 --metric sim_gui_shown=<0|1>`.
3. PSpice for TI under Wine. List its installer in `datasheets/manifest.yaml`. It probably
   needs a TI account, so it is likely user-fetch: you download it once, and the pipeline
   checks its hash. Then:
   - install it unattended under xvfb in `fmcw3-sim`, as a separate build stage, never
     committing the installer;
   - check for a batch mode (for example `psp_cmd`);
   - smoke-test the encrypted LMR51420 model (`slum825`) in a transient run.

   Record the result: install yes or no, batch yes or no, model runs yes or no, with the error
   text, as metrics on the same `friday result write`. If there is no batch mode but the GUI
   works, it is a GUI tool for you through `--sim-gui`, with a checklist in
   `docs/gui-tool-checklists.md`.
4. Resolve "LD3920" (U25). Read U25's value and fields from the schematic export and find the
   real manufacturer and part number. Its datasheet may help; it is likely not TI. Add its
   datasheet, and its model if one exists, to the manifests.
5. Update `docs/analysis-tools.md` with Edit: the `--sim-gui` route, the PSpice for TI rows,
   U25's identity, and the sim-02 buck route. Use PSpice if its model runs; otherwise keep the
   hand-built averaged model plus your WEBENCH check.

## Rules
- Never commit an installer, or a model whose licence forbids it.
- Never open X11 access to anyone but your own user; revoke it when the command exits.

## Review
- Run `./run --sim-gui ltspice` yourself and open one of the smoke-test circuits.
- Read the PSpice for TI and U25 rows in `docs/analysis-tools.md`.

## Out of scope
- Running the actual buck analysis (goal `sim-spurs`, sim-02).
- A Windows virtual machine.

## Allowed commands
- `./run *`
- `docker build -t fmcw3-sim* *`
- `friday result write fnd-08 *`

## Log

### 2026-11-20
Commits:
- 2e62903 fnd-08: ./run --sim-gui and ltspice shortcut (X11, own-user xhost, revoked on exit)
Notes:
- step 2: ran ./run --sim-gui ltspice tests/sim/rc_lowpass.cir; xhost grant and revoke worked; the run ended with X Error BadValue (MIT-SHM, X_ShmPutImage, opcode 130/3), exit code 0.
- likely cause: MIT-SHM across the container boundary (no --ipc=host); candidate fixes: add --ipc=host to the --sim-gui docker command, or disable shm. Not applied (step 1 code).
- sim_gui_shown not written: no user confirmation that the window opened and the plot works.
Verify: not run
Independent review: not recorded
Blocked: step 2: Did the LTspice window open and did the plot work on your screen (the MIT-SHM error may have broken rendering)? If not, I recommend a step 1 fix: add '--ipc=host' (or disable MIT-SHM) to the --sim-gui docker command and its test, then re-run. If it did work, tell me and I will write 'friday result write fnd-08 --metric sim_gui_shown=1' (otherwise =0).
