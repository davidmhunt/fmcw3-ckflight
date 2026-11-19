# fnd-01: Survey legacy files, upstream branches and the firmware repo before cleanup
Status: approved
Goal: foundation
Node: any
Deliverable: doc
Accept: user
Verify: test -s docs/surveys/upstream-survey.md && grep -q '^## Legacy files' docs/surveys/upstream-survey.md && grep -q '^## Branches' docs/surveys/upstream-survey.md && grep -q '^## Firmware' docs/surveys/upstream-survey.md && grep -q '^## Safe to delete' docs/surveys/upstream-survey.md
Hardware: none

## Goal
A written survey, `docs/surveys/upstream-survey.md`, that says whether the legacy files and the
other upstream branches hold anything the current KiCad 10 project lacks, and what the firmware
repo tells us about the hardware. It holds when the user can read it and decide that fnd-02 may
delete the legacy files.

## Steps
1. Legacy versus current. Export the component list and netlist of the current project
   (`kicad-cli sch export netlist` and `sch export bom` on `fmcw3.kicad_sch`, output under
   `runs/fnd-01/`). Parse the legacy files (`fmcw3.sch` and its sheets if present, `fmcw3.net`,
   `fmcw3.xml`, `fmcw3.csv`, `fmcw3-cache.lib`, `fmcw3-rescue.lib`, `libs/`, `rescue-backup/`,
   `fmcw3-backups/`, `production/backups/`) and compare refdes, values, footprints and nets.
   Record file dates and KiCad versions. List every difference; say for each whether the current
   project supersedes it.
2. Branches. For each of `origin/jlcpcb_v2`, `origin/jlcpcb_version`, `origin/lt6232_implement`,
   `origin/lt6232_ld3920_33`, `origin/oshpark_version`: `git log`/`git diff` against `origin/main`,
   confirm whether it is merged, and extract what differs: part substitutions, stackup, LCSC
   numbers in BOM files, fab outputs, README text. Read-only: use `git show`/`git worktree` under
   `runs/fnd-01/`, never check a branch out in the main tree.
3. Firmware. Clone `davidmhunt/fmcw3-ckflight-fw` into `runs/fnd-01/fw` (read-only). Record: FPGA
   variants built (35T, 100T), pin constraints (`.xdc`) versus the schematic's FPGA net names with
   any mismatch listed, clock frequencies, ADC sample rate, ADF4158 register/chirp settings.
4. Write `docs/surveys/upstream-survey.md` with sections `## Legacy files`, `## Branches`,
   `## Firmware`, `## Worth carrying over` and `## Safe to delete` (an explicit list of paths with a
   yes/no and reason for each). Each claim names the file, branch or commit it comes from.

## Acceptance
- Every legacy path named in step 1 appears in `## Safe to delete` with yes or no and a reason.
- All five branches have a subsection saying merged or not, and what differs from `main`.
- `## Firmware` states the FPGA variants, the clock and sample-rate numbers with file references,
  and the result of the pin-constraint comparison.
- `## Worth carrying over` lists concrete items (or says none) with where each should go later.
- No file outside `docs/surveys/` is changed.

## Review
- Open `docs/surveys/upstream-survey.md`. Check `## Safe to delete`: fnd-02 deletes or archives
  exactly what is marked yes.
- Read `## Worth carrying over` and say if any item should change the later goals.

## Out of scope
- Deleting, moving or editing any existing file.
- Evaluating upstream's host software repos.

## Allowed commands
- `gh repo clone davidmhunt/fmcw3-ckflight-fw runs/fnd-01/fw*`
- `git worktree add runs/fnd-01/*`

## Log
