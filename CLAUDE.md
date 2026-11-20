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
  `reports/NN_name.pdf` and `.pptx` from `writeup.md` and `deck.yaml` (never `report.md`).
  Tests: `./run uv run pytest tests -q`. Target sets: `analysis/targets/*.yaml`, loaded by
  `tools/targets.py`.
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
- Never edit `.kicad_sch`/`.kicad_pcb` while the user has the project open in KiCad.

## Division of labour
- The agent: run ERC/DRC, exports, BOM/availability checks, apply written-down part changes.
- The user: routing, placement, part/footprint choice, any electrical design decision,
  ordering and sending to a fab. Schematic or layout changes are `Accept: user` with a
  `## Review` naming sheets, layers and refdes.

## Layout
- `kicad/`: the KiCad project. `legacy/`: unused upstream exports (see its README).
- `checks/`: ERC/DRC gate, baseline and recorded reports.
- `docs/references/pcb-review-plan.md` (and the PDF): the user's 7-phase review plan (parts,
  RF chain, impedance, testability, ERC/DRC, SPICE, spurs) and its open questions. The source
  for `/friday:plan`.
- `docs/goals/`, `docs/directives/`: friday plan files (written by `/friday:plan`).
  `docs/surveys/`: upstream survey. `docs/upstream-readme.md`: upstream's README.
- `parts/`: BOM groups (`parts.csv`), DigiKey availability check and its outputs.
- `analysis/`, `reports/`, `datasheets/`, `docker/`: placeholders with READMEs.
- `runs/<id>/notes.md` (untracked): findings from measure-only steps.
