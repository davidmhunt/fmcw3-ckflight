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
| U14 (PA) | TQP5525 | QPA9501TR13 (recommended); fallback: remaining TQP5525 stock | The user found the TQP5525 discontinued on Qorvo's page (2026-11-21). The QPA9501 has the same pinout, footprint, enable and detector, and JLC stocks it (C2911573) | `reports/02_pa.pptx`, par-07 Log; `qorvo-qpa9501-datasheet`, `qorvo-qpa9501-sparams` | rf-01 (level plan); sim-01 (5 V branch current) | proposed (par-07, awaiting the user) |
| FB4 (PA supply bead) | BLM18PG181SN1D (1.5 A at 85 C) | BLM18KG221SN1D (2.2 A at 85 C), same 0603 footprint | More current margin for the PA at the 25 dBm target; the PA current at that power is not in its datasheet | `parts/decisions.csv` FB4; `murata-blm18pg181sn1d-datasheet` table | sim-01 must use the KG model in the 5 V branch before this is final; par-08 fetches the model | proposed (user choice) |
| U22-U24, U25 | value "LD3920" / "LD3920_33" (not orderable) | LD39200DPUR (ADJ, DFN8) / LD39200PU33R (3.3 V, DFN6) | The value field did not hold an orderable code; the part is unchanged | `st-ld39200-datasheet` p.24; `parts/decisions.csv` | none needed (ordering fields only) | proposed (par-03) |
| U26-U28 (baluns) | 5400BL15B0050001E | unchanged; confirmed as the current code of the legacy 5400BL15B050 | Confirmation only | `johanson-5400bl15b0050001e-datasheet` p.1 | rf-01 (uses `johanson-5400bl15b050-sparams`) | confirmed |

The par-03 choices (FPGA, ADC grade, USB-C, L5-L7 inductor, consigned parts, library, U6, buck
variant, Y2) get a row here once the user decides them.

## Open design findings (not yet changes)

| Finding | Source | Goes to |
|---|---|---|
| TX output is short of the 25 dBm target. The PA gets about -7.2 dBm of drive and needs 32.7 dB of gain; same-gain PAs give about 32 dB typical, which is 0.7 dB short. The QPA9501's measured gain is about 31 dB across 5.60-5.90 GHz, which is about 1.7 dB short. This is in the original design. A smaller TX pad (U3 6 dB or U12 3 dB, if either is before the PA) could close it. That is a design choice for the user | `reports/02_pa.pptx` (par-07) | rf-01 (RF level plan): check which pads are in the TX path and the drive level |
| The target band (5.60-5.90 GHz) and the 25 dBm target extend beyond the 5.725-5.875 GHz ISM band | `analysis/targets/default.yaml` (set by the user 2026-11-21) | the user (regulatory) |
