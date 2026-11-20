# KiCad IPC API (fnd-06)

Interactive work goes through the KiCad IPC API, so you can follow along in your own KiCad
window while the agent selects or edits things. Batch work (ERC, DRC, exports, report builds)
stays on `kicad-cli` in Docker (`./run`).

## Setup

- **KiCad 10.0.5** on the host. Turn on the API server in **Preferences → Plugins → Enable
  KiCad API**. It is on in this setup: `~/.config/kicad/10.0/kicad_common.json` has
  `"api": {"enable_server": true}`.
- **`kicad-python` (`kipy`) 0.8.0**, pinned as the uv dependency group `ipc` in
  `pyproject.toml`. The wheels' API versions, read without installing them:

  | kicad-python | API version |
  |---|---|
  | 0.5.0 | 9.0.5 |
  | 0.6.0 | 9.0.8 |
  | 0.7.1 | 10.0.1 |
  | 0.8.0 | 10.0.6 |

  `kipy.check_version` refuses a KiCad *newer* than the library's API. So 0.8.0 accepts 10.0.5,
  and 0.7.1 would refuse it. A KiCad upgrade to 10.0.8 (the PPA's current build) would be refused
  by 0.8.0, and it would also diverge from the Docker image pinned at 10.0.5.
- **Native only.** The API socket belongs to the GUI on the host, so run the client with
  `./run --native`, never in Docker.

## Commands

`tools/kicad_ipc.py` (run as `./run --native tools/kicad_ipc.py <command>`):

- **`status [PROJECT]`** prints:
  - `ipc` when KiCad has the project open (default `kicad/fmcw3.kicad_pro`);
  - `closed` when no KiCad process runs;
  - `other` when KiCad runs without this project or the API does not answer.
- **`show --refs R... --nets N... [--pcb]`** selects those items in the PCB Editor, so you can see
  what is being discussed.
- **`set-fields CSV [--dry-run]`** sets schematic symbol fields as one commit and never saves. It is
  for KiCad 11. On KiCad 10 it refuses, including `--dry-run`, because reading symbols also needs
  the schematic API (see below).
- Any future board edit goes through `begin_board_commit()` in the tool, which refuses while the
  Schematic Editor is open.

The tool never calls `save`, `save_as` or `revert`: you save. Before any edit it refuses when the
Schematic Editor is open, because KiCad freezes otherwise (see below).

## What works on KiCad 10.0.5 (live trial, 2026-11-20)

The trial ran on a scratch copy, `runs/fnd-06/scratch/`, with you watching. Each operation ran
as its own command with a timeout.

| Operation | Editor | PCB Editor only | Schematic Editor also open |
|---|---|---|---|
| `status`, ping, version | both | works | works |
| Select footprints and nets (`show --pcb`: U30, 28 items of `/ADF_DATA`) | board | works | works |
| Read geometry (382 footprints in 0.03 s; `/LO` 17 tracks, 29.35 mm, 0.17 and 0.23 mm widths) | board | works | works |
| Empty commit, dropped and pushed | board | works (0.00 s) | not tested separately |
| Edit a board text in a commit; Ctrl+Z undoes it in one step | board | **works** (0.01 s), confirmed by you | not tested |
| Edit a footprint field (R13 Value) in a commit | board | **works** (0.02 s) | **KiCad freezes** at `begin_commit` (timed out), then quits; seen twice |
| List the open schematic | schematic | works | works |
| Read schematic items or selection | schematic | n/a | **no route**: KiCad 10.0.5 answers `no handler available for request of type kiapi.common.commands.GetItems` (and `GetSelection`) |
| `kipy` schematic module | schematic | n/a | **fails to import**: `cannot import name 'PageSettings' from 'kipy.common_types'`. 0.8.0's schematic module targets KiCad 11 |
| Headless (no GUI) | either | no route: the API server is part of the running GUI | no route |

## Rules that follow (KiCad 10)

1. **Showing and reading** through IPC work with both editors open. Use them so you can follow
   along.
2. **Live edits are board-only**, and only while the **Schematic Editor is closed**. The tool
   checks this and refuses rather than freezing KiCad. Each edit is one undoable commit, never
   saved by the agent.
3. **Schematic changes**, such as par-04's part-number fields, stay file-level, with KiCad closed,
   until KiCad 11 brings the schematic API.
4. The freeze with the Schematic Editor open looks like a KiCad bug: an API call hangs instead of
   returning an error. It is worth reporting upstream with the steps above.
