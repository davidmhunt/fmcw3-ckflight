# par-12: Apply the par-03 part changes to the 2-RX schematic (L5-L7, Y2 and R19 first)
Status: approved
Goal: parts
Node: any
Deliverable: code
Accept: user
Verify: ./run checks/run_checks.sh && ./run checks/run_checks.sh --project kicad-1rx && ./run parts/bom.py --offline --check && ./run uv run pytest tests/test_par03_changes.py -q
Hardware: none

## Goal
`kicad/` carries the part changes the user chose in par-03 that are more than field edits, so the
user can update the 2-RX PCB. par-04 writes fields only. The changes known today, all chosen by the
user on 2026-11-23 for both boards:
- L5-L7: the Coilank APS0650M330A (33 uH, 7.7 x 6.6 mm, JLC C47327223) in place of the
  SRR6040A-330M (new footprint).
- Y2: the Epson TG2520SMN 40 MHz clipped-sine TCXO, X1G0054210307 (JLC C3007519), in place of the
  ECS-TXO-32CSMV-400. The ECS part is 3.2 x 2.5 mm but the footprint is the 2.5 x 2.0 mm ECS
  2520MV; the Epson part fits that footprint, so the footprint stays (value and fields change).
- R19 (Y2 output to U6 FIN): 0 ohm becomes a 10 nF 0402 DC-cut capacitor, as Epson asks
  (epson-tg2520smn-datasheet p.1: external DC-cut capacitor, 0.01 uF min) and as the upstream note
  on the `clock` sheet offers ("Place 10nF cap or 0 ohm resistor").
- U21: the TI TPS7A4901DGNR (JLC C16430), adjustable, in place of the fixed 10 V LP2985A-10DBVR
  (chosen 2026-11-23, both boards, "if possible"; the fallback in `docs/par-03-choices.md` goes
  back to the user if step 5 shows it cannot fit).
It holds when every netlist difference from the par-04 state is a row of `parts/par03_changes.csv`,
the new footprint matches the datasheet land pattern, and ERC has no error type above the baseline.
(Y2 and R19 amended 2026-11-23; U21 amended 2026-11-24.)

## Steps
1. Preconditions. Stop with `blocked` if par-03 is not accepted, par-04 is not done, or par-11 does
   not have `aps0650_ok == 1`. Run `./run --native tools/kicad_ipc.py status` and
   `status --project kicad-1rx`; if either does not print `closed`, stop and ask the user to close
   KiCad.
2. `parts/par03_changes.csv`: one row per ref for every par-03 choice the user accepted that changes
   a symbol, value or footprint (read the accept note in the par-03 Log). Columns as
   `parts/rx1_changes.csv`. Today that is:
   - L5, L6, L7: footprint and fields;
   - Y2: value, `Datasheet` (the Epson sheet), `Description` (clipped-sine TCXO) and part fields;
     footprint unchanged;
   - R19: the resistor symbol becomes a capacitor (`Device:C`), value 10n, X7R, 0402 footprint
     unchanged, a JLC Basic 10 nF 0402 part (`LCSC`, `MPN`). Keep the symbol's UUID so Update PCB
     keeps the footprint where it is. The reference becomes the next free C number; record the
     new reference in the row and in `docs/board-changes.md`.
   - U21: symbol for the TPS7A4901 (pins per ti-tps7a49-datasheet p.4: 1 OUT, 2 FB, 3 NC, 4 GND,
     5 EN, 6 NR/SS, 7 DNC, 8 IN, 9 PowerPAD), footprint
     `Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm_ThermalVias` (checked against p.34 and
     p.37). Nets: IN and EN on /power/12V, OUT on /10V, GND and the pad on GND, NR/SS on C95 (10 nF,
     now CNR/SS), pin 7 a no-connect flag, pin 3 to GND. New parts, next free references, 0402,
     JLC Basic where one exists: R1 OUT to FB and R2 FB to GND, 1 % E96, R2 <= 237 k (p.5), divider
     current >= 5 uA (p.14), nominal output within 1 % of 10 V with VFB 1.185 V (p.6), for example
     165 k and 22.1 k (10.03 V); CFF 10 nF X7R from OUT to FB (p.14-15). Keep the existing input and
     output capacitors.
   Add any others the accept note names.
3. Package scan, report only: for every placed part on both boards, compare the package size in
   the JLC database row of its LCSC number (or the datasheet when there is no JLC row) with its
   footprint's body size, and list each mismatch in the Log and in the step 8 summary. Y2 was such
   a mismatch that the rx1-02 stock list did not catch. Fix nothing here; a new mismatch goes back
   to the user as a choice.
4. Footprint `APS0650` in the project footprint library of `kicad/` and of `kicad-1rx/` (the same
   file content in both), from the land pattern in coilank-aps1040m330a-datasheet p.1 (the APS
   series sheet; APS0650 row: F 8.4, G 3.5, H 3.6 mm, body A 6.6, B 7.7 max, C 5.0 max). Pads
   along Y with pad 1 at -Y, as the current `fmcw3:SRR6040A`, so Update PCB keeps the
   orientation. Courtyard 0.25 mm around the larger of body and pads; silk and fab outlines on
   the body.
5. Fit check, headless, on both boards:
   - place the new L5-L7 footprint at each current position and rotation and report the clearance
     to the board edge and to every neighbouring courtyard, and the pad overlap with the current
     copper and zones;
   - Y2: compare the Epson recommended land pattern (epson-tg2520smn-datasheet p.14: pads
     0.8 x 1.0 mm) and its terminal positions with the existing ECS 2520MV pads, and report whether
     every terminal lands fully on its pad.
   - U21: place the HVSSOP-8 footprint at U21's position in both orientations (leads along X and
     along Y) and report the courtyard clearance to every neighbour (C85, C88, C89, C95, C98,
     C102, U7, U24 today), the top-side room for R1, R2 and CFF, and which neighbour would have to
     move and by how much. TI wants every capacitor on the regulator's side, close, with no vias
     (ti-tps7a49-datasheet p.19). If it cannot fit without moving more than neighbouring passives,
     stop with `blocked` and put the fallback in `docs/par-03-choices.md` to the user.
   Report any overlap or shortfall; do not move parts (placement is the user's).
6. Apply in `kicad/` only: the rows of step 2, with fields `MPN`, `Manufacturer`, `LCSC` and
   `DigiKey` (DigiKey: say if none). `kicad-1rx/` gets the same changes in rx1-03.
7. `tests/test_par03_changes.py`: export the netlist headless and check that every difference from
   the par-04 netlist is a row of `parts/par03_changes.csv`, every row is present, R19's
   replacement is a capacitor on the same two nets (`Net-(Y2-OUT)`, `Net-(U6-FIN)`), and the
   APS0650 footprint's pads match the datasheet numbers of step 4, U21's pins sit on the nets of
   step 2 (pin 7 on no net), and the R1/R2 values give 10 V within 1 % at VFB 1.185 V.
8. ERC on `kicad/`; explain or fix any new error type. Add or update the `docs/board-changes.md`
   rows for every row of step 2 (status `applied (<commit>)`, the evidence, the par-11 load result
   for L5-L7, the fit check, and that the Y2 and R19 change has no simulation: the 10 nF
   capacitor is about 0.4 ohm at 40 MHz and its high-pass corner with the 10 kohm load is about
   1.6 kHz).
9. Ask the user to open `kicad/` and run Update PCB from Schematic, then check the step 5 fit and
   reconnect the L5-L7 pads (the zones refill). Placement and routing are theirs.

## Review
- Open `kicad/` sheet `power`: L5-L7 footprint and fields; U21 (TPS7A4901), its divider, CFF,
  C95 on NR/SS and the no-connect on pin 7.
- Open `kicad/` sheet `clock`: Y2 value and fields, and R19's replacement capacitor between Y2 OUT
  and U6 FIN.
- Open the footprint `APS0650` in the footprint editor and compare its pads with the datasheet p.1.
- Read the step 3 package scan, the step 5 fit check and the netlist-test result in the Log.

## Out of scope
- Writing `kicad-1rx/` schematics (rx1-03); only the shared footprint file is written there.
- Placement and routing (the user).
- Changes the user did not accept in par-03, including fixes for new package mismatches.

## Rules
- Write `kicad/` and `kicad-1rx/` files only right after `status` (with and without
  `--project kicad-1rx`) prints `closed`.
- Only the changes in `parts/par03_changes.csv`; no other symbol, value, footprint, wire or
  position change.

## Allowed commands
- `./run *`

## Log
