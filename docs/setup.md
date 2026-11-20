# Setup guide

Two ways to get the same ERC/DRC results: the pinned Docker image (easiest, no KiCad install)
or a native KiCad 10.0.5. Both are driven through the `./run` wrapper. The GUI is only used
natively; the Docker image runs the command-line tools.

## 1. Get the repo

```
git clone <url> fmcw3-ckflight        # or use it as the hardware/ submodule of the parent repo
cd fmcw3-ckflight
```

git-lfs: this repo currently has no LFS-tracked files, but the parent repo may. Install it once
(`sudo apt install git-lfs` on Ubuntu, `brew install git-lfs` on macOS, bundled with Git for
Windows) and run `git lfs install`; then `git lfs pull` in any checkout that has LFS files.

## 2. Docker path (recommended)

1. Install Docker Engine: https://docs.docker.com/engine/install/ubuntu/ (Docker Desktop on
   macOS/Windows; use WSL2 on Windows and work inside the WSL filesystem).
2. Let your user run Docker without sudo: `sudo usermod -aG docker $USER`, then log out and in.
   Check with `docker info`.
3. Run anything through the wrapper from the repo root:

   ```
   ./run --docker checks/run_checks.sh
   ./run --docker kicad-cli version        # prints 10.0.5
   ```

   The first call builds the `fmcw3-tools` image from `docker/Dockerfile` (a few minutes, large
   download: it is based on `kicad/kicad:10.0.5`). The repo is mounted at `/work`, the command runs
   as your uid/gid, and `.env` is passed in when present. Details: `docker/README.md`.
4. Python tooling (pytest etc.) runs in the same image: `./run uv run pytest tests -q`.

With no flag, `./run` uses Docker when it is usable and falls back to native otherwise.

### GUI tools from the sim container (`--sim-gui`)

`./run --sim-gui <cmd>` runs a command in the `fmcw3-sim` image with a window on your desktop
(an X11 session, `DISPLAY` set; it needs `xhost`, package `x11-xserver-utils`). It mounts
`/tmp/.X11-unix`, passes `DISPLAY`, runs as your uid like `./run`, and grants X access only to your
own user (`xhost +SI:localuser:<user>`), revoked when the command exits. It never runs `xhost +`.

```
./run --sim-gui ltspice                          # LTspice under Wine
./run --sim-gui ltspice tests/sim/rc_lowpass.cir # open a netlist (.asc or .net/.cir) from the repo
./run --sim-gui --print ltspice                  # show the docker command, run nothing
```

The file must be inside the repo. `tests/test_run_sim_gui.py` checks the printed command.

## 3. Native path

### KiCad 10.0.5 on Ubuntu

KiCad 9 cannot open this project; you need 10.x, and results are pinned to 10.0.5.

```
sudo add-apt-repository ppa:kicad/kicad-10.0-releases
sudo apt update
apt-cache policy kicad                      # confirm 10.0.5 is a candidate
sudo apt install kicad=10.0.5*              # pin the exact version
sudo apt-mark hold kicad kicad-doc          # stop apt upgrading it
kicad-cli version                           # must print 10.0.5
```

If the PPA has moved on past 10.0.5 and the exact version is no longer offered, use the Docker
path (its version is pinned) or install from the Flatpak/other source that still has 10.0.5, and
record the version you used when comparing results.

### macOS / Windows

Install the 10.0.5 release from https://www.kicad.org/download/ (macOS dmg, Windows installer).
`kicad-cli` lives inside the app bundle on macOS
(`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`) and in `C:\Program Files\KiCad\10.0\bin`
on Windows; put it on `PATH`. `checks/run_checks.sh` is a bash script, so on Windows run it in WSL
or Git Bash, or use the Docker path.

### uv and Python tooling

```
curl -LsSf https://astral.sh/uv/install.sh | sh     # or: pipx install uv
uv sync                                              # creates .venv from pyproject.toml/uv.lock
```

`./run uv run pytest tests -q` then runs the tests natively (`--native`) or in Docker. The native
branch of `./run` unsets `PYTHONPATH` so a host ROS or similar install cannot leak into pytest. If
pytest reports that `/tmp/pytest-of-$USER` is not owned by you, remove it or pass `--basetemp=DIR`.

### Running the checks natively

```
./run --native checks/run_checks.sh            # ERC + DRC against checks/baseline.json
./run --native checks/run_checks.sh --record   # re-record the baseline (only when intended)
```

The check fails if errors exceed `checks/baseline.json` or unconnected items appear. Upstream is not
clean, so a bare `kicad-cli ... --exit-code-violations` fails; use the script. The DRC
`solder_mask_bridge` count jitters by +/-1 between identical runs, so never compare an exact
warning count.

## 4. DigiKey API keys and `.env`

Only `parts/check_digikey.py` (stock and lifecycle of the BOM) needs keys.

1. Create an account at https://developer.digikey.com and sign in.
2. Open "Organizations" and create an organization (or use an existing one).
3. In the organization, choose "Create production app" (or a sandbox app to test). Give it a name
   such as `fmcw3-bom`.
4. Enable the "Product Information V4" API for the app.
5. Set the OAuth callback URL to `https://localhost` (client-credentials flow does not use it, but
   the form requires one).
6. Save. The app page shows the Client ID and Client Secret.
7. In the repo root: `cp .env.example .env`, then edit `.env` and paste the two values after
   `DIGIKEY_CLIENT_ID=` and `DIGIKEY_CLIENT_SECRET=` (no quotes needed).
8. Run `./run python3 parts/check_digikey.py`. A message "Missing DIGIKEY_..." means a value is
   empty.

`.env` is gitignored. Never commit it or paste its contents into chats, logs or issues. `./run`
passes it into the container; natively the script reads it from the repo root. The old
`.digikey.env` name is no longer read.

## 5. Rule: how project files are edited

Never write `kicad/*.kicad_sch` or `kicad/*.kicad_pcb` directly while KiCad has the project open:
KiCad keeps its own copy in memory and will overwrite the change (or the reverse) on save. Check
with `./run --native tools/kicad_ipc.py status`:

- `closed`: file-level edits are allowed.
- `other`: stop and ask.
- `ipc`: the agent may make written-down board edits live through IPC, as one undoable commit,
  never saving, while you watch; you review in the GUI and save. This needs the Schematic Editor
  closed. Schematic edits are never live on KiCad 10: close KiCad, or ask for the edit and
  reopen afterwards.

Which edits to make stays your decision (routing, placement, parts, electrical design); IPC only
applies what is written down. Read-only runs (ERC/DRC exports to a separate output file) are safe.

## 6. Following along in KiCad (IPC API)

To watch the agent select parts and nets, and make board-only edits live, enable KiCad's API
server (Preferences → Plugins). The client runs natively: `./run --native tools/kicad_ipc.py
status`. On KiCad 10, live edits need the Schematic Editor closed, and schematic changes still
need KiCad closed. See [`docs/kicad-ipc.md`](kicad-ipc.md) for the setup, the commands and what
works.
