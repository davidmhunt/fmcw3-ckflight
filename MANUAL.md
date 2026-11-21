# Workspace manual

How to set up this workspace and use every tool in it. This is the one place to start; each
section links to the detailed doc when there is one. `README.md` says what the board is and how
the repo is laid out.

The rule: a change that adds or changes a tool, a software download or a `./run` mode updates
this file in the same change. `tests/test_manual.py` fails when it falls behind.

## 1. Setup

You need Linux, Docker, git and [uv](https://docs.astral.sh/uv/). You also need native KiCad
10.0.5 for the GUI, the IPC API and native checks. Step by step, including the KiCad PPA pin and
the DigiKey keys: [`docs/setup.md`](docs/setup.md).

```sh
git clone <this repo> && cd fmcw3-ckflight
cp .env.example .env            # then fill in the API keys (never commit .env)
./run checks/run_checks.sh      # builds the fmcw3-tools image on first use
./run uv run pytest tests -q
```

## 2. The `./run` wrapper

Every command goes through `./run`, so it runs the same way on any machine.

| Mode | Runs in | Use it for | Example |
|---|---|---|---|
| `./run <cmd>` | `fmcw3-tools` image if Docker works, else the host | everyday commands | `./run checks/run_checks.sh` |
| `./run --docker <cmd>` | `fmcw3-tools` (KiCad 10.0.5, Python, uv, pandoc, LibreOffice) | forcing the container | `./run --docker kicad-cli version` |
| `./run --native <cmd>` | the host | native KiCad, the KiCad IPC client | `./run --native tools/kicad_ipc.py status` |
| `./run --sim <cmd>` | `fmcw3-sim` (ngspice, LTspice under Wine with spicelib, openEMS, scikit-rf) | simulations and their tests | `./run --sim python3 -m pytest tests/test_sim_smoke.py -q` |
| `./run --sim-gui <cmd>` | `fmcw3-sim`, shown on your X11 desktop | GUI tools in the container | `./run --sim-gui ltspice tests/sim/rc_lowpass_ltspice.net` |

`--sim-gui` details:
- It grants X11 access only to your own user, revoked when the command exits, and passes
  `--ipc=host` (needed for Wine's shared-memory drawing).
- Text is scaled with `SIM_GUI_DPI` (default 144, which is 150 %), for example
  `SIM_GUI_DPI=192 ./run --sim-gui ltspice`.
- `--print` shows the docker command without running it.
- An LTspice netlist (`.net`) opens as text. After a run, right-click the plot and use Add
  Traces. A schematic (`.asc`) opens as a drawing you can probe.

Images: `docker/Dockerfile` (`fmcw3-tools`) and `docker/Dockerfile.sim` (`fmcw3-sim`, first
build about 25 minutes). Both are built automatically on first use. Details:
[`docker/README.md`](docker/README.md).

## 3. KiCad: checks, exports and the open project

- **ERC and DRC gate**: `./run checks/run_checks.sh`. It passes when error counts are not above
  `checks/baseline.json`, with 0 unconnected items and 0 schematic-parity issues. Warning
  counts are only printed: DRC jitters by ±1. `--record` re-records the baseline (use
  `--native`). See [`checks/README.md`](checks/README.md).
- **Batch work** (ERC, DRC, exports) uses `kicad-cli` through `./run`, with KiCad 10.0.5 in
  the image and on the host.
- **Following along in your open KiCad (IPC API)**: `tools/kicad_ipc.py`, run natively.
  - `status` prints `ipc`, `closed` or `other`.
  - `show --refs ... --nets ...` selects parts and nets on the board so you can see what is
    being discussed.
  - `set-fields` (schematic fields) needs KiCad 11.

  On KiCad 10, live edits are board-only and need the Schematic Editor closed (KiCad freezes
  otherwise). Schematic changes need KiCad closed. Setup, the version pin (`kicad-python`
  0.8.0) and the trial results: [`docs/kicad-ipc.md`](docs/kicad-ipc.md).

## 4. Reports and decks

Each analysis is a folder `analysis/NN_name/` containing:
- `writeup.md` (never `report.md`);
- `deck.yaml`;
- `figures.py`, which regenerates every figure and table into `build/`.

Convention: [`analysis/README.md`](analysis/README.md).

- `./run tools/build_report.py analysis/NN_name [--targets NAME] [--check]` builds three files:
  `reports/NN_name.pdf`, `reports/NN_name.pptx` and `reports/NN_name_ppt.pdf` (the slides as a
  PDF).
- `./run tools/build_all.py [--check]` rebuilds every analysis.
- Built files are gitignored and never committed: rebuild them locally.
- Target sets live in `analysis/targets/*.yaml` and load through `tools/targets.py`:
  - a `design` group (required, printed first): frequency range, chirp bandwidth, sample
    rate, TX power, TX/RX isolation, board quantity;
  - an optional `performance` group.

  Range resolution is derived from the bandwidth.

## 5. Simulation and RF tools

Which tool is used for which analysis, and why: [`docs/analysis-tools.md`](docs/analysis-tools.md).
In short:

| Tool | Runs | Used for |
|---|---|---|
| LTspice (ADI), through `spicelib` | `./run --sim` (batch), `./run --sim-gui ltspice` (GUI) | circuits with ADI models, and mixed ADI and TI circuits |
| ngspice | `./run --sim` | TI-only circuits (PSpice mode `ngbehavior=psa`) |
| PSpice for TI | under Wine in `fmcw3-sim`, **deferred to sim-05 (waiting on TI access)** | TI-encrypted models such as the LMR51420 buck |
| openEMS | `./run --sim` | 3D EM fallback and cross-check (SMA launch, vias) |
| scikit-rf | `./run --sim` | RF cascade and S-parameters |

Every circuit simulated in goals `sim-spurs` and `rf-review` is committed both as a netlist and
as an LTspice `.asc` schematic you can open with `--sim-gui`.

## 6. Software downloads

Installers are listed in [`software/manifest.yaml`](software/manifest.yaml) and stored under
`software/files/`, which is gitignored. Save a download by hand at the `file` path below. Then
run `./run tools/fetch_sources.py --record` to pin its hash, and `--check` to verify it.
[`software/README.md`](software/README.md) has the details.

| Id | What | Link | Account | Save as |
|---|---|---|---|---|
| `adi-ltspice-installer` | LTspice 64-bit Windows installer; the sim image downloads it at build | https://ltspice.analog.com/software/LTspice64.msi | no | `software/files/adi/LTspice64.msi` |
| `ti-pspice-for-ti-installer` | PSpice for TI (Windows), for TI-encrypted models | https://www.ti.com/tool/PSPICE-FOR-TI | TI account | `software/files/ti/pspice-for-ti-installer.zip` |

## 7. Tools you run elsewhere

These are GUI-only, licensed or web tools, used by you, mostly on a Windows machine. Where a
checklist exists it says what to enter and what to record back into the repo; the checklists are
in [`docs/gui-tool-checklists.md`](docs/gui-tool-checklists.md). CST Studio Suite and TI WEBENCH
have no checklist yet.

| Tool | Link | Checklist | Used for |
|---|---|---|---|
| CST Studio Suite Learning Edition | already installed on your Windows machine (Dassault Systèmes student licence) | none yet | 3D EM where its size limits allow; `.s2p` results committed, or listed in a manifest if too large |
| ADIsimPLL | the ADIsimPLL page on analog.com (Windows; not verified from here, find the installer on the page) | [ADIsimPLL](docs/gui-tool-checklists.md#adisimpll-adf4158-chirp-pll-review-plan-phase-6-item-4-and-phase-7) | validating the PLL model (sim-03) |
| ADIsimRF | the ADIsimRF page on analog.com (Windows; not verified from here, find the installer on the page) | [ADIsimRF](docs/gui-tool-checklists.md#adisimrf-rf-cascade-review-plan-phase-2) | RF cascade cross-check (rf-01) |
| Saturn PCB Toolkit | https://saturnpcb.com/saturn-pcb-toolkit/ (Windows; Download button opens an email form) | [Saturn PCB Toolkit](docs/gui-tool-checklists.md#saturn-pcb-toolkit-impedance-cross-check-review-plan-phase-3) | impedance hand check (rf-02) |
| TI WEBENCH | https://webench.ti.com (browser, TI account) | none yet | buck cross-check (sim-02) |
| JLCPCB impedance calculator | https://jlcpcb.com/pcb-impedance-calculator (browser) | [JLCPCB impedance calculator](docs/gui-tool-checklists.md#jlcpcb-impedance-calculator-the-fabs-own-reference-browser-user-run) | final trace widths for JLCPCB's stackups (rf-02) |

## 8. Datasheets, models and references

There are three manifests, all read by `tools/fetch_sources.py`:
- [`datasheets/manifest.yaml`](datasheets/manifest.yaml) for datasheets and vendor models;
- [`docs/references/manifest.yaml`](docs/references/manifest.yaml) for papers, app notes and
  books;
- [`software/manifest.yaml`](software/manifest.yaml) for installers.

`./run tools/fetch_sources.py`:
- downloads every public entry;
- prints a to-do list with links for entries behind a form or a login;
- `--check` fails on a missing file, a hash mismatch, or a reference without `verified` items.
  An entry behind a form or login that you have not fetched yet, with no hash pinned, is listed
  as `PENDING` instead of failing; once its hash is pinned, a missing file fails.

Adding a source: `./run tools/fetch_sources.py --add URL --id ID --kind KIND --title TEXT
--file datasheets/files/<vendor>/<name>.pdf [--licence TEXT] [--commit yes|no] [--manifest PATH]`
downloads the URL, computes the SHA-256 and appends an entry to `datasheets/manifest.yaml` (or
the manifest you name) with `access: direct`. `--commit` defaults to `no`, which needs a path
under a `files/` directory; use `yes` only when the licence allows redistribution. It refuses an
id that already exists in any manifest and reports a dead link without adding anything.

Every calculation the repo implements itself cites a reference that was downloaded and checked
against the file (page and equation recorded), never from memory. Files are committed only when
their licence allows it.

## 9. Parts and availability

One command groups the BOM from the schematic (read headless, nothing under `kicad/` is
written) and checks every line against DigiKey and the JLCPCB parts library. Columns, match
confidence and how to add keys: [`parts/README.md`](parts/README.md).

- `./run parts/bom.py [--targets NAME] [--boards N] [--spares N] [--offline] [--check]`:
  writes `parts/out/bom.csv`, `parts/out/availability.csv` (one verdict per line: JLC assemble,
  consign from DigiKey, hand-solder, unresolved) and a JLCPCB BOM and CPL under
  `parts/out/jlc/`. Boards default to `board_quantity` of the target set. `--offline` uses the
  caches only; `--check` exits 1 on a placed part without an MPN.
- `./run parts/check_digikey.py [--boards N] [--spares N] [--limit K]`: the DigiKey lookup alone.
  Needs `DIGIKEY_CLIENT_ID` and `DIGIKEY_CLIENT_SECRET` in `.env` (never commit it).
- `./run parts/check_jlc.py [--boards N] [--spares N] [--limit K] [--refresh | --offline]`: the
  JLCPCB lookup alone. The first run downloads the parts database (about 190 MB, 830 MB
  unpacked) into the gitignored `parts/cache/jlcpcb/`.

## 10. How work is planned and run

Work is planned and run with friday:
- **Goals** in [`docs/goals/`](docs/goals/) are one PR each.
- **Directives** in [`docs/directives/`](docs/directives/) are the reviewable steps, each with a
  `Verify:` command.
- The agent implements a directive on the goal branch `friday/<goal>`, gates it on Verify and
  has it reviewed independently.
- Directives marked `Accept: user` wait for you: `friday accept <id>`, or
  `friday accept <id> --reject REASON`.
- `friday status` shows where everything stands. `friday land --goal <goal>` opens the goal's
  PR into `falcon_development`.

The repo-wide rules every agent follows are in `.claude/friday.json` and
[`CLAUDE.md`](CLAUDE.md).
