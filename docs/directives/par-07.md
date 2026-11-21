# par-07: Replacement candidates for the discontinued TQP5525 power amplifier (U14)
Status: approved
Goal: parts
Node: any
Deliverable: slides
Accept: user
Verify: ./run tools/build_report.py analysis/02_pa --check
Hardware: none

## Goal
The user can choose a replacement for U14, the TQP5525 that Qorvo has discontinued (the user's
report, 2026-11-21, in `parts/decisions.csv`). The options are laid out against the board's own
requirements, and the choice stays with the user. It holds when the `02_pa` report and deck
build. They must show every shortlisted candidate against each requirement, with the datasheet
page for every number.

## Steps
1. Requirements, each with where it came from:
   - Band 5.60 to 5.90 GHz and TX power `tx_power_dbm` (25 dBm), from the `default` target
     set.
   - U14's connections, read headless from the schematic and netlist: supply rail and its
     voltage, which regulator feeds it and that regulator's current limit, enable and detector
     pins, what drives the input and what follows the output.
   - The drive level at U14's input, from the datasheets of the parts before it.
   - The loss between U14 and the antenna SMA.
   - The TQP5525's own figures from `qorvo-tqp5525-datasheet` (4900 to 5925 MHz, 5 V, about
     32 dB gain, QFN-20 4x4), as the baseline.
   - Temperature -40 to 85 C.
   FMCW is a constant-envelope signal, so compare P1dB and Psat at 5.8 GHz, not the WLAN EVM
   power, and say so.
2. Candidate search through the DigiKey Product Information API (RF amplifiers covering 5.6 to
   5.9 GHz with enough output power) and the JLC parts database. Every candidate's datasheet
   goes through the sources pipeline (par-06) and is read from the file; a candidate without a
   datasheet on file is listed "for the user to obtain", never scored from memory. Shortlist
   at most six. Always include the option "buy the remaining TQP5525 stock for this build" with
   current stock.
3. For each candidate:
   - frequency range;
   - gain, P1dB and Psat at 5.8 GHz;
   - supply voltage and current at the target power, and whether the existing rail and
     regulator can supply it;
   - dissipation and thermal pad;
   - package, and whether it fits the TQP5525 footprint and pinout or needs a footprint and
     layout change;
   - lifecycle, DigiKey and JLC stock for 3 boards, and price;
   - the datasheet page for each number.
4. `analysis/02_pa/` (`writeup.md`, `deck.yaml`, `figures.py`): report and deck, with:
   - one requirements slide;
   - one comparison table;
   - one slide per shortlisted candidate;
   - a recommendation labelled as such.
   When the project is open in KiCad, use `tools/kicad_ipc.py show --refs U14` while
   discussing it.

## Acceptance
- Every requirement states its source (target set, schematic net, or datasheet and page).
- Every candidate number cites the datasheet manifest id and page; candidates without a datasheet
  on file are marked "for the user to obtain".
- The table states for each candidate whether it fits the existing U14 footprint and supply.
- The remaining-stock TQP5525 option is included with its current stock.
- The recommendation is labelled as such; no part is changed in the schematic or decisions.csv.
- The deck has no more than 12 slides.

## Review
- Open `reports/02_pa.pptx`. Choose the U14 part, and give the choice in the note when you
  accept this directive. A footprint or rail change it needs is yours to make (U14 and its sheet, named in the report);
  the agent then writes the new part into `parts/decisions.csv` for par-04.

## Out of scope
- Changing the schematic, the footprint or the layout.
- The full RF link budget and antenna (the RF-chain goal).

## Allowed commands
- `./run *`

## Log
