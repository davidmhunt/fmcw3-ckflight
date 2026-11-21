# fnd-07: Switch the KiCad editing rules to IPC-when-open
Status: done
Goal: foundation
Node: any
Deliverable: code
Verify: friday check --all && ./run uv run pytest tests -q
Hardware: none

## Goal
The repo rules match how the user now works. When the project is open in KiCad, the agent changes
it only through the IPC API and the user saves. When it is closed, the agent makes file-level
edits. Batch work runs through `kicad-cli` in Docker. It holds when `CLAUDE.md` and
`.claude/friday.json` state these rules and the old "never edit while open" rule is gone.

## Steps
1. In `.claude/friday.json` `rules` and in `CLAUDE.md`, replace the rule "Never edit
   kicad/*.kicad_sch or kicad/*.kicad_pcb while the user has the project open in KiCad" with:
   - Before changing anything under `kicad/`, run `./run --native tools/kicad_ipc.py status`.
     `closed`: file-level edits are allowed. `other`: stop and ask the user. `ipc`:
     - board edits go only through `tools/kicad_ipc.py` (IPC), as one undoable commit, never
       saving, and only while the Schematic Editor is closed (the tool refuses otherwise; KiCad
       10 freezes); the user reviews in the GUI and saves;
     - schematic edits are never live on KiCad 10 (no schematic API until KiCad 11).
     (Amended after the fnd-06 live trial; see `docs/kicad-ipc.md`.)
   - Never write `kicad/*.kicad_sch` or `kicad/*.kicad_pcb` directly while KiCad has the project
     open.
   - If an edit is needed that IPC cannot do while the project is open (any schematic change, or
     a board edit while the user needs the Schematic Editor open), stop and ask the user to close
     KiCad, or just the Schematic Editor; after the edit, ask them to reopen it.
   - Batch operations (ERC, DRC, exports, report builds) use `kicad-cli` through `./run`. Analyses
     read the files headless so reports rebuild without the GUI. When the project is open, use
     `tools/kicad_ipc.py show` to select what is being discussed so the user can follow along.
2. Update the matching lines in `README.md` and `docs/setup.md`, and the CLAUDE.md "Division of
   labour" section: the agent may make written-down edits live through IPC while the user watches,
   and design decisions stay the user's.
3. `tests/test_rules.py`: `.claude/friday.json` parses, its `rules` and `CLAUDE.md` no longer
   contain "while the user has the project open", and both mention `tools/kicad_ipc.py status`.
   This is a test, not a grep in Verify, because the `bash_file_io` hook denies a Verify line that
   reads files (friday issue #33).

## Out of scope
- Changes to `tools/kicad_ipc.py` (fnd-06).
- Editing other directives.

## Log

### 2026-11-20
Commits:
- f44b735 fnd-07 step 1: replace never-edit-while-open rule with IPC-when-open rules
- 5200950 fnd-07 step 2: README, setup and Division of labour describe IPC-when-open edits
- 39f30af fnd-07 step 3: test_rules checks friday.json and CLAUDE.md carry the IPC-when-open rules
Verify: Verify passed: friday check --all && ./run uv run pytest tests -q
Independent review: no gaps
