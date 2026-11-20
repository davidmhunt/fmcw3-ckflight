# fnd-06: KiCad IPC client and a live trial with the user watching
Status: approved
Goal: foundation
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests/test_kicad_ipc.py -q && friday result check fnd-06 --require 'trial_complete == 1' --files
Hardware: none

## Goal
The agent can work in the user's open KiCad 10.0.5 session through the IPC API: it can tell
whether the project is open, select and highlight parts and nets so the user can follow along,
and change schematic symbol fields as one undoable commit that the user then saves. It holds when
the unit tests pass and a live trial on a scratch copy of the project, watched by the user, is
recorded with what works and what does not.

## Steps
1. Version pin. For the `kicad-python` (`kipy`) releases on PyPI, read each wheel's
   `kipy/kicad_api_version.py` without installing it; pick the release that matches KiCad
   10.0.5 (`kicad-cli version`). Release 0.8.0 is built for API 10.0.6, so check that it accepts
   10.0.5 before choosing it. Add it as a uv dependency group `ipc` in `pyproject.toml` and
   `uv.lock`. It runs natively (`./run --native`), because the API socket belongs to the GUI on
   the host.
2. `tools/kicad_ipc.py` (library plus CLI). `status [PROJECT]` prints `ipc` when a KiCad with the
   API server has this project open (default `kicad/fmcw3.kicad_pro`; match on the open
   documents' paths), `closed` when no KiCad process is running, and `other` when KiCad runs
   without this project or the API does not answer. `show --refs R... --nets N... [--sch|--pcb]`
   selects those items in the editors. `set-fields CSV [--dry-run]` sets symbol fields
   (columns: ref, field, value) in the open schematic in one commit (`begin_commit` /
   `push_commit`) and prints a diff per ref. It never calls `save`, `save_as` or `revert`. It
   refuses with a clear message on an API version mismatch.
3. `tests/test_kicad_ipc.py` with a fake client, so no KiCad is needed and the tests run in
   Docker: status for each case; set-fields makes exactly one commit and no save; dry-run changes
   nothing; show maps refs and nets to item ids; version-mismatch refusal.
4. Live trial, with the user. Copy `kicad/` to `runs/fnd-06/scratch/` (untracked). If
   `./run --native tools/kicad_ipc.py status runs/fnd-06/scratch/fmcw3.kicad_pro` is not `ipc`,
   return needs_user asking the user to open that scratch project in KiCad, with both the
   schematic and board editors open. Then, on the scratch project:
   - `show` U30 and net `/ADF_DATA` in the schematic and the board;
   - read the track widths of one RF net from the board;
   - `set-fields` a test field `IPC_TEST=1` on R13, then undo it with `drop_commit` or by asking
     the user to press Ctrl+Z;
   - check whether any IPC route works without the GUI (headless).
   Ask the user to confirm what they saw. Record it with `friday result write fnd-06 --metric
   trial_complete=1 --metric sch_select=<0|1> --metric pcb_select=<0|1> --metric
   sch_field_edit=<0|1> --metric pcb_read=<0|1> --metric headless=<0|1> --file
   docs/kicad-ipc.md`. Do this after step 5 writes that file.
5. `docs/kicad-ipc.md`: how to enable the API server (Preferences, Plugins), the pinned
   `kicad-python` and why it runs natively, the `tools/kicad_ipc.py` commands, and a capability
   table from step 4 (operation, schematic or board, works yes/no, error text). Point to it from
   `docs/setup.md`.

## Rules
- Never call `save`, `save_as` or `revert` on a document through IPC; the user saves.
- In this directive, live IPC operations target only `runs/fnd-06/scratch/`, never `kicad/`.

## Review
- During step 4, watch KiCad: U30 and `/ADF_DATA` are selected in both editors, and the test
  field appears on R13 and is undone.
- Read the capability table in `docs/kicad-ipc.md`: is anything you want to do live missing.

## Out of scope
- Changing the rules in `CLAUDE.md` and `.claude/friday.json` (fnd-07).
- Any edit to `kicad/`.
- Running the KiCad GUI in Docker.

## Allowed commands
- `./run *`
- `friday result write fnd-06 *`

## Log
