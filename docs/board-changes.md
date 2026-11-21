# Changes to the board

This is the running record of every change to the upstream FMCW3 board (`ckflight/FMCW3-Kicad`, as
forked into `kicad/`), including proposed changes, decisions and changes already applied. Each row
gives:
- the change;
- why it was made;
- where the evidence is;
- which simulation or analysis covers it;
- its status.

Status values:
- `proposed`: the agent suggested it;
- `chosen`: the user decided it;
- `applied`: written into `kicad/`, with the commit.

Directives update this file whenever they propose, decide or apply a change (rule of the `parts`
goal). `production/` (upstream's as-ordered XC7A35T build) is not changed and is not listed here.

## Part changes

| Ref | From | To | Why | Evidence | Covered by | Status |
|---|---|---|---|---|---|---|
| U14 (PA) | TQP5525 | QPA9501TR13 (recommended); fallback: remaining TQP5525 stock | The user found the TQP5525 discontinued on Qorvo's page (2026-11-21). The QPA9501 has the same pinout, footprint, enable and detector, and JLC stocks it (C2911573) | `reports/02_pa.pptx`, par-07 Log; `qorvo-qpa9501-datasheet`, `qorvo-qpa9501-sparams` | rf-01 (level plan); sim-01 (5 V branch current) | chosen (par-07 accepted 2026-11-21: QPA9501TR13); par-04 writes the fields |
| FB4 (PA supply bead) | BLM18PG181SN1D (1.5 A at 85 C) | BLM18KG221SN1D (2.2 A at 85 C), same 0603 footprint | More current margin for the PA at the 25 dBm target; the PA current at that power is not in its datasheet | `parts/decisions.csv` FB4; `murata-blm18pg181sn1d-datasheet` table | sim-01 must use the KG model in the 5 V branch before this is final; par-08 fetches the model | proposed (user choice) |
| U22-U24, U25 | value "LD3920" / "LD3920_33" (not orderable) | LD39200DPUR (ADJ, DFN8) / LD39200PU33R (3.3 V, DFN6) | The value field did not hold an orderable code; the part is unchanged | `st-ld39200-datasheet` p.24; `parts/decisions.csv` | none needed (ordering fields only) | proposed (par-03) |
| U26-U28 (baluns) | 5400BL15B0050001E | unchanged; confirmed as the current code of the legacy 5400BL15B050 | Confirmation only | `johanson-5400bl15b0050001e-datasheet` p.1 | rf-01 (uses `johanson-5400bl15b050-sparams`) | confirmed |
| U30 (FPGA) | XC7A100T-1FTG256C (not at JLC) | XC7A100T-1FTG256I C1521781 (JLC stock 59), recommended | JLC assembles it; same package and pins, value C to I | `reports/03_sourcing.pptx`; `amd-ds180-7series-overview` p.15 (Table 12: Artix-7 -1C 0 to 85 C, -1I -40 to 100 C), p.16 (Figure 2); par-03 choice 1 pin check | none needed (same die, I grade) | proposed (par-09, recommendation) |
| U8 (ADC) | LTC2292 (no MPN) | none recommended: keep LTC2292IUP#PBF, sourced or consigned. Options: LTC2298IUP (pin drop-in, consign only); ADS7863ARGET, AD7356BRUZ-500RL7, ADS4229IRGCT (JLC stock, redesign) | JLC stock of the LTC2290-LTC2299 family is 0; the JLC-stocked ADCs change footprint, FPGA pins, data interface and firmware | `reports/03_sourcing.pptx`; `adi-ltc2292-datasheet`, `adi-ltc2298-datasheet`, `ti-ads7863-datasheet`, `adi-ad7356-datasheet`, `ti-ads4229-datasheet` | LTC2298: none needed. Redesign options: sim-02, sim-01 and sim-spurs, not run; they need a new hardware-design directive | proposed (par-09; options, not recommended) |
| U26-U28 (baluns) | 5400BL15B0050001E | HHM1907B1 TDK C531388 (option only) | JLC stocks it; 0402 4-terminal against 0805 5-terminal, so a footprint change | `tdk-hhm1907b1-datasheet` p.2-3 | rf-01 (amplitude balance 2.5 dB against 2 dB); no TDK S-parameters on file, so not covered today | proposed (par-09; option, not recommended) |
| U45 (op-amp) | LT6232IGN#PBF | options: LT6232CGN#PBF C673022 (JLC stock 2, drop-in, 0 to 70 C); 2 x LT6231CS8#TRPBF C4369556 per board (footprint change) | JLC lists the C grade only | `adi-lt6232-datasheet` p.2-4 | sim-02 re-run needed for the LT6231 pair (model `adi-lt6231-ltspice-bundled`); the C grade swap changes the temperature range only | proposed (par-09; options; recommended: keep the I grade, sourced) |
| U21 (LDO) | LP2985A-10DBVR | options: TPS7A2401DBVR C2693328, MIC5205YM5-TR C412820 (BYPASS pin becomes an FB divider) | Not in the JLC database; JLC stocks both | `ti-tps7a24-datasheet` p.1, 3; `microchip-mic5205-datasheet` p.1; `ti-lp2985-datasheet` p.3 | sim-01 and sim-spurs (10 V rail noise against 30 uVrms), not run | proposed (par-09; option, not recommended) |
| P1, P2, U15 (SMA) | CONSMA003.062 | options: BWSMA-KE-P001 C496550, 132134-15 C3172297 | Not in the JLC database; JLC stocks both | `batwireless-bwsma-ke-p001-datasheet` p.4 (0-6 GHz, 0.15 dB at 6 GHz), p.6 (drawing); `amphenol-132134-datasheet` (still a user-fetch row in docs/user-fetch.md; no page until saved) | none: board-thickness fit unverified; the 5.8 GHz rating holds for the Bat Wireless part only, the Amphenol rating is unverified | proposed (par-09; option, not recommended) |
| U12 (attenuator) | PAT1220-C-3DB-T5 | option: PAT0816-C-3DB-T5 C2655485 (1.6x0.8 mm, 64 mW) | JLC stock of the 0805 part is 5 for a need of 3 | `pat1220-attenuator-datasheet` p.1-2 (the same Susumu sheet covers PAT0816: 64 mW, 0603) | rf-01 level plan (power below 64 mW), not run | proposed (par-09; option, not recommended) |
| L5-L7 (inductor) | SRR6040A-330M | options: CDRH6D28NP-330NC C313052, SRR6038-330Y C2041395 (footprint change) | JLC stock 3 of 9; DigiKey NFND | `sumida-cdrh6d28-datasheet` p.2; `bourns-srr6038-datasheet` p.1 | LMR51420 current-limit check of par-03 choice 4; both options saturate near 1 A, so neither covers it | proposed (par-09; options; recommended: none, see choice 4) |
| D1-D3, D5-D7 (LEDs) | no part number | KT-0603R red C2286 (JLC Basic, stock 8412802), recommended | JLC stocks it; the colour is the user's | `kento-kt-0603-led-datasheet` p.3-4 (red: Vf 1.8-2.4 V at 20 mA); `kento-kt-0603w-led-datasheet`, `kento-kt-0603g-led-datasheet`, `kento-kt-0603b-led-datasheet` p.3 (Vf 2.6-3.1 V at 5 mA) | none needed for red; white, green or blue (up to 3.1 V) need the series resistors re-sized | proposed (par-09, recommendation) |
| CON2 (jack), J2 (header) | no part number | DC-005-A200 C720557; 2.54-2*8PPin C68234 (options) | JLC stocks both (through-hole) | `xunpu-dc-005-a200-datasheet` p.1 (30 V DC / 3 A, PCB layout); `boomele-2-54-2x8-header-datasheet` p.1 (3 A; a 1xN family drawing); alternates `shouhan-dc005-datasheet` p.1, p.3; `hanxia-hx-pz2-54-2x8p-datasheet` p.3-4 | none; the J2 pitch (2.5 mm pads against 2.54 mm) is a footprint question | proposed (par-09; options) |

The par-03 choices (FPGA, ADC grade, USB-C, L5-L7 inductor, consigned parts, library, U6, buck
variant, Y2) get a row here once the user decides them.

## Open design findings (not yet changes)

| Finding | Source | Goes to |
|---|---|---|
| TX output is short of the 25 dBm target. The PA gets about -7.2 dBm of drive and needs 32.7 dB of gain; same-gain PAs give about 32 dB typical, which is 0.7 dB short. The QPA9501's measured gain is about 31 dB across 5.60-5.90 GHz, which is about 1.7 dB short. This is in the original design. A smaller TX pad (U3 6 dB or U12 3 dB, if either is before the PA) could close it. That is a design choice for the user | `reports/02_pa.pptx` (par-07) | rf-01 (RF level plan): check which pads are in the TX path and the drive level |
| The target band (5.60-5.90 GHz) and the 25 dBm target extend beyond the 5.725-5.875 GHz ISM band | `analysis/targets/default.yaml` (set by the user 2026-11-21) | the user (regulatory) |
| The 10 uF 25 V X5R 0805 capacitors (CL21A106KAYNNNE; C60-C62, C64, C70 and C71 are on the 12 V rail) lose about 80 % of their capacitance at 12 V DC bias, so each acts like about 2 uF there. Options: a larger or higher-voltage part on the 12 V rail; a design choice for the user | `samsung-cl21a106kaynnne-sheet` (DC bias curve) | sim-01 and sim-02: use the derated value on the 12 V rail |
