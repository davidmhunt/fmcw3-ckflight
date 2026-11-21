# fnd-08: LTspice GUI from the sim container, and PSpice for TI under Wine
Status: awaiting review
Goal: foundation
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests -q && ./run --sim python3 -m pytest tests/test_sim_smoke.py -q && friday result check fnd-08 --require 'sim_gui_shown == 1' --files
Hardware: none

## Goal
You can open the container's LTspice (and the other Wine GUI tools in `fmcw3-sim`) on your own
desktop, tool installers have their own `software/` manifest, and U25 ("LD3920") is identified.
It holds when you have seen LTspice open from `./run --sim-gui`. (Amended 2026-11-20 at the
user's request: the PSpice for TI install and LMR51420 trial moved to sim-05 in goal `sim-spurs`
while TI account access is pending.)

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
3. PSpice for TI under Wine. (Amended 2026-11-20 at the user's request.) First add a top-level
   `software/` folder for downloaded tool installers, separate from datasheets:
   - `software/manifest.yaml` is a third manifest read by `tools/fetch_sources.py`, with the
     same fields and checks;
   - files go under `software/files/`, which is gitignored;
   - `software/README.md` explains where to save a user-fetched installer and how to pin it.

   Move the PSpice for TI entry there from `datasheets/manifest.yaml`. The LTspice installer,
   which the image build downloads, is also listed there for its link and hash. Update
   `tests/test_sources.py`, `.gitignore` and the docs.

   The installer needs a TI account, so it is user-fetch. Its download, the unattended Wine
   install, the batch-mode check and the LMR51420 smoke test moved to sim-05 (goal `sim-spurs`)
   on 2026-11-20, at the user's request, while TI access is pending. This step ends once the
   `software/` folder and its manifest entries are in place.
4. Resolve "LD3920" (U25). Read U25's value and fields from the schematic export and find the
   real manufacturer and part number. Its datasheet may help; it is likely not TI. Add its
   datasheet, and its model if one exists, to the manifests.
5. Update `docs/analysis-tools.md` with Edit: the `--sim-gui` route, U25's identity, and the
   PSpice for TI rows and sim-02 buck route marked as deferred to sim-05. Update the PSpice line
   in `MANUAL.md` section 5 to "deferred to sim-05 (waiting on TI access)".

## Rules
- Never commit an installer, or a model whose licence forbids it.
- Never open X11 access to anyone but your own user; revoke it when the command exits.

## Review
- Run `./run --sim-gui ltspice` yourself and open one of the smoke-test circuits.
- Read the U25 row, and the PSpice for TI rows marked deferred, in `docs/analysis-tools.md`.

## Out of scope
- Running the actual buck analysis (goal `sim-spurs`, sim-02).
- The PSpice for TI install and trial (sim-05).
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

### 2026-11-20
Unblocked: was blocked: step 2: Did the LTspice window open and did the plot work on your screen (the MIT-SHM error may have broken rendering)? If not, I recommend a step 1 fix: add '--ipc=host' (or disable MIT-SHM) to the --sim-gui docker command and its test, then re-run. If it did work, tell me and I will write 'friday result write fnd-08 --metric sim_gui_shown=1' (otherwise =0).

### 2026-11-20
Commits:
- 2e62903 fnd-08: ./run --sim-gui and ltspice shortcut (X11, own-user xhost, revoked on exit)
- 0c9e41a fnd-08: record the live LTspice GUI check (user-confirmed)
- f2dcac0 fnd-08: --sim-gui adds --ipc=host and SIM_GUI_DPI (default 144); LTspice-syntax example net
- b7b74f4 fnd-08: list the PSpice for TI installer in the datasheets manifest (access: login, user-fetch)
Notes:
- step 2: ran ./run --sim-gui ltspice tests/sim/rc_lowpass.cir; xhost grant and revoke worked; the run ended with X Error BadValue (MIT-SHM, X_ShmPutImage, opcode 130/3), exit code 0.
- likely cause: MIT-SHM across the container boundary (no --ipc=host); candidate fixes: add --ipc=host to the --sim-gui docker command, or disable shm. Not applied (step 1 code).
- sim_gui_shown not written: no user confirmation that the window opened and the plot works.
Verify: not run
Independent review: not recorded
Blocked: step 3: Please download the PSpice for TI installer once, signed in to your TI account. Go to https://www.ti.com/tool/PSPICE-FOR-TI, press Download or Get software, and take the full Windows installer (the zip or exe, not the web stub). Save it as /home/david/Documents/pcb_work/fmcw3-ckflight/datasheets/files/ti/pspice-for-ti-installer.zip. If TI gives you an .exe, tell me the real file name and I will change the manifest entry's 'file' to match. Then tell me, and I will run './run python3 tools/fetch_sources.py --record' to pin its hash and continue with step 3: a separate build stage in docker/Dockerfile.sim, the batch-mode check, and the LMR51420 (slum825) transient smoke test. My recommendation is to fetch it. If TI's licence or the installer refuses to run under Wine, I will record install=no with the error text and keep the hand-built averaged buck model for sim-02.

### 2026-11-20
Unblocked: was blocked: step 3: Please download the PSpice for TI installer once, signed in to your TI account. Go to https://www.ti.com/tool/PSPICE-FOR-TI, press Download or Get software, and take the full Windows installer (the zip or exe, not the web stub). Save it as /home/david/Documents/pcb_work/fmcw3-ckflight/datasheets/files/ti/pspice-for-ti-installer.zip. If TI gives you an .exe, tell me the real file name and I will change the manifest entry's 'file' to match. Then tell me, and I will run './run python3 tools/fetch_sources.py --record' to pin its hash and continue with step 3: a separate build stage in docker/Dockerfile.sim, the batch-mode check, and the LMR51420 (slum825) transient smoke test. My recommendation is to fetch it. If TI's licence or the installer refuses to run under Wine, I will record install=no with the error text and keep the hand-built averaged buck model for sim-02.

### 2026-11-20
Commits:
- 2e62903 fnd-08: ./run --sim-gui and ltspice shortcut (X11, own-user xhost, revoked on exit)
- 0c9e41a fnd-08: record the live LTspice GUI check (user-confirmed)
- f2dcac0 fnd-08: --sim-gui adds --ipc=host and SIM_GUI_DPI (default 144); LTspice-syntax example net
- b7b74f4 fnd-08: list the PSpice for TI installer in the datasheets manifest (access: login, user-fetch)
- c643fc2 fnd-08: software/ folder for tool installers; PSpice for TI and LTspice entries move there
Notes:
- step 2: ran ./run --sim-gui ltspice tests/sim/rc_lowpass.cir; xhost grant and revoke worked; the run ended with X Error BadValue (MIT-SHM, X_ShmPutImage, opcode 130/3), exit code 0.
- likely cause: MIT-SHM across the container boundary (no --ipc=host); candidate fixes: add --ipc=host to the --sim-gui docker command, or disable shm. Not applied (step 1 code).
- sim_gui_shown not written: no user confirmation that the window opened and the plot works.
Verify: not run
Independent review: not recorded
Blocked: step 3: Please save the PSpice for TI installer, once your TI access arrives, as /home/david/Documents/pcb_work/fmcw3-ckflight/software/files/ti/pspice-for-ti-installer.zip. Get it from https://www.ti.com/tool/PSPICE-FOR-TI while signed in, and take the full Windows installer, not the web stub. If TI gives you an .exe, tell me the real file name and I will change the manifest entry's 'file'. Then tell me, and I will run './run tools/fetch_sources.py --record' to pin the hash and continue with the Wine install, the batch check and the slum825 smoke test. My recommendation is to fetch it; if the installer will not run under Wine, I will record install=no with the error text and keep the hand-built averaged buck model for sim-02.

### 2026-11-20
Unblocked: was blocked: step 3: Please save the PSpice for TI installer, once your TI access arrives, as /home/david/Documents/pcb_work/fmcw3-ckflight/software/files/ti/pspice-for-ti-installer.zip. Get it from https://www.ti.com/tool/PSPICE-FOR-TI while signed in, and take the full Windows installer, not the web stub. If TI gives you an .exe, tell me the real file name and I will change the manifest entry's 'file'. Then tell me, and I will run './run tools/fetch_sources.py --record' to pin the hash and continue with the Wine install, the batch check and the slum825 smoke test. My recommendation is to fetch it; if the installer will not run under Wine, I will record install=no with the error text and keep the hand-built averaged buck model for sim-02.

### 2026-11-20
Commits:
- 2e62903 fnd-08: ./run --sim-gui and ltspice shortcut (X11, own-user xhost, revoked on exit)
- 0c9e41a fnd-08: record the live LTspice GUI check (user-confirmed)
- f2dcac0 fnd-08: --sim-gui adds --ipc=host and SIM_GUI_DPI (default 144); LTspice-syntax example net
- b7b74f4 fnd-08: list the PSpice for TI installer in the datasheets manifest (access: login, user-fetch)
- c643fc2 fnd-08: software/ folder for tool installers; PSpice for TI and LTspice entries move there
- 1900823 fnd-08: identify U25 as ST LD39200PU33R (datasheet in manifest); mark PSpice for TI rows deferred to sim-05
Notes:
- step 2: ran ./run --sim-gui ltspice tests/sim/rc_lowpass.cir; xhost grant and revoke worked; the run ended with X Error BadValue (MIT-SHM, X_ShmPutImage, opcode 130/3), exit code 0.
- likely cause: MIT-SHM across the container boundary (no --ipc=host); candidate fixes: add --ipc=host to the --sim-gui docker command, or disable shm. Not applied (step 1 code).
- sim_gui_shown not written: no user confirmation that the window opened and the plot works.
Verify: Verify passed: ./run uv run pytest tests -q && ./run --sim python3 -m pytest tests/test_sim_smoke.py -q && friday result check fnd-08 --require 'sim_gui_shown == 1' --files
Independent review: no gaps
