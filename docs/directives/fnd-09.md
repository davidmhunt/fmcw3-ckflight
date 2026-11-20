# fnd-09: Workspace manual (MANUAL.md) and a rule that keeps it current
Status: awaiting review
Goal: foundation
Node: any
Deliverable: doc
Accept: user
Verify: ./run uv run pytest tests/test_manual.py -q && ./run uv run pytest tests -q
Hardware: none

## Goal
Someone new to this workspace can set it up and use every tool from one top-level file,
`MANUAL.md`, without hunting through subfolders. It holds when the manual covers every `./run`
mode, every tool and every software download, a test fails when one is missing, and a repo
rule makes later directives keep it current.

## Steps
1. Write `MANUAL.md` at the repo root, linked from `README.md`. It covers:
   - setup (Docker, native KiCad 10.0.5, uv), pointing to `docs/setup.md` for detail;
   - every `./run` mode (`--docker`, `--native`, `--sim`, `--sim-gui` with `SIM_GUI_DPI`), with
     one example each;
   - each tool, what it is for and how to run it: `kicad-cli` and `checks/run_checks.sh`, the
     report pipeline (`tools/build_report.py`, `tools/build_all.py`, target sets), KiCad IPC
     (`tools/kicad_ipc.py` and its KiCad 10 limits), LTspice through spicelib and in the GUI,
     ngspice, openEMS, scikit-rf, and PSpice for TI with its trial result;
   - every software download, as a table built from `software/manifest.yaml`: what it is, link,
     whether it needs an account, where to save it (`software/files/`), and how to pin its hash
     with `tools/fetch_sources.py --record`;
   - tools run elsewhere (CST on the user's Windows machine, ADIsimPLL, ADIsimRF, Saturn,
     WEBENCH, the JLCPCB calculator), with links to `docs/gui-tool-checklists.md`;
   - the datasheet, model and reference pipeline (the three manifests, `--check`, and the
     rule that references are checked against the downloaded file);
   - how work is planned and run (friday goals and directives, `docs/goals/`, the review and
     accept flow), in a few lines.

   Write it in the main session (Claude Code refuses subagent Write of report-style docs), or
   with Edit if the file exists.
2. `tests/test_manual.py`. It checks:
   - every `./run` mode in the `run` script's usage text appears in `MANUAL.md`;
   - every id in `software/manifest.yaml` appears in the downloads table;
   - every `tools/*.py` with a command-line entry point is named;
   - every relative link in the manual resolves.
3. Add a repo rule to `.claude/friday.json` and `CLAUDE.md`: a directive that adds or changes a
   tool, a software download or a `./run` mode updates `MANUAL.md` in the same directive, and
   the reviewer treats a stale manual as a gap.

## Acceptance
- `MANUAL.md` exists at the root and `README.md` links to it.
- Every `./run` mode, every `software/manifest.yaml` entry and every command-line tool in
  `tools/` appears in it, and `tests/test_manual.py` enforces this.
- Each externally run tool names its link and the checklist that goes with it.
- The repo rule is in both `.claude/friday.json` and `CLAUDE.md`.

## Review
- Read `MANUAL.md` as if you were new to the repo: could you set up and run each tool from it.

## Out of scope
- Rewriting the detailed docs it links to (`docs/setup.md`, `docs/analysis-tools.md`,
  `docs/kicad-ipc.md`, `docs/gui-tool-checklists.md`).

## Log

### 2026-11-20
Commits:
- 1304354 fnd-09: MANUAL.md workspace manual (step 1), linked from README.md
- 73834d5 fnd-09: tests/test_manual.py checks MANUAL.md coverage (step 2)
- 7c4aa98 fnd-09: repo rule to keep MANUAL.md current (step 3)
- 92c8f69 fnd-09: MANUAL.md section 7 names each tool's link and checklist
Verify: Verify passed: ./run uv run pytest tests/test_manual.py -q && ./run uv run pytest tests -q
Independent review: gaps fixed in second review: 1. /home/david/Documents/pcb_work/fmcw3-ckflight/MANUAL.md:121-128 (section 7, 'Tools you run elsewhere'): Acceptance bullet 3 requires each externally run tool to name its link. Only the JLCPCB row has one. CST Studio Suite, ADIsimPLL, ADIsimRF, Saturn PCB Toolkit and TI WEBENCH have only a 'Where' label such as 'Windows (ADI)' or 'browser, TI account'. Links were available in the repo and were not used: Saturn https://saturnpcb.com/saturn-pcb-toolkit/ (docs/gui-tool-checklists.md:54, docs/analysis-tools.md:142), WEBENCH webench.ti.com (docs/analysis-tools.md:148), and the ADI product pages (docs/analysis-tools.md:140-141). (evidence: MANUAL.md table rows 123-127 have no URL. Only row 128 contains https://jlcpcb.com/pcb-impedance-calculator.) 2. /home/david/Documents/pcb_work/fmcw3-ckflight/MANUAL.md:117-119 and 121-128: Acceptance bullet 3 also requires each external tool to name the checklist that goes with it. The manual gives one blanket link to docs/gui-tool-checklists.md and says every tool here is used 'from a checklist'. No row points to its own checklist section. That file only has checklists for ADIsimPLL, ADIsimRF, Saturn and JLCPCB. CST Studio Suite and TI WEBENCH have none, so the manual's claim is wrong for those two and it does not say they have no checklist yet. (evidence: The headings in docs/gui-tool-checklists.md are 'ADIsimPLL', 'ADIsimRF', 'Saturn PCB Toolkit' and 'JLCPCB impedance calculator' (lines 23, 40, 52, 64). Neither CST nor WEBENCH appears in it. MANUAL.md:117-119 says 'used by you ... from a checklist that says what to enter'.) 3. Acceptance: not met: Each externally run tool names its link and the checklist that goes with it. (evidence: In MANUAL.md section 7, only the JLCPCB row has a link. CST, ADIsimPLL, ADIsimRF, Saturn and WEBENCH have none. The checklist is one blanket link to docs/gui-tool-checklists.md, which has no checklist for CST or WEBENCH.)
