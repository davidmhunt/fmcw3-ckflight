# par-09: JLC sourcing plan for every line JLCPCB cannot place today
Status: approved
Goal: parts
Node: any
Deliverable: slides
Accept: user
Verify: ./run tools/build_report.py analysis/03_sourcing --check && ./run uv run python parts/check_decisions.py
Hardware: none

## Goal
The user knows, before ordering, how each part JLCPCB cannot place today gets onto the board:
- a JLC-stocked part;
- a JLC-stocked substitute, with the analysis or layout work it needs;
- JLC's parts-sourcing service;
- consignment;
- hand soldering.

It holds when every such line has its routes ranked (JLC-first, by the goal rule), each with its
cost, lead time and the work it causes, and the `03_sourcing` report and deck build. (Added
2026-11-21 at the user's request.)

## Steps
1. Refresh the JLC parts database (`./run parts/check_jlc.py --refresh`) and rerun
   `./run parts/bom.py` so stock is current. Record the database date in the Log.
2. List every line whose verdict is not "JLC assemble", plus every line whose JLC stock is below
   twice the need. Include the user-choice options that change the verdict (U30 I grade, U14
   QPA9501). Today this covers:
   - U8 LTC2292 (ADC);
   - U26-U28 (baluns);
   - U45 LT6232 (op-amp);
   - U21 LP2985A-10 (LDO);
   - P1, P2 and U15 (SMA);
   - U12 PAT1220 3 dB (stock 5 for a need of 3);
   - L5-L7 (inductors);
   - the lines with no part number yet: D1-D7, CON2 and J2.
3. For each line, find JLC-stocked substitutes through the JLC database and the DigiKey API. Read
   every candidate's datasheet through the sources pipeline (never from memory) and classify it:
   - **drop-in**: same footprint and pinout, ratings at least as good, so only the fields change;
   - **footprint change**: a layout change for the user;
   - **design change**: needs an analysis (name it: rf-01, sim-01, sim-02) and/or FPGA or
     firmware changes.

   For the ADC, check the LTC2292 pin-compatible family first (LTC2290-LTC2299). A 2026-11-21
   check found the family at stock 0 at JLC and no pin-compatible dual ADC in stock. State the
   redesign scope of any non-pin-compatible ADC: footprint, FPGA bank and pins, data interface,
   firmware.
4. JLC's parts-sourcing service (buying parts from other distributors into the user's JLC parts
   library): find JLC's current documentation, download it into `docs/references/manifest.yaml`
   and check it against the file. Record what it covers, its fees and lead time, and whether it
   applies to each line (for example U8 from DigiKey stock). If the documentation cannot be
   fetched, it becomes a user-fetch row, never a claim from memory.
5. `analysis/03_sourcing/` (`writeup.md`, `deck.yaml`, `figures.py`), report and deck:
   - one table, one row per line, with its routes ranked JLC-first and each route's cost for 3
     boards, lead time, the work it causes and its datasheet evidence;
   - a summary: the lines settled by a decision alone, the lines needing analysis or layout, and
     the lines that must be sourced or consigned;
   - a recommendation, labelled as such.

   Add each proposed substitute to `parts/choices.json` (a choice option), and each proposed or
   recommended change to `docs/board-changes.md`.

## Acceptance
- Every line not assembled by JLC today is in the table with at least two ranked routes, or says
  why only one exists.
- Every substitute cites its datasheet manifest id and page for pinout and ratings.
- The JLC sourcing-service facts cite a downloaded reference, or are marked "for the user to
  confirm".
- The stock figures state the JLC database date and the DigiKey query date.
- The deck has no more than 12 slides; the recommendation is labelled as such.

## Review
- Open `reports/03_sourcing.pptx`. For each line choose its route, and give the choices in the
  note when you accept this directive. Substitutes that need a layout change are yours to make.

## Rules
- The agent never logs in, quotes, uploads or orders at JLCPCB or DigiKey.
- No schematic or layout edit; substitutes reach the schematic only through par-04 after the user
  chooses them.

## Out of scope
- Running the analyses a substitute needs (rf-01, sim-01, sim-02), and choosing parts.

## Allowed commands
- `./run *`

## Log
