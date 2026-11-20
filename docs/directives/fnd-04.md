# fnd-04: Report and deck pipeline with target sets and a baseline report
Status: approved
Goal: foundation
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests -q && ./run tools/build_report.py analysis/00_baseline --check
Hardware: none

## Goal
One command turns an analysis folder into a PDF report and a `.pptx` deck in `reports/`, and
every analysis reads its system targets from a named target set. It holds when
`./run tools/build_report.py analysis/00_baseline` produces both files from scripts and data in
the repo, with no hand-made figure.

## Steps
1. Convention, documented in `analysis/README.md`: each analysis is `analysis/NN_name/` with
   `writeup.md` (the full write-up; not `report.md`, which Claude Code refuses to let subagents
   write; amendment approved by the user 2026-11-20), `deck.yaml` (slide list: title, bullets, figure or table
   reference, speaker note), `figures.py` (regenerates every figure and table into `build/`,
   gitignored) and optional data files. Every report starts with: question, inputs and
   assumptions (target set name and values), method, findings, open decisions for the user.
2. `tools/build_report.py <analysis dir> [--targets NAME] [--check]`: runs `figures.py`, builds
   `reports/NN_name.pdf` from `writeup.md` with pandoc, and `reports/NN_name.pptx` from
   `deck.yaml` with python-pptx using one shared 16:9 template (`tools/deck_template.py`:
   title, bullet, figure, table and "decisions needed" layouts). `--check` fails on a missing
   figure, an unresolved reference, or text that overflows a slide's text box (estimate from
   character count and font size per layout; unit-tested).
3. Targets: `analysis/targets/default.yaml` (max range, range resolution or chirp bandwidth,
   chirp duration, sample rate, TX power, antenna gain and isolation, board quantity) with
   values marked `assumed` until the user sets them, a schema check, and
   `tools/targets.py` to load a set by name. Reports print the target set they used.
4. Git LFS: `.gitattributes` tracks `reports/*.pdf` and `reports/*.pptx`. Before committing any
   LFS object, push one small test object to `origin` on the goal branch; GitHub can refuse LFS
   uploads to a fork. If refused, commit built files as normal git files, say so in
   `reports/README.md`, and note it in `runs/fnd-04/notes.md`.
5. First real report, `analysis/00_baseline/`: the state of the board as inherited. ERC/DRC
   counts by type from `checks/` with a bar chart, what each type means and which goal handles
   it, the folder map, the roadmap. Build it and commit `reports/00_baseline.pdf` and `.pptx`.
6. Tests in `tests/`: target loading and schema errors, deck overflow check, a build of a tiny
   fixture analysis. Document the commands in `README.md` and `CLAUDE.md`.

## Review
- Open `reports/00_baseline.pptx` and `reports/00_baseline.pdf`: is the deck style, level of
  detail and slide density what you want for every later analysis. Say what to change now; the
  template is reused by all later goals.
- Open `analysis/targets/default.yaml`: are these the right parameters to carry as targets.

## Out of scope
- Any new analysis beyond summarising the existing ERC/DRC baseline.
- Online documents (Claude Docs, Google Slides).

## Allowed commands
- `./run *`
- `git lfs track *`

## Log
