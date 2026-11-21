# par-10: Stock watch for hard-to-source parts (ADC first)
Status: approved
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_watch.py -q && ./run parts/watch.py --offline --check
Hardware: none

## Goal
One command tells the user whether a hard-to-source part, or a drop-in for it, can now be
assembled by JLCPCB for `board_quantity` boards. The first such part is the ADC U8 (LTC2292,
JLC stock 0 on 2026-11-21, DigiKey stock 334). The user can then move it from "sourced or
consigned" to "JLC places it" before ordering, with no redesign. It holds when the watch list
covers U8's pin-compatible family plus every line par-09 routes outside JLC, and the tests pass.
(Added 2026-11-21 at the user's request.)

## Steps
1. `parts/watch.csv` (committed): one row per watched MPN, with:
   - the refdes it would fill;
   - why it is watched;
   - whether it is a drop-in, with evidence (datasheet manifest id and page for the pinout).

   Start with U8 and the LTC2292's pin-compatible family (LTC2290-LTC2299, which share the
   QFN-64 pinout), each checked against its datasheet through the sources pipeline; never list a
   part as a drop-in from memory. Add the lines par-09 routes outside JLC, with their candidate
   substitutes.
2. `parts/watch.py [--offline] [--refresh] [--check]`: for each row, prints:
   - JLC stock and library type (JLC parts database, `--refresh` for a fresh copy);
   - DigiKey stock, price and lifecycle (`parts/check_digikey.py`);
   - "JLC can place now" when JLC stock covers the need at `board_quantity`.

   It writes `parts/out/watch.csv`. `--check` exits non-zero on a malformed row or a drop-in row
   without evidence. Tests in `tests/test_watch.py` on fixture database rows and fake DigiKey
   answers.
3. Document it in `MANUAL.md` (parts section) and `parts/README.md`: how to run it before
   ordering, and what a "JLC can place now" line means for the par-09 route of that part.
4. Optional, the user's choice at review: run it on a schedule (for example a daily cloud
   routine that reports changes to the user). Only set up if the user asks; describe the option
   in the Log.

## Rules
- Never print or commit the `.env` keys.
- The agent never quotes, uploads or orders at JLCPCB or DigiKey.

## Out of scope
- Choosing a substitute or changing the schematic (par-09 options, then par-04).

## Allowed commands
- `./run *`

## Log
