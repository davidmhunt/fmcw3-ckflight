---
title: "FMCW3 1-RX board: every change from the 2-RX board, with its evidence and check"
---

# 1. Question

What turns the 2-RX board (`kicad/`) into the 1-RX board (`kicad-1rx/`): U8 as the AD9237BCPZ-40
(LCSC C514275), receive chain 2 not fitted, and every placed line in JLCPCB stock for
{{fact:boards}} boards? For each change: its datasheet evidence, the check that covers it, and
the layout work it causes. Can the board stream raw or decimated samples to the PC with no
hardware change?

# 2. Inputs and assumptions

{{targets}}

- Sources: datasheets in `datasheets/manifest.yaml`, each claim with its manifest id and PDF page
  (for `adi-ad9237-datasheet`, `ftdi-ft2232h-datasheet` and `adi-lt6232-datasheet` the PDF page
  is the printed folio). The LTC2292 figures come from its own sheet,
  `adi-ltc2293-2292-2291-datasheet` (saved by the user 2026-11-22), which replaced the LTC2294 sheet.
- Netlist: `kicad-cli sch export netlist` of `kicad/fmcw3.kicad_sch`, read headless. Nothing under
  `kicad/` or `kicad-1rx/` was written.
- Firmware: `davidmhunt/fmcw3-ckflight-fw` at commit `{{fact:fw_commit}}`, read only.
- JLC stock: parts database dated {{fact:jlc_db}} (`parts/check_jlc.py --refresh`). A line passes with
  stock of at least 3 times its quantity; "thin" means it passes with under twice the need.
- Mixer noise and the RF level plan are not in the ADC analysis (rf-01 has that cascade).
- Nothing is decided here: every option is yours; the recommendations are labelled.

# 3. Method

- Step 2 (pin map and straps): each U8 net of the netlist mapped to an AD9237 pin from Table 6
  (p.8) and Tables 7 to 10, with the straps set so the span (2 V p-p), the output format (twos
  complement) and the OE and PDWN polarity match what the FPGA drives today.
- Step 3 (input analysis): LTspice in `./run --sim` through `adc_input_sim.py` (22 runs): U45 with
  its vendor model (the LTspice LT6231 subcircuit that the LT6232 symbol uses) drives the AD9237
  input load of Table 1 and Figure 35 through the existing network, with the bias from the 1 kohm
  divider. `adc_numbers.py` holds the datasheet constants, rail load, SNR and dynamic range.
- Step 4 (RX2): a walk of the netlist from each antenna port to its ADC channel, with the ADL5802
  channel pairing from `adi-adl5802-datasheet` p.6 (Table 3).
- Step 5 (stock): `stock_lines.py` checks all 87 lines of the 1-RX BOM (the changes applied on
  paper) against the JLC database, and lists JLC-stocked options with their class and check.
- Step 6 (data path): `data_path.py`: rates, the FT2232H limits and the FPGA buffers.
- Step 7: `rx1_changes.py` writes `parts/rx1_changes.csv` and the `rx1-` keys of
  `parts/choices.json` from those results; `figures.py` draws everything below from the same files.

# 4. Findings

## Summary of the changes

{{table:change_summary.csv}}

{{fact:n_changes}} rows in `parts/rx1_changes.csv`: {{fact:n_status_decided}} decided by the
directive, {{fact:n_status_proposed}} proposed by the agent, {{fact:n_status_option}} options that
apply only when you accept the option of the named `rx1-` choice. Each row names its row in
`docs/board-changes.md` (Board column 1-RX) and its covering check.

## Which chain is kept (a correction)

The step 2 notes first read the mixer net labels (IF1, IF2) as the channel letters and concluded
the chains cross; the walk with the ADL5802 pin pairing shows they do not: P1 ends on U8 AINA and
P2 on AINB. So RX1 (P1) is kept with AINA; channel B is removed. What does cross is the bias: the
kept chain's U45 amps A and B have their + inputs on `/ADC_VCMB`, which today the LTC2292 drives
from its channel-B pin. The 1.5 V divider therefore goes on `/ADC_VCMB` (not `/ADC_VCMA`, as the
directive's step 2 text says); the step 3 simulation modelled the identical amps C and D (every
value and footprint pair was checked equal), so its numbers apply to the kept chain unchanged.

## ADC pin map and straps

First the signals, then the straps, references, decoupling and the bias.

{{table:pin_map.csv}}

- Output format: the firmware sign-extends 12 bits as twos complement (`adc.vhd` lines 98 to 100)
  with 12 data pins in the constraints; MODE at 2/3 AVDD is twos complement with DCS on, as today.
  The strap sits at 0.65 AVDD with R91 4.7k and R92 10k; the datasheet gives nominal levels only.
- OE and PDWN: `control.vhd` initialises both to "00" and never assigns anything else (the "11"
  assignments are commented out), so the FPGA holds OE low (outputs enabled) and PDWN low (normal),
  direct connection, no inverter. PDWN's absolute maximum is AVDD + 0.3 V; a 3.3 V high from the
  FPGA is at that limit if a later firmware drives it.
- Firmware (a later goal): the AD9237 is a single channel part. `adc.vhd` and `top_module.vhd`
  use the LTC2292 multiplexed mode (CLKA, CLKB, MUX on the 40 MHz clock); a single-channel build is
  needed.
- Decoupling: the AD9237 asks for 0.1 uF per supply pin group and 0.1 uF with 10 uF recommended
  (p.8, Table 6). The kicad/ netlist and board positions (`supply_decoupling.py`) give what is there.
  AVDD (pins 27, 32) takes the LTC2292 VDD net `/fpga/adc/3V0`: six caps, 100n C24, C27, C223, C224
  and 1u C222, C249, all within 10 mm of U8, no 10u. DRVDD (pin 16) takes `/3V3D`, a shared rail:
  100n C25, C225, C252 are 5.9 to 10.9 mm from U8; the nearest 10u is C106 at 32 mm (a 4.7u, C194, is at 16 mm). So the 100n is
  met by caps that stay, and the 10u is not met: C994 (10u on 3V0) and C995 (10u on 3V3D) are
  proposed, in `rx1_changes.csv` and `docs/board-changes.md`. No simulation covers them; they are
  datasheet values, and placement is yours. No open question is left for rx1-03.
- The input network (R97/R99 49.9 ohm, C163 to C165 100 pF) is kept: it is what the simulation
  covers. The datasheet's own examples use 33 ohm and 15 pF across (p.17), and p.16 says to reduce
  or remove the shunt capacitor for IF undersampling; this board's IF is baseband, so it is left.

## Input simulation: U45 driving the AD9237

{{fact:fs_min_v}} to {{fact:fs_max_v}} V is the U45 output at full scale (2 V p-p differential at
the pins) against an available swing of 0.35 to 2.90 V (`adi-lt6232-datasheet` p.4): margins 0.69 V
below and 0.85 V above. Driven 3 times over full scale the chain clips at {{fact:clip_peak_v}} V peak
differential (9.6 dB over the 1 V span peak), so the ADC over-ranges (OTR) well before U45 clips.

![IF response, today against 1-RX](build/if_response.png)

The IF response is identical in band: -3 dB from 15.8 kHz to 1.26 MHz; the 1-RX load differs by
0.000 dB up to 1 MHz and -0.056 dB at 20 MHz (7 pF per pin against 5 pF behind 15 ohm). The 200 kHz
beat of the target set (100 m, 300 MHz in 1 ms) and the 1 MHz Nyquist of the decimated stream are
both inside the band.

![Swing and common mode](build/swing_cm.png)

Common mode at the pins: {{fact:cm_rx1}} V (today {{fact:cm_today}} V). The output sits IB x R39 = 50
mV above the + input in both cases (5 uA typical bias current, `adi-lt6232-datasheet` p.3). Worst case
(11 uA over temperature, p.5, 1 percent divider tolerance) is 1.60 V, inside the AD9237 range of 0.5 to
2.0 V (`adi-ad9237-datasheet` p.17). Found: clipped pins reach 0.04 to 3.05 V, within the
-0.3 V to AVDD + 0.3 V absolute maximum (p.7) by 0.25 V while 3V0 is up; if 3V3A came up before 3V0, a
pin could exceed it for that time. Not simulated; a note for the review.

![Settling within half a 40 MHz period](build/settling.png)

Settling within 12.5 ns, -1 dBFS sine: {{fact:settle_rx1_1m}} LSB maximum at 1 MHz (today
{{fact:settle_today_1m}}) and {{fact:settle_rx1_200k}} LSB at 200 kHz. Nearly all of it is linear (a
46 ps delay, -0.0004 dB gain); what is left after that fit is 0.04 LSB at 1 MHz against the half-LSB
target of 244 uV. The "reset" bound, where the sampling capacitor is discharged each cycle, gives
{{fact:settle_reset}} LSB. Model limit: the switches are linear, so signal-dependent charge injection is
not modelled (neither datasheet gives it); the switch on-resistance (10 ohm, swept to 50 and 200) and
what the capacitor holds when tracking starts are assumptions.

![3V0 rail, SNR and dynamic range](build/rail_snr.png)

- 3V0 rail (U39 LP5907-3.0, 250 mA, `ti-lp5907-datasheet` p.5): today {{fact:rail_today}} mA
  ({{fact:rail_today_pct}} percent); 1-RX {{fact:rail_rx1}} mA ({{fact:rail_rx1_pct}} percent), bounded at
  {{fact:rail_bound}} mA ({{fact:rail_bound_pct}} percent) with all 180 mW on AVDD. The load drops by
  about 31 mA.
- SNR at 40 MSPS: AD9237-40 {{fact:snr_ad}} dBFS (66.5 dBc at -0.5 dBFS, `adi-ad9237-datasheet` p.4)
  against {{fact:snr_ltc}} dBFS for the LTC2292 (`adi-ltc2293-2292-2291-datasheet` p.3, 5 MHz input):
  {{fact:snr_delta}} dB lower.
- IF dynamic range, full scale to total noise at the pins (U45 stage plus ADC, mixer noise excluded):
  over the full 20 MHz band {{fact:dr_ad_nyq}} dB against {{fact:dr_ltc_nyq}} dB (loss
  {{fact:dr_loss_nyq}} dB); after the firmware's decimation by 20, in 1 MHz, {{fact:dr_ad_band}} dB against
  {{fact:dr_ltc_band}} dB (loss {{fact:dr_loss_band}} dB), because U45's own noise is then comparable.

## RX2 not fitted

{{fact:n_dnp}} refs are used only by receive chain 2 (from the P2 antenna port to ADC channel B) and
are DNP in 1-RX. R51 and R52 are counted in them but electrically bias the shared ADL5802 IF1 output;
the recommendation (`rx1-ifbias`) is to keep them fitted. No shared part is removed: U29 (dual mixer),
U45 (one quad package; amps A and B kept), the LO split (U3, U26, F1, F2) and U8 (replaced) are not in
the list (`tests/test_rx1_rx2_dnp.py`).

{{table:rx2_dnp.csv}}

The unused U45 amps C and D have their + inputs on `/ADC_VCMA`, which has no source once the LTC2292
goes. Recommended (a, `rx1-unused-amps`): merge `/ADC_VCMA` into `/ADC_VCMB` so each is a unity
follower on the bias; with U45 replaced by the LT6231 the pair disappears and this is not needed.
Three FPGA pins are freed (U30 M1, P1, N2); the channel-B data bus was never routed to the FPGA.

## Stock-only lines

JLC database {{fact:jlc_db}}: of {{fact:n_lines}} lines, {{fact:n_ok}} pass, {{fact:n_thin}} is thin
(U29: stock 3 for a need of 3) and {{fact:n_fail}} fail; the rest are vias, pads and mounting holes
(nothing to buy) or not fitted. U8 passes at stock 200 for 3. Each failing line has a JLC-stocked
option; the table gives the recommended one (JLC-first, least layout work, a datasheet on file). All
options, their datasheet pages and their checks are in the `rx1-` keys of `parts/choices.json`.

{{table:stock_lines.csv}}

Layout work the substitutions cause: {{fact:n_fp_lines}} footprint-change lines ({{fact:fp_lines}}) and
{{fact:n_design_lines}} design change with a layout edit ({{fact:design_lines}}: pin 4 BYPASS becomes
FB, two divider resistors), {{fact:n_layout_refs}} refs in all, plus the U8 footprint (LFCSP-32 5 x 5 mm)
that the directive already decides. Notes:

- Covering checks that exist: U45 as the LT6231 is covered by the step 3 simulation; the L5 to L7
  options are checked against the LMR51420 current limit (`stock_lines.py`, `inductor_check`:
  only the APS1040M330A, 5.05 A, is near the 3.5 A typical and 5.1 A maximum limit,
  `ti-lmr51420-datasheet` p.5 and p.18); the U21 divider for 10 V is calculated (TPS7A2401 with
  1.15 M and 162 k gives 10.04 V, 9.71 to 10.39 V worst case, `ti-tps7a24-datasheet` p.14).
- Not covered by any simulation, and said so in `docs/board-changes.md`: the TDK balun (rf-01
  amplitude balance 2.5 dB against 2 dB, no S-parameters on file), the LDO output noise (2.4 mVrms
  scaled against 30 uVrms; sim-01, sim-spurs), PAT0816, the SMA transition.
- P1 and U15: the par-09 option BWSMA-KE-P001 is a vertical screw-on SMA, not an edge launch
  (`batwireless-bwsma-ke-p001-datasheet` p.3, p.6; the CONSMA is edge-mount, `dk-consma003.062` p.1).
  The edge-mount Amphenol 132134-15 has no datasheet on file (`docs/user-fetch.md`). No option is
  recommended: this is your choice (`rx1-sma`) and it needs the datasheet or a design change.
- Through-hole parts (CON2, J2): whether JLC places them for this order is for you to confirm in the
  order tool.

## Data path for real-time SAR

{{fact:raw_pct25}} percent of the 25 MB/s that the FT2232H datasheet states for the synchronous FIFO
(`ftdi-ft2232h-datasheet` p.26; p.1: up to 40 MB/s) is what raw 12-bit samples at 40 MSPS need
(60 MB/s packed, 80 MB/s as the firmware's 16-bit words): {{fact:raw_pct40}} percent of the 40 MB/s
maximum and the whole 60 MB/s of the 60 MHz by 8 bit bus (p.32). The decimated stream (by 20, 2 MSPS) needs
4 MB/s as 16-bit single-channel words ({{fact:dec_pct25}} percent of 25) or 8 MB/s as the firmware sends it
today ({{fact:decw_pct25}} percent).

![Data rates against the FT2232H limits](build/data_path.png)

- Answer: decimated samples stream off the board with no hardware change; raw samples do not.
  The hardware change for raw would be U33 (FT2232H, 8 bit, 60 MHz) replaced by a wider or faster USB
  bridge (for example a USB 3 synchronous FIFO class). Making it is out of scope and it is not needed for
  the decimated stream. No rate is claimed for any such part: its datasheet is not on file.
- FPGA buffers (XC7A100T, 4,860 Kb, `amd-ds180-7series-overview` p.3): the firmware's three FIFOs use
  {{fact:fifos_pct}} percent, and a 2001-word decimated chirp fits the 2048-word ADC FIFO. A raw 1 ms chirp
  (40,000 samples) fits in block RAM ({{fact:raw_chirp_pct}} percent) but that is store and forward:
  draining it takes 3.2 ms at 25 MB/s, so a continuous 1 ms chirp cannot be sustained.
- Firmware ceiling, not a hardware limit: `control.vhd` moves a 32-bit word in about 18 clocks (8.9 MB/s),
  only 11 percent above the 8 MB/s the 2 MSPS stream needs (counted from the state machines, not
  simulated). A lower decimation (4, 10 MSPS, 20 MB/s) is a firmware change; so is sending 16-bit
  single-channel words.

# 5. Recommendation (labelled as such, the decision is yours)

The choices, each with its recommendation (`parts/choices.json`, keys `rx1-`):

{{table:choices.csv}}

# 6. Changes recorded

- `parts/rx1_changes.csv`: {{fact:n_changes}} rows, one per ref or net, which rx1-03 applies and tests
  the `kicad/` against `kicad-1rx/` netlist difference against. Rows with status `option` are applied
  only when you accept that option.
- `docs/board-changes.md`: a Board column (`1-RX`, `2-RX`, `both`) and one 1-RX row per group of
  changes, each naming its covering check, or saying that none exists.
- `parts/choices.json`: {{fact:n_choices}} keys prefixed `rx1-`. Accept with
  `friday accept rx1-02 --note "<choice per rx1- key>"`.
- Open for the review: which of the options above (the SMA is the one with no recommendation), the
  R92 value, the unused-amp handling, R51/R52, the 3V3A before 3V0 start-up note, and the decoupling
  check of rx1-03.
