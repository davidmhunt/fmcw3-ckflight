# foundation: Clean repo layout, repeatable environment and report pipeline
Status: blocked: fnd-04
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
- Reports: markdown source, built PDF, and a `.pptx` deck per analysis; built files go through Git LFS.
- System targets (range, chirp, TX power, antennas) are parameters in `analysis/targets/*.yaml`
  so every analysis can be re-run for a new target set.
- The user has Linux only: analysis tools must run natively, in Docker, or under Wine.

## Log
