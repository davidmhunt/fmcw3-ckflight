# par-14: Repeatable parts-availability check and shortage report, both boards
Status: awaiting review
Goal: parts
Node: any
Deliverable: slides
Accept: user
Verify: ./run uv run pytest tests/test_availability_report.py -q && ./run parts/availability_report.py --offline --check && ./run tools/build_report.py analysis/14_parts_availability --check && ./run uv run pytest tests/test_manual.py -q
Hardware: none

## Goal
One command, runnable any day, that checks the stock of every part on both boards against what
the build needs and flags shortages, and a short report of the result. It holds when
`./run parts/availability_report.py --refresh` followed by the report build gives a dated
snapshot and a deck that lists every short or thin line first, with the action for each, and
what changed since the previous snapshot. (Added 2026-11-24 at the user's request.)

## Steps
1. Preconditions: par-13 done (it creates `parts/final_parts.csv` and `parts/inventory.csv`).
2. `parts/availability_report.py [--refresh] [--offline] [--boards N] [--spares N] [--check]`.
   Reads `parts/final_parts.csv` (fitted rows only) and `parts/inventory.csv`; reuses
   `parts/check_jlc.py` (the JLC database; `--refresh` downloads a fresh copy) and
   `parts/check_digikey.py` (DigiKey; `--offline` uses the cache). Need per line = refs per board x
   `board_quantity` of the target set (or `--boards`), plus spares (default: 2 for parts not in the
   JLC Basic library). For each line, by route:
   - `jlc-stock`: JLC stock against need; `jlc-library`: inventory first, then JLC stock;
   - `jlc-sourcing` and `hand-solder`: DigiKey stock against need (the JLC sourcing service buys
     from distributors);
   and a status: `short` (cannot cover the need), `thin` (covers it with less than 3 times the
   need left), `ok`, or `unknown` (no data). It always notes that the JLC database is a daily
   snapshot that can lag the live site, so `short` and `thin` JLC lines are to be checked on the
   JLC page (pre-order status is not in the database).
   For every `short` or `thin` line it prints the fallback from `parts/final_parts.csv`.
3. Output, never overwriting a previous run: `parts/out/availability/<YYYY-MM-DD>/` with
   `lines.csv`, `summary.json` (counts by status and board, the JLC database date) and a
   provenance note (command, database date, DigiKey cache or live). A second run the same day
   gets a `-2` suffix. `--check` exits 1 on a malformed input row or a line with no data source.
   Diff against the latest earlier snapshot: lines whose status or stock changed.
4. `analysis/14_parts_availability/` (`writeup.md`, `deck.yaml`, `figures.py`) builds from the
   latest snapshot: title with the snapshot date and database date; status counts per board;
   short lines, then thin lines, each with need, stock, inventory, route and fallback; changes
   since the last snapshot; the sourced and hand-solder lines with DigiKey stock. No more than
   10 slides. Running it again after a new snapshot gives the new report.
5. `tests/test_availability_report.py`: on fixture JLC, DigiKey and inventory data, the need
   arithmetic, inventory taken first for `jlc-library`, each status boundary, the snapshot
   naming (no overwrite, `-2` suffix), the diff, and the `--check` failures.
6. `MANUAL.md`: the command, the snapshot path, how to rerun the report, and the lag note.
   `parts/README.md`: `final_parts.csv`, `inventory.csv` and the snapshot folders.
7. Run it once with `--refresh` for the first snapshot, build the report, and record
   `friday result write par-14 --metric short=<n> --metric thin=<n> --file
   parts/out/availability/<date>/summary.json`.

## Acceptance
- One command produces a dated snapshot without overwriting an earlier one, and the report
  rebuilds from it.
- Every fitted line on both boards appears with need, stock, inventory, route and status; short
  and thin lines come first with their fallback.
- The report shows what changed since the previous snapshot and states the JLC database date and
  its lag.
- The deck has no more than 10 slides.

## Review
- Open `reports/14_parts_availability_ppt.pdf`: the short and thin lines, and whether the
  actions make sense against what you see on the JLC and DigiKey pages.
- Run `./run parts/availability_report.py --refresh` yourself once and rebuild the report.

## Out of scope
- Buying, quoting or uploading anything (the user).
- Changing part choices: a short line goes back to the user with its fallback.

## Rules
- The agent never logs in, uploads, quotes or orders on DigiKey or JLCPCB.
- Never read `.env` into output.
- Snapshots are new folders, never edits of an earlier one.
- Never commit `reports/*.pdf` or `*.pptx`.

## Allowed commands
- `./run *`
- `friday result write par-14 *`

## Log

### 2026-11-25
Commits:
- 4113245 par-14 step 2: parts/availability_report.py, need against JLC/DigiKey/inventory stock with dated snapshots
- 0bc3796 par-14 step 4: analysis/14_parts_availability, report and deck built from the latest availability snapshot
- 0411192 par-14 step 5: tests/test_availability_report.py, need, inventory first, status boundaries, snapshot naming, diff, --check failures
- a7471cd par-14 step 6: MANUAL and parts/README for the availability report, snapshots, final_parts and inventory
- 1def7ed par-14 step 7: first availability snapshot 2026-11-25 (--refresh) and rebuilt deck
- 3c63a96 par-14: --check validates inputs only and writes no snapshot
Notes:
- step 1: preconditions met. parts/final_parts.csv (214 rows per par-13 step 2) and parts/inventory.csv (3 rows: ADL5802, YAT-3A+, QPA9501) are committed and clean; par-13 results recorded (69cdba7). No tracked files changed.
Verify: Verify passed: ./run uv run pytest tests/test_availability_report.py -q && ./run parts/availability_report.py --offline --check && ./run tools/build_report.py analysis/14_parts_availability --check && ./run uv run pytest tests/test_manual.py -q
Independent review: gaps fixed in second review: 1. parts/availability_report.py:362-394 (main), together with the Verify line in docs/directives/par-14.md:7: '--check' only adds an exit-1 condition. On good input it still writes a full dated snapshot. So every run of this directive's Verify ('./run parts/availability_report.py --offline --check') adds another snapshot folder made from cached DigiKey data only, and that folder becomes the 'latest snapshot' the report is built from and diffed against. The PDF/PPTX the user is told to open under ## Review now come from that Verify run, not from the recorded '--refresh' snapshot. The tracked, generated deck.yaml is also left modified after every Verify. (evidence: Untracked parts/out/availability/2026-11-25-2/provenance.md reads 'command: parts/availability_report.py --offline --check', 'DigiKey: cache only', 'previous snapshot: 2026-11-25'. git status shows 'M analysis/14_parts_availability/deck.yaml', whose title is now 'Parts availability 2026-11-25-2' with note 'DigiKey: cache only'. The committed version (1def7ed) says 2026-11-25 with live DigiKey. results/par-14.json records the 2026-11-25 snapshot.)
