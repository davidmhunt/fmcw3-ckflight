# fnd-02: Restructure the repo (KiCad project into kicad/, legacy cleanup, one README)
Status: approved
Goal: foundation
Node: any
Deliverable: code
Accept: user
Verify: checks/run_checks.sh && test -f kicad/fmcw3.kicad_pcb && test ! -e fmcw3.kicad_pcb && test -z "$(git ls-files '*.lck' fmcw3-backups rescue-backup)"
Hardware: none

## Goal
A clean root: all KiCad content in `kicad/`, legacy exports in `legacy/`, the lock file and
backups gone, one README, and an ERC/DRC check that compares against a recorded baseline. It
holds when the netlist exported after the move equals the one exported before, and
`checks/run_checks.sh` passes.

## Steps
1. Preconditions. Stop with `blocked` if fnd-01 is not `done` (accepted by the user), or if a
   KiCad process is running (`pgrep kicad`). Export the netlist and BOM of the untouched project
   to `runs/fnd-02/before/`.
2. Move with `git mv` (history kept) into `kicad/`: `fmcw3.kicad_pro`, `fmcw3.kicad_pcb`,
   `fmcw3.kicad_sch`, the ten sheet files, `fmcw3.pretty/`, `libs/`, `sym-lib-table`,
   `fp-lib-table`, `fabrication-toolkit-options.json`, `fmcw3.round-tracks-config`. Untrack
   `fmcw3.kicad_prl` and `fp-info-cache` (local state; already or newly gitignored).
3. Delete `~_autosave-fmcw3.kicad_pcb.lck`, `fmcw3-backups/`, `rescue-backup/`. Move to `legacy/`
   the paths fnd-01 marked safe: `*.plt`, `fmcw3.sch`, `fmcw3.net`, `fmcw3.xml`, `fmcw3.csv`,
   `fmcw3-cache.lib`, `fmcw3-rescue.lib`, upstream's `fmcw3.pdf`. Anything fnd-01 marked "no" is
   kept and noted. Add `legacy/README.md` (what each file is, that it is not used).
4. Library tables. Rewrite `kicad/sym-lib-table` and `kicad/fp-lib-table` so they list only
   libraries that exist in the repo, with `${KIPRJMOD}`-relative paths (today they point into
   `/home/ck/...`). Do not edit `lib_id` or any other content of `.kicad_sch`/`.kicad_pcb`; the
   schematic and board files must be pure renames (`git diff -M --stat` shows 100% similarity).
   Record which symbol or footprint links still do not resolve, for goal `layout-review`.
5. Checks. Move `reports/erc.json`, `reports/drc.json` and their README to `checks/`. Write
   `checks/run_checks.sh`: runs ERC and DRC with `kicad-cli` on `kicad/` into a temp dir and exits
   0 only when error-severity counts are not above `checks/baseline.json`, and DRC reports 0
   unconnected items and 0 schematic-parity issues. It never compares warning counts exactly (DRC
   jitters). Re-record `checks/baseline.json` and the two JSON reports after step 4, and state the
   before/after counts by type in `checks/README.md`.
6. Proof of no electrical change: export the netlist again to `runs/fnd-02/after/` and diff it
   against step 1, ignoring dates, tool version and source paths. Any other difference is a
   failure to fix, not to accept.
7. Docs. Merge `readme.md` (upstream's) and `README.md` into one `README.md`: what the board is,
   the folder map, how to run the checks, the roadmap of goals, upstream and licence. Keep
   upstream's text as `docs/upstream-readme.md`. Add `LICENSE` (GPLv3 text, as upstream states).
   Commit the review-plan PDF in `docs/references/`. Create empty-with-README
   folders `analysis/`, `reports/`, `datasheets/`, `docker/`. Update `CLAUDE.md` to the new
   paths, commands and rules (remove the lock-file and legacy rules that no longer apply; rename
   `.digikey.env` to `.env`), and `.gitignore` accordingly. In `CLAUDE.md` the board's FPGA is
   XC7A100T (U30, per `docs/surveys/upstream-survey.md`), not XC7A35T; `production/` is the
   as-ordered 35T build.
8. Upstream branches (amendment approved by the user 2026-11-19). For each of `jlcpcb_v2`,
   `jlcpcb_version`, `lt6232_implement`, `lt6232_ld3920_33`, `oshpark_version`: create an annotated
   tag `archive/<branch>` on `origin/<branch>`'s tip with a one-line message (merged into main or
   not, per the survey), push the tags, confirm each tag resolves to the same SHA as the branch,
   then delete the remote branch. Record branch, SHA and tag in the root `README.md` under a
   short "Archived upstream branches" note.

## Review
- Open `kicad/fmcw3.kicad_pro` in the KiCad 10 GUI: the schematic and board open without a
  "file already open" prompt and without missing-sheet errors; footprint and symbol libraries
  resolve from the project (Preferences, Manage Libraries, Project Specific tab).
- Read the root `README.md` and look at the root folder listing: is this the layout you wanted.
- Read `checks/README.md`: the before/after ERC/DRC counts, and the netlist-equality result.
- `git ls-remote --tags origin 'archive/*'` lists five tags; the five branches are gone from GitHub.

## Out of scope
- Any edit inside a `.kicad_sch` or `.kicad_pcb` file.
- Regenerating or moving `production/`.
- Fixing ERC/DRC findings (goal `layout-review`).
- Updating the Falcon parent repo's submodule paths, or syncing with upstream.

## Allowed commands
- `git tag -a archive/* origin/* -m *`
- `git push origin refs/tags/archive/*`
- `git push origin --delete jlcpcb_v2 jlcpcb_version lt6232_implement lt6232_ld3920_33 oshpark_version`

## Log
