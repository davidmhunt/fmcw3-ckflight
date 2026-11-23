---
title: "Load budget for the 1V0, 3V8 and 5V6 buck rails and the APS0650M330A inductor check"
---

# 1. Question

The user chose the Coilank APS0650M330A (JLC C47327223) for L5, L6 and L7 on both boards on
2026-11-23, in place of the SRR6040A-330M, subject to this check. L5, L6 and L7 are the inductors of
the LMR51420 bucks U17 (1V0), U18 (3V8) and U19 (5V6). Does the APS0650M330A hold the real operating
current of each rail, on the 2-RX board (`kicad/`) and the 1-RX board (`kicad-1rx/`)?

**Result: yes, on every rail of both boards (`aps0650_ok` = {{fact:ok}}).** The worst-case peak current is
{{fact:peak_max}} A (limit {{fact:peak_limit}} A) and the worst-case DC load is {{fact:dc_max}} A (limit
{{fact:dc_limit}} A). The inductor choice stays with the user; this report only supplies the evidence.

# 2. Inputs and assumptions

- The consumer list of each board is read headless from the netlist export of `kicad/` and
  `kicad-1rx/` (`consumers.py`, `kicad-cli`); nothing under `kicad/` or `kicad-1rx/` was changed.
  Each buck output is traced through its LDOs to every part it feeds. An LDO passes its load current
  plus its own ground current back to the buck, so each LDO appears as a row (its ground current)
  and its loads as rows below it.
- On the 1-RX board the receive-chain-2 parts that are not fitted (U13, U16; `parts/rx1_changes.csv`)
  are left out, the AD9237 takes the place of the LTC2292, and R990/R991 are added.
- Every current names its datasheet manifest id (`datasheets/manifest.yaml`) and PDF page, or is
  `computed` (Ohm's law or CV$^2$f on schematic values), or is a `bound` with its reason. "Typ" is the
  expected operating value, "Max" the worst case used for the pass marks.
- The pass marks are the ones fixed in the directive. Inductor: APS0650M330A, 33 uH, DCR
  {{fact:dcr}} mohm max, Irms {{fact:irms}} A (about a 40 C rise), Isat {{fact:isat}} A typ (the
  current at which the inductance has dropped about 40 %), manifest id
  `coilank-aps1040m330a-datasheet` (the APS series sheet), PDF page 6 for the row and page 1 for the
  definitions.
    - peak current at most 60 % of Isat = {{fact:peak_limit}} A;
    - DC load at most 2/3 of Irms = {{fact:dc_limit}} A, and at most the LMR51420's 2 A rating
      (`ti-lmr51420` p1);
    - the copper loss at the typical load is listed.
- The LMR51420 variant of U17-U19 is unresolved (`parts/decisions.csv`, user-choice: the X and XF
  parts switch at 500 kHz, the Y and YF parts at 1.1 MHz). Both frequencies are reported, and the
  worst case (the lower frequency, the larger ripple) is the one the pass mark uses.

# 3. Method

**Ripple.** `ti-lmr51420` equation 10 (PDF page 18, section 9.2.2.4):

$$\Delta I_L = \frac{V_{out}\,(V_{IN}-V_{out})}{V_{IN}\; L\; f_{SW}}$$

$V_{IN}$ = 12 V (net `/power/12V` on pin 3 of U17-U19), $V_{out}$ from the feedback dividers
(0.6 V reference, `ti-lmr51420` p5): 1.008 V, 3.809 V and 5.600 V. L is 33 uH less 20 % =
{{fact:l_low}} uH. The ripple does not depend on the load in continuous conduction. The peak current is
DC + ripple / 2.

Hand-worked case, 5V6 at 500 kHz: 5.6 x (12 - 5.6) / (12 x 26.4 uH x 500 kHz) = 35.84 / 158.4 =
0.226 A peak to peak, so the peak at 1.165 A DC is 1.165 + 0.113 = 1.278 A. `tests/test_rail_loads.py`
repeats this by hand.

**Copper loss** at the typical load: I$_{typ}^2$ x DCR (178 mohm is the maximum, so the loss is an
upper figure; it is DC only, with no AC or core loss).

**1V0 FPGA core.** There is no datasheet number for VCCINT of the XC7A100T: it is static current
(DS181) plus dynamic current that depends on the design (`vccint.py`). The source is the routed Vivado
power report committed in the firmware repo (`davidmhunt/fmcw3-ckflight-fw`, read only, file
`FMCW3.runs/impl_1/top_module_power_routed.rpt`, commit 1b354b58, device xc7a100tftg256-1, junction
26.3 C, confidence Low). Current design: 7831 LUTs, 9932 flip-flops, 35 block RAM tiles, 15 DSPs, 1 MMCM.

- Typical: the report's VCCINT plus VCCBRAM, **{{fact:vccint_typ}} mA** (95 mA VCCINT, 79 mA of it dynamic).
- Bounded worst case: **{{fact:vccint_max}} mA** = static 159 mA (DS181 ICCINTQ 155 + ICCBRAMQ 4, the highest
  static figure the sheet gives, at 85 C Tj) + 4 x the report's 79 mA dynamic. The factor 4 stands for a
  50 % average toggle rate on every net, four times the usual vectorless default (that default is from
  memory of the tool; the report does not state its activity: no SAIF file, "Medium" internal-node
  confidence). It scales the clock tree too, so it is on the high side. Clocks are as constrained in
  the report (40, 100 and 60 MHz); growth of the design is not in the bound.
- Power-on current (DS181 Table 6: ICCINTQ + 170 mA, ICCBRAMQ + 60 mA = {{fact:vccint_on}} mA) is a
  requirement on the supply during configuration, not a running load.
- The Vivado power report of the final design replaces this estimate.

# 4. Findings

## Result per rail and board

{{table:summary.csv}}

"DC max" is the worst-case DC load, "Ripple" the peak-to-peak ripple at 500 kHz with L 20 % low, "Peak" the
worst case (DC max + ripple / 2), "Cu loss" the copper loss at the typical load. Pass marks: peak at
most {{fact:peak_limit}} A, DC at most {{fact:dc_limit}} A.

![Worst case against the limits](build/peak_vs_limit.png)

Every rail passes on both boards. The 5V6 rail is the tightest: its worst-case DC load is
{{fact:dc_5v6}} A, leaving {{fact:dc_5v6_margin}} A under the DC mark, and its worst-case peak is
{{fact:pk_5v6}} A, leaving {{fact:pk_5v6_margin}} A under the peak mark. The 1V0 and 3V8 rails have more
than a factor of two on the DC mark. The 1-RX board draws less on 3V8 (receive chain 2 not fitted, a
different ADC) and the same on 5V6 and 1V0.

## Ripple, peak and copper loss at both switching frequencies

{{fact:ripple_table}}

The ripple at 1.1 MHz is less than half
that at 500 kHz, so the 500 kHz case is the worst case for the pass marks whichever suffix is chosen;
the suffix decision does not change the result.

## Consumer tables

The tables list every consumer of each rail, both boards in one table ("Board" says which). Each
row is one part on one supply path; an LDO row is its ground current and the rows after it are its
loads. The sum rows are the DC load the buck delivers.

### 1V0 (U17, L5)

{{fact:table_1V0}}

### 3V8 (U18, L6)

{{fact:table_3V8}}

### 5V6 (U19, L7)

{{fact:table_5V6}}

## Fault case (no pass mark)

- LMR51420 high-side peak current limit, `ti-lmr51420` p5 (IHS_PK(OC)): {{fact:ilim_min}} A min, {{fact:ilim_typ}} A
  typ, {{fact:ilim_max}} A max. Against the APS0650M330A Isat of {{fact:isat}} A these are
  {{fact:ilim_min_pct}} %, {{fact:ilim_typ_pct}} % and {{fact:ilim_max_pct}} % of Isat. So at the typical limit the inductor is
  just at its saturation point, and at the maximum limit (5.1 A) it saturates before the regulator
  limits. The maximum output current of equation 8 (p14), the average of the valley and peak limits, is
  {{fact:iout8_min}} / {{fact:iout8_typ}} / {{fact:iout8_max}} A (min / typ / max).
- Hiccup mode (section 8.3.6, PDF page 14; the directive names page 18, which holds equation 10, not
  hiccup): {{fact:hiccup_trigger}}. The converter shuts down and stays off for tHICCUP, 135 ms typ, then
  restarts, and repeats while the fault remains. {{fact:hiccup_blank}}.
- An overload that keeps FB above 40 % of the reference is limited cycle by cycle at the peak limit,
  not by hiccup; the inductor then carries up to the peak limit for as long as the overload lasts.
- Reading: the working loads are far below Isat, so saturation can only occur in a fault (a short or an
  overload on a rail), and only at the upper part of the current-limit spread. Whether that is acceptable
  is the user's call. The fault case is stated, not scored.

## Checks that are bounds

- A consumer with no datasheet current is a `bound` row, with its reason in the Source column:
  the header J2 (100 mA allowance on 3V3D), R49 (VSET pin of the ADL5802, 2.5 mA), the ADF4158 VP
  pin (5 mA).
- LED colours are not chosen (`parts/decisions.csv` D1 to D7, user): Vf 2.1 V typ and 1.8 V (the lowest
  candidate) give the typical and maximum.

# 5. Open items

1. **VCCINT is an estimate.** The committed power report has confidence Low and no activity file. The
   1V0 rail has a large margin (worst-case peak {{fact:pk_1v0}} A against {{fact:peak_limit}} A), so a design
   several times larger still passes; the Vivado report of the final design replaces the number.
2. **LMR51420 suffix** of U17-U19 is unresolved. Both frequencies are reported; the result does not
   depend on it.
3. **The PA (U14) current** is the TQP5525's (qorvo-tqp5525-datasheet p3, 850 mA max at 27.5 dBm). par-07
   replaces that part; the QPA9501's current at 25.5 dBm is not in its datasheet. The 5V6 rail has
   {{fact:dc_5v6_margin}} A of DC headroom and {{fact:pk_5v6_margin}} A of peak headroom, so a replacement
   drawing up to the smaller of the two more than the 850 mA used still passes; this should be re-run when the PA is chosen.
4. **Header J2** load (100 mA allowance on 3V3D) and **LED colours** are not set by the design.
5. **Datasheet readings that need a second look:** the SKY65404 enable-current column order, the LTC2292
   IOVDD read from a plot, the AD9237 AVDD maximum from power over voltage (180 mW / 3 V, which counts the
   DRVDD share, so it is high). None of them can move a rail across its mark.
6. The "typ" Isat of 3.53 A has no stated tolerance; the 60 % mark is the margin for it. The temperature
   rise of the inductor in the enclosure is covered only by the 2/3 Irms mark, not measured.
7. Simulating the bucks is out of scope (the LMR51420 model loads in no engine here; sim-05).
8. **FPGA VCCAUX and VCCADC (U30, 1V8 branch)** use the firmware's routed power report for the typical
   (Vccaux 77 mA, of which 58 mA dynamic, plus Vccadc 20 mA = 97 mA), not the DS181 quiescent figure
   (36 mA) used in the first pass. The maximum is DS181 ICCAUXQ 36 mA plus the report's VCCAUX dynamic
   current times the same factor 4 as the 1V0 core, plus Vccadc: 268 + 20 = 288 mA. The 3V8 rail's maximum
   is 1.184 A (2-RX) against the 1.55 A mark, so the result is unchanged.

# 6. Reproduce

```
./run python3 analysis/12_rail_loads/consumers.py --check   # netlist export, both boards
./run python3 analysis/12_rail_loads/currents.py --check
./run python3 analysis/12_rail_loads/vccint.py --check
./run python3 analysis/12_rail_loads/loads.py --check --show
./run tools/build_report.py analysis/12_rail_loads
./run uv run pytest tests/test_rail_loads.py -q
```
