# foundation: Clean repo layout, repeatable environment and report pipeline
Status: blocked: fnd-06
Base: falcon_development
Land: pr

## Goal
The repo is organised so the PCB review can start on a sound footing: nothing of value from
upstream's other branches or legacy files is lost, the KiCad project lives in `kicad/`, ERC/DRC
run the same way natively and in a pinned Docker image, each analysis can be built into a report
PDF and a `.pptx` deck with one command, and the Linux tools for the later analyses are chosen.
It holds when `./run checks/run_checks.sh` and `./run tools/build_report.py analysis/00_baseline`
both pass on a fresh clone following `docs/setup.md`.

## Directives
1. fnd-01: Survey legacy files, upstream branches and the firmware repo before cleanup
2. fnd-02: Restructure the repo (KiCad project into kicad/, legacy cleanup, one README)
3. fnd-03: Repeatable environment (setup guide, pinned Docker image, run wrapper, .env)
4. fnd-04: Report and deck pipeline with target sets and a baseline report
5. fnd-05: Choose and smoke-test Linux tools for the simulation and RF analyses
6. fnd-06: KiCad IPC client and a live trial with the user watching
7. fnd-07: Switch the KiCad editing rules to IPC-when-open

## Roadmap
This is the first of five goals, each one PR into `falcon_development`; a single PR from
`falcon_development` into `main` follows at the end. Later goals are written as `proposed` and
are re-checked and approved one at a time.

1. `foundation` (this goal)
2. `parts`: BOM from the schematic, DigiKey and JLCPCB checks, datasheets (review plan Phase 1)
3. `rf-review`: RF level plan and 50 ohm impedance (Phases 2 and 3)
4. `layout-review`: ERC/DRC triage, layout checks, testability and bring-up (Phases 4 and 5)
5. `sim-spurs`: supply-noise, IF filter and PLL simulation, frequency plan (Phases 6 and 7)

## Decisions (planning interview, 2026-11-19)
- "Upstream" means the original author's repo `ckflight/FMCW3-Kicad` that this repo was forked from.
- Audit first. Design changes are expected but are planned later, once part availability is known.
- Build route: JLCPCB fab plus assembly for nearly everything; SMA connectors may be hand-soldered.
  DigiKey is the second source. DigiKey's own PCB service is something the user will look into.
- Layout: flat. `kicad/` holds all KiCad content, `analysis/NN_name/` holds scripts and report
  source, `reports/` in the root holds the built PDFs and decks, `production/` keeps its path.
- Part numbers (MPN, DigiKey, LCSC) will live in schematic symbol fields (done in goal `parts`).
- Datasheets: manifest plus download script; PDFs are not committed.
- One `.env` for all API keys, with a committed `.env.example`.
- Reports: markdown source, built PDF, and a `.pptx` deck per analysis. Superseded 2026-11-20: GitHub
  refuses LFS uploads to this public fork, so built PDFs and decks are not committed at all; they are
  gitignored and rebuilt by script (fnd-04 amendment).
- System targets (range, chirp, TX power, antennas) are parameters in `analysis/targets/*.yaml`
  so every analysis can be re-run for a new target set.
- The user has Linux only: analysis tools must run natively, in Docker, or under Wine.

## Decisions (planning interview, 2026-11-20)
- Analysis write-up sources are `writeup.md`, not `report.md` (Claude Code blocks subagents from
  writing report files).
- KiCad interaction: batch work (ERC, DRC, exports, report builds) uses `kicad-cli` in Docker.
  Interactive work uses the KiCad IPC API against the user's open KiCad 10.0.5, so the user can
  follow along. This reverses the old "never edit while KiCad is open" rule (fnd-06, fnd-07).
- IPC edits are one undoable commit each, and the agent never saves; the user reviews and saves.
- Analyses read the files headless so reports rebuild without the GUI. IPC is used to show
  (select or highlight) what is being discussed.
- If an edit IPC cannot do is needed while KiCad is open, the agent stops and asks the user to
  close it.
- Analysis tools: prefer validated industry or vendor tools. The repo's own code is used only
  where none fits, and only with a downloaded source checked against the file and a test that
  reproduces a published worked example. LTspice (through spicelib, under Wine) runs ADI models
  and mixed ADI+TI circuits; ngspice runs TI-only circuits (fnd-05 amendment).
- Full-wave EM for 3D structures (SMA launch, vias, coupler, balun traces, isolation): the user's
  CST Studio Suite Learning Edition where it applies, run by the user on their Windows machine
  from a checklist the agent prepares. openEMS is the open, repeatable fallback and cross-check in
  `fmcw3-sim`, and takes over where a model exceeds the Learning Edition's size limits. CST
  results enter the repo as exported `.s2p` files recorded with `friday result write`. A file too
  large for git is kept outside the repo, with its location and sha256 in the sources manifest.

## Log
