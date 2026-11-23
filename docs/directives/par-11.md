# par-11: Load budget for the three buck rails and the APS0650M330A inductor check
Status: approved
Goal: parts
Node: any
Deliverable: slides
Accept: auto
Verify: ./run tools/build_report.py analysis/12_rail_loads --check && friday result check par-11 --require 'aps0650_ok == 1' --files && ./run uv run pytest tests/test_rail_loads.py -q
Hardware: none

## Goal
A sourced load budget for the 1V0 (U17/L5), 3V8 (U18/L6) and 5V6 (U19/L7) buck rails, on both
boards, that shows whether the APS0650M330A (Coilank, JLC C47327223) holds the real operating
current. The user chose this part for L5-L7 on both boards on 2026-11-23, in place of the
SRR6040A-330M, subject to this check. It holds when every rail's worst-case peak and DC current
is below the limits in step 4, on both boards, and the report shows how each number was reached.

## Steps
1. Per-rail consumer list from the netlists of `kicad/` and `kicad-1rx/` (headless export). Trace
   each buck output through its LDOs to every part it feeds: 1V0 to VCCINT; 3V8 to U20, U23,
   U24, U25 and U39 and their loads; 5V6 to U22 and its loads. An LDO passes its load current
   plus its ground current back to the buck. On the 1-RX board, leave out the receive-chain-2
   DNP parts (`parts/rx1_changes.csv`) and use the AD9237 in place of the LTC2292.
2. Each consumer's current from its datasheet on file (`datasheets/manifest.yaml` id and PDF page
   for every number), typical and maximum. Where a datasheet gives only power, divide by the
   rail voltage and say so. A consumer with no datasheet on file is listed as such, with a stated
   bound and the reason.
3. `[heavy]` The FPGA core (1V0, VCCINT) of the XC7A100T. Heavy because it has no single datasheet
   number: it is static current (DS181) plus dynamic current that depends on the design. Use the
   firmware repo `davidmhunt/fmcw3-ckflight-fw` (read only): its utilization or power report if
   one is committed, else the resource use of the current design. Give a typical case and a
   bounded worst case (say what the bound assumes, for example toggle rate and clock), and note
   that the Vivado power report on the final design replaces this estimate.
4. `analysis/12_rail_loads/`: per rail and board, the DC load, the inductor ripple (ti-lmr51420
   equation for the U17-U19 suffix in `parts/decisions.csv`; if that is unresolved, report both
   500 kHz and 1.1 MHz) with the inductance 20 % low, and the peak = DC + ripple/2. Pass when, on
   both boards:
   - the worst-case peak is at most 60 % of the APS0650M330A Isat (3.53 A typ,
     coilank-aps1040m330a-datasheet, the APS series sheet; the 40 % inductance-drop definition
     on p.1), so at most 2.1 A;
   - the worst-case DC load is at most 2/3 of its Irms (2.32 A, the 40 C rise), so at most
     1.55 A, and at most the LMR51420's 2 A rating;
   - the copper loss at the typical load (DCR 178 mohm max) is listed per rail.
   Also state, without a pass mark, the fault case: the regulator's peak current limit (2.7 / 3.5 /
   5.1 A, ti-lmr51420 p.5) against the Isat, and what hiccup mode does (p.18).
5. `tests/test_rail_loads.py`: the per-rail sums equal the consumer table; the ripple matches the
   datasheet equation on one hand-worked case; the pass marks use the stated Isat and Irms.
6. Report `writeup.md` and `deck.yaml` (consumer table per rail, peak against Isat per rail and
   board, fault case, open items), built with `./run tools/build_report.py analysis/12_rail_loads`.
   Record `friday result write par-11 --set aps0650_ok=<1|0> --set peak_max_a=<A>
   --set dc_max_a=<A> --file reports/12_rail_loads.pdf`. If a rail fails, set `aps0650_ok=0` and
   stop: the inductor choice goes back to the user.
7. Add the result to the L5-L7 rows of `docs/board-changes.md` (both boards): the analysis and its
   numbers.

## Acceptance
- Every rail on both boards has a consumer table, and every current names a manifest id and page,
  or says why it is a bound.
- The VCCINT estimate states its source (firmware report or resource use) and its assumptions.
- The peak and DC load per rail are compared with the APS0650M330A Isat and Irms, with the pass
  marks of step 4, and the fault case is stated.
- The figures regenerate from the scripts in `analysis/12_rail_loads/`.

## Out of scope
- Changing the schematic or the footprint (par-12 for `kicad/`, rx1-03 for `kicad-1rx/`).
- Choosing a different inductor (the user, if this fails).
- Simulating the bucks (the LMR51420 model loads in no engine here; sim-05).

## Rules
- Read only: `kicad/`, `kicad-1rx/` and the firmware repo are read, never written.

## Allowed commands
- `./run *`
- `friday result write par-11 *`

## Log
