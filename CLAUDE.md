# fmcw3-ckflight

Fork of `ckflight/FMCW3-Kicad`: a 6-layer, Artix-7 (XC7A100T, U30, per
`docs/surveys/upstream-survey.md`), 5.8 GHz FMCW radar board. `production/` is the as-ordered
XC7A35T build, not the current design.
Used as a submodule of the Falcon parent repo (under `hardware/`); directive ids like
hw-17..19 in `README.md` refer to that parent repo, not to `docs/directives/` here.
Firmware lives in a separate repo (`davidmhunt/fmcw3-ckflight-fw`). Licence: GPLv3 (`LICENSE`).

## Tools
- KiCad **10.0.5** (`kicad-cli` on PATH). The project is in KiCad 10 format; KiCad 9 cannot
  open `kicad/fmcw3.kicad_pcb`.
- Run commands through the wrapper: `./run <cmd...>` (Docker image `fmcw3-tools` if available,
  else native); `./run --docker ...` / `./run --native ...` force one. Tests:
  `./run uv run pytest tests -q`.
- Checks: `./run checks/run_checks.sh` (ERC + DRC on `kicad/` against `checks/baseline.json`);
  `./run checks/run_checks.sh --record` re-records the baseline and reports (use `--native`;
  Docker ERC has extra library-config warnings, see `checks/README.md`).
- ERC by hand: `kicad-cli sch erc --format json -o OUT.json kicad/fmcw3.kicad_sch`
- DRC by hand: `kicad-cli pcb drc --format json -o OUT.json kicad/fmcw3.kicad_pcb`
- Reports: `./run tools/build_report.py analysis/NN_name [--targets NAME] [--check]` builds
  `reports/NN_name.pdf`, `.pptx` and `NN_name_ppt.pdf` (deck exported by LibreOffice) from
  `writeup.md` and `deck.yaml` (never `report.md`).
  `./run tools/build_all.py [--check]` rebuilds every analysis. Built files are gitignored:
  never commit `reports/*.pdf` or `.pptx`.
  Tests: `./run uv run pytest tests -q`. Target sets: `analysis/targets/*.yaml`, loaded by
  `tools/targets.py`; `design` group (required, printed first) and `performance` group
  (optional); range resolution is derived from bandwidth, never set.
- Root sheet is `kicad/fmcw3.kicad_sch`; sub-sheets are `adc clock fpga fpga_config mixer
  opamp_amp power rx tx usb` (`.kicad_sch`).

## Baseline (do not assume clean)
- Upstream is NOT ERC/DRC clean; counts by type are in `checks/README.md` and
  `checks/baseline.json`. A bare `--exit-code-violations` fails today. Verify with
  `checks/run_checks.sh` (errors not above baseline).
- DRC is nondeterministic run to run: `solder_mask_bridge` count jitters by +/-1 on identical
  input. Never Verify on an exact DRC warning count.

## Files not to touch / treat with care
- `production/` is upstream's as-ordered JLCPCB fab package (XC7A35T build); do not
  regenerate in place. New fab outputs go to new paths and are recorded with
  `friday result write --file`.
- `.env` holds DigiKey API credentials for `parts/check_digikey.py`. Never read it into
  output, never commit it.
- Before changing anything under `kicad/`, run `./run --native tools/kicad_ipc.py status`.
  `closed`: file-level edits are allowed. `other`: stop and ask the user. `ipc`:
  - board edits go only through `tools/kicad_ipc.py` (IPC), as one undoable commit, never
    saving, and only while the Schematic Editor is closed (the tool refuses otherwise; KiCad
    10 freezes); the user reviews in the GUI and saves;
  - schematic edits are never live on KiCad 10 (no schematic API until KiCad 11).
  (Amended after the fnd-06 live trial; see `docs/kicad-ipc.md`.)
- Never write `kicad/*.kicad_sch` or `kicad/*.kicad_pcb` directly while KiCad has the project open.
- If an edit is needed that IPC cannot do while the project is open (any schematic change, or
  a board edit while the user needs the Schematic Editor open), stop and ask the user to close
  KiCad, or just the Schematic Editor; after the edit, ask them to reopen it.
- Batch operations (ERC, DRC, exports, report builds) use `kicad-cli` through `./run`. Analyses
  read the files headless so reports rebuild without the GUI. When the project is open, use
  `tools/kicad_ipc.py show` to select what is being discussed so the user can follow along.

## Keep MANUAL.md current
- A directive that adds or changes a tool, a software download or a `./run` mode updates
  `MANUAL.md` in the same directive. The reviewer treats a stale manual as a gap.
  `tests/test_manual.py` enforces the coverage.

## Division of labour
- The agent: run ERC/DRC, exports, BOM/availability checks, apply written-down part changes. When
  the project is open in KiCad, the agent may make written-down board edits live through IPC
  (`tools/kicad_ipc.py`) while the user watches; the user reviews and saves.
- The user: routing, placement, part/footprint choice, any electrical design decision,
  ordering and sending to a fab. These stay the user's even when IPC makes an edit easy.
  Schematic or layout changes are `Accept: user` with a `## Review` naming sheets, layers and
  refdes.

## Layout
- `kicad/`: the KiCad project. `kicad-1rx/`: the 1-RX variant, under the same rules as `kicad/`
  (`--project kicad-1rx` on the checks and parts tools). `legacy/`: unused upstream exports (see its README).
- `checks/`: ERC/DRC gate, baseline and recorded reports.
- `docs/references/pcb-review-plan.md` (and the PDF): the user's 7-phase review plan (parts,
  RF chain, impedance, testability, ERC/DRC, SPICE, spurs) and its open questions. The source
  for `/friday:plan`.
- `docs/goals/`, `docs/directives/`: friday plan files (written by `/friday:plan`).
  `docs/surveys/`: upstream survey. `docs/upstream-readme.md`: upstream's README.
- `parts/`: BOM groups (`parts.csv`), DigiKey availability check and its outputs.
- `analysis/`, `reports/`, `datasheets/`, `docker/`: placeholders with READMEs.
- `runs/<id>/notes.md` (untracked): findings from measure-only steps.
