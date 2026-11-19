# fmcw3-ckflight

Fork of `ckflight/FMCW3-Kicad`: a 6-layer, Artix-7 (XC7A35T), 5.8 GHz FMCW radar board.
Used as a submodule of the Falcon parent repo (under `hardware/`); directive ids like
hw-17..19 in `README.md` refer to that parent repo, not to `docs/directives/` here.
Firmware lives in a separate repo (`davidmhunt/fmcw3-ckflight-fw`). Upstream licence: GPLv3.

## Tools
- KiCad **10.0.5** (`kicad-cli` on PATH). Board and project were re-saved in KiCad 10 format
  (dc25294); KiCad 9 can no longer open `fmcw3.kicad_pcb`. `README.md` still says "KiCad 9".
- ERC: `kicad-cli sch erc --format json -o reports/erc.json fmcw3.kicad_sch`
- DRC: `kicad-cli pcb drc --format json -o reports/drc.json fmcw3.kicad_pcb`
- Root sheet is `fmcw3.kicad_sch`; sub-sheets are `adc clock fpga fpga_config mixer
  opamp_amp power rx tx usb` (`.kicad_sch`).

## Baseline (do not assume clean)
- Upstream as forked is NOT ERC/DRC clean: ERC 1118 (1 error, 1117 warnings), DRC 410
  (4 errors, 406 warnings), from `reports/*.json` at cf34c04. So a bare
  `--exit-code-violations` Verify fails today. Verify against the baseline instead (e.g. no
  new errors, or a count not above the baseline) or scope severity with `--severity-error`.
- DRC is nondeterministic run to run: `solder_mask_bridge` count jitters by +/-1 on identical
  input. Never Verify on an exact DRC warning count.

## Files not to touch / treat with care
- `~_autosave-fmcw3.kicad_pcb.lck` is a stray lock file committed upstream and deliberately
  left in place; it makes the KiCad GUI think the board is open. Do not delete it without a directive.
- `production/` is upstream's as-shipped JLCPCB fab package; do not regenerate in place.
  New fab outputs go to new paths and are recorded with `friday result write --file`.
- `fmcw3-backups/`, `rescue-backup/`, `*.plt`, `fmcw3.pdf`, `fmcw3.net`, `fmcw3.xml`,
  `fmcw3.sch`, `fmcw3-cache.lib`, `fmcw3-rescue.lib`: upstream legacy/exports. Read-only.
- `.digikey.env` holds DigiKey API credentials for `parts/check_digikey.py`. Never read it into
  output, never commit it.
- Never edit `.kicad_sch`/`.kicad_pcb` while the user has the project open in KiCad.

## Division of labour
- The agent: run ERC/DRC, exports, BOM/availability checks, apply written-down part changes.
- The user: routing, placement, part/footprint choice, any electrical design decision,
  ordering and sending to a fab. Schematic or layout changes are `Accept: user` with a
  `## Review` naming sheets, layers and refdes.

## Layout
- `docs/references/pcb-review-plan.md`: the user's 7-phase review plan (parts, RF chain,
  impedance, testability, ERC/DRC, SPICE, spurs) and its open questions. The source for
  `/friday:plan`; written against b0dbb27, before the KiCad 10 re-save.
- `docs/goals/`, `docs/directives/`: friday plan files (written by `/friday:plan`).
- `parts/`: BOM groups (`parts.csv`), DigiKey availability check and its outputs.
- `reports/`: ERC/DRC JSON reports and how they were produced.
- `runs/<id>/notes.md` (untracked): findings from measure-only steps.
