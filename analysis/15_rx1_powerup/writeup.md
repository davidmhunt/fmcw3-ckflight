---
title: "1-RX power-up and power-down: AD9237 pins and FPGA rail order"
---

# 1. Question

On the 1-RX board (`kicad-1rx/` with the rx1-02 changes) do the AD9237 pins with an AVDD + 0.3 V limit
(VIN+, VIN-, CLK, PDWN; `adi-ad9237-datasheet` p.7) stay inside it, and pass no current into their clamp
diodes, while the rails come up and go down, with the rail order set by the circuit? The sequenced design
is `rx1-seq` A (the user, 2026-11-25): U24 EN (3V3A) and U23 EN (1V8, whose PG enables U25 for 3V3D) are
on 3V0 from U39. The CLK pin is also checked in steady state, where the U6 clock on 3V3D swings to 3.3 V
against AVDD 3.0 V. The FPGA rails are checked against the DS181 power order. Nothing under `kicad/` or
`kicad-1rx/` was written; the board is read headless.

**Result.**

- **Power-up passes.** In all {{fact:n_cases}} cases (8 power corners, mixer IF at zero and at full scale) no pin goes
  above AVDD + 0.3 V and the clamp current is under 0.01 uA ({{fact:up_clamp_ua}} uA to two places). 3V3A, 1V8 and 3V3D start after 3V0 passes the
  EN threshold in all of them (the 3V0 EN fires at {{fact:t_en_min}} to {{fact:t_en_max}} ms). The tightest pins are CLK and PDWN, {{fact:up_clk_margin}} V
  inside the limit, and that margin depends on an assumption about the PG output (section 5, sweep VPGMIN).
- **Sudden 12 V removal fails** in all {{fact:n_cases}} cases. CLK reaches {{fact:dn_clk_over}} V over the limit and pushes
  {{fact:dn_clk_ma}} mA into its clamp for {{fact:dn_clk_us}} ms above 10 uA, VIN {{fact:dn_vin_over}} V over with {{fact:dn_vin_ma}} mA, PDWN {{fact:dn_pdwn_over}} V over with
  {{fact:dn_pdwn_ma}} mA. The AD9237 sheet gives no clamp current it tolerates, so none of these can be called safe; the LTC2292 on
  the 2-RX board tolerates over 100 mA (`adi-ltc2293-2292-2291-datasheet` p.5 note 3). With a one-way U39 output the
  CLK current is {{fact:ns_clk_ma}} mA and VIN has none; the truth lies between the two (section 6).
- **CLK steady state fails at the tolerance limits.** Nominal 3V3D 3.3 V against AVDD 3.0 V sits exactly on the
  limit (over by {{fact:st_nom_over}} V); at 3V3D +2 % and 3V0 -2 % CLK is {{fact:st2_over}} V over, at +/-5 % {{fact:st5_over}} V over. A larger R15 does not
  lower the pin voltage; a divider does (F3a).
- **The FPGA order is timing, not design, for {{fact:n_timing_on}} of {{fact:n_on}} power-up rows and {{fact:n_timing_off}} of {{fact:n_off}} power-off rows.** 1V0 (U17)
  before 1V8 and 3V3D is not forced: U17 and U18 both start from 12 V. Fixes F1c (design) and F1b (timing) are
  below. VCCO - VCCAUX peaks at {{fact:vcco_vccaux_max}} V against 2.625 V, with {{fact:vcco_vccaux_over_ms}} ms over the limit, in every case.
- No fix is applied here. The choices are the user's (section 9).

# 2. Facts from the datasheets

Every number below has its manifest id and PDF page; the simulation uses nothing else except the assumptions
of section 3.

- **AD9237** (`adi-ad9237-datasheet`): VIN+, VIN-, CLK and PDWN are AGND - 0.3 V to AVDD + 0.3 V absolute
  maximum (p.7; AVDD is 3V0, so the ceiling is 3.3 V when AVDD is 3.0 V). Figures 4 and 7 (p.10): the VIN
  diodes to AVDD and ground sit at the pin; the CLK and PDWN diode pair sits at the pin ahead of a 375 ohm
  resistor. The sheet states no clamp current or latch-up rating (text search of the whole sheet). Input
  capacitance 7 pF per VIN pin (p.3 Table 1); logic inputs 2 pF, input current +/-10 uA (p.4 Table 2).
- **LTC2292** (`adi-ltc2293-2292-2291-datasheet` p.5 note 3): inputs are clamped by internal diodes and take more
  than 100 mA without latch-up, which is why the 2-RX board is the reference and out of scope.
- **LP5907** (`ti-lp5907-datasheet`), U39 3V0: turn-on time 80 typ / 150 max us, EN high 1.2 V min, low
  0.4 V max (p.6). Its IN and EN are on 3V8.
- **LD39200** (`st-ld39200-datasheet`), U23, U24, U25: EN high 1.2 V min, low 0.5 V max (p.7, p.8); PG rising
  threshold 0.92 x VOUT, falling 0.8 x VOUT, open drain, 0.4 V at 6 mA (p.7, p.8); start-up plots p.13 Figures 21 to 24
  (Figure 23: EN start-up, no bypass capacitor, VIN 3.7 V). ST publishes no model (`parts/models_needed.csv`).
- **LMR51420** (`ti-lmr51420-datasheet`), U17 (1V0), U18 (3V8), U19 (5V6): EN rising 1.1 / 1.227 / 1.36 V, falling
  0.95 to 1.22 V, VIN UVLO rising 3.89 typ / 4.5 max, falling 3.58 typ / 3.35 min, soft start 3.2 / 4.0 / 5.4 ms
  (p.5), 3.5 A typical current limit (p.5); six pins and no power-good (p.3). All three have EN and VIN on 12 V.
- **XC7A100T** (`amd-ds181-artix7-datasheet`): recommended power-on order VCCINT, VCCBRAM, VCCAUX, VCCO, power-off in
  reverse (p.8); VCCO - VCCAUX not above 2.625 V for longer than TVCCO2VCCAUX per cycle (p.8), 300 ms at 125 C
  (p.9); ramp GND to 90 % 0.2 to 50 ms (p.9 Table 7); pad pull-up 90 to 330 uA at VCCO 3.3 V (p.3).
  `amd-ug470-7series-config` p.22: with PUDC_B low the pull-ups are on during configuration. On this board
  VCCINT and VCCBRAM are 1V0 (U17), VCCAUX and VCCADC 1V8 (U23), VCCO 3V3D (U25).
- **PL133-37** (`microchip-pl133-37-datasheet`) U6: VOH 2.4 V min at -12 mA and 3.3 V; typical CMOS output
  impedance 20 ohm (p.2, p.3); the sheet gives no rail-to-rail figure.
- Bypass capacitors (`kicad-1rx/` netlist with the rx1-02 changes): 3V0 12.4 uF with C994, 3V3A 10.87 uF, 1V8 68.75 uF,
  3V3D 82.57 uF with C995, 1V0 178.28 uF, 3V8 80 uF, 5V6 50 uF, 12 V 51 uF. R97 and R99 49.9 ohm, C163 to C165 100 pF,
  R992 10k in PDWN.

# 3. Simulation and assumptions

LTspice transient through `./run --sim` (`powerup_sim.py`, results in `sim/powerup.json`; the report
rebuilds from the JSON without the simulator): bucks U17, U18, U19 behavioural (the TI model is encrypted)
starting at the 12 V UVLO with their soft start; U39 the TI LP5907-3.0 model on file (`ti-lp5907-3p0-pspice`); U23, U24, U25 LD39200
behavioural with the EN threshold, the start-up fitted to Figure 23 ({{fact:ld_td}} us delay, {{fact:ld_tau}} us time constant,
90 % at {{fact:ld_t90}} us, rms error {{fact:ld_rms}} V) scaled to 0.1 and 0.3 ms for the fast and slow corners, and the PG at its thresholds; U45 the
LT6231 subcircuit; U6 a 3.3 V CMOS source on 3V3D through R15; each AD9237 pin as its capacitance with clamp
diodes to AVDD and AGND. Eight power corners (U17 and U18 soft start 3.2 or 5.4 ms, LDO start-up 0.1 or 0.3 ms)
times IF at zero and at full scale, each with the 12 V removal at 14 ms; the {{fact:n_checks}} sanity checks (rail settles at its set
voltage, no timestep or matrix warning, fit error) all pass ({{fact:n_runs_checks}} of {{fact:n_checks}}).

Assumptions, each stated and swept (table in section 6):

1. **Clamp diode model.** The sheet gives no diode voltage. Weak (Is 1e-15 A, Rs 10 ohm), typical (1e-14 A, 5 ohm),
   strong (1e-12 A, 2 ohm). CLK clamp current {{fact:diode_clk_range}} mA over the three.
2. **LD39200 behavioural model.** One exponential after a delay fitted to Figure 23; the sheet gives no min or max start-up
   time, so the corners are scaled. The fit is tested against the plot points in `tests/test_rx1_powerup.py`.
3. **U6 output resistance and swing.** 20 ohm typical (p.2); 10 and 40 ohm give CLK clamp current {{fact:ro_clk_range}} mA. The rail-to-rail
   swing is an assumption (the sheet gives none). The clock is held high during the slow transients, the worst case for the pin voltage.
4. **Y2 start-up.** The output is high from the first volt U6 can run on, or after the 2 ms start-up of `ecs-txo-32csmv-datasheet` p.1; no change in the result.
5. **PG behaviour at low VIN (VPGMIN).** The LD39200 sheet states no PG behaviour below VIN 1.25 V. The base case pulls PG low from VIN 1.25 V. If PG
   only pulls low from 2.0 or 2.8 V, U25 follows its EN pulled up to 3V8 by R104, 3V3D starts before 3V0 and CLK is {{fact:vpgmin_2_up_over}} to {{fact:vpgmin_28_up_over}} V over at power-up. **The board is sensitive to
   this assumption**; the bench (lay-03) should confirm it.
6. **Loads** are constant resistances at nominal voltage from `analysis/12_rail_loads/sim/currents.json`; 12 V rises in 1 ms (0.1 to 5 ms: no change) and is
   disconnected at once at removal. With no load left the 12 V node stays at the buck UVLO (3.58 V) in the simulation, which does not change the pin results.
7. **U39 at removal.** The TI model sinks current once its VIN is below 2.2 V, so 3V0 collapses faster than a real LDO. Run as supplied (`ti`) and with a one-way
   output and the pass-device body diode (`nosink`, assumed Is 1e-11 A, Rs 0.3 ohm). The truth lies between.

# 4. The order map

Each row is one ordering the ADC or the FPGA needs, read from the `kicad-1rx/` netlist with the rx1-02 changes
(`sequence.py`, `sequence.csv`). **Design** means an EN or PG chain forces it; **timing** means it holds only because one regulator
is faster. The margin is the later rail's 90 % time minus the earlier rail's, over the 8 power corners, from the simulation (the IF level changes it by
at most {{fact:if_spread_ms}} ms). A chain from 3V0 forces the *start* of 3V3A, 1V8 and 3V3D (EN 1.2 V) but not the 90 % time: 1V8 starts after 3V0
passes its EN but reaches 90 % first, and no ADC pin is on 1V8, so that row is design with a negative margin.

Power-up:

{{fact:md_order_on}}

Power-off (sudden 12 V removal):

{{fact:md_order_off}}

An EN or PG chain acts only after its source rail has fallen below its low threshold, so it cannot make the dependent rail fall first. Only a feed
(an input from the earlier rail) forces a power-off order, and every LDO here runs from 3V8 (fix F2c: no circuit exists). The off orders are set by each rail's
stored charge against its load, and the simulation shows 1V8 falling after 3V0, 1V8 after 1V0 and 3V3D after 1V0 at removal: the wrong order for AVDD and for DS181 p.8.

# 5. Power-up, per case

Waveforms of the fast and the slow corner, the worst pin case against AVDD + 0.3 V, and the FPGA rails:

![Power-up: rails in order, pins against the limit, FPGA rails](build/powerup.png)

The table gives, per case, the pin voltage minus the limit (negative is inside), at power-up and at 12 V removal (section 6):

{{fact:md_pins}}

At power-up the worst pin is CLK and PDWN at {{fact:up_clk_peak}} V against AVDD {{fact:up_clk_avdd}} V at that instant ({{fact:up_clk_margin}} V inside the limit, case {{fact:up_worst_case}}); VIN peaks at {{fact:vin_up_peak}} V,
{{fact:up_vin_margin}} V inside. 3V3D starts after 3V0 because U25's EN follows the U23 PG, which follows 1V8, which starts when the 3V0 EN fires.

# 6. 12 V removal and the clamp currents

![12 V removal at 14 ms: rails, pins against AVDD + 0.3 V, clamp current, VCCO - VCCAUX](build/removal.png)

The worst case is {{fact:worst_dn_case}} (clamp currents and the sweeps of each assumption):

{{fact:md_clamp}}

The cause is the order of falling rails: AVDD (3V0) falls from 90 % to 10 % in about 0.5 ms in this case (and the 5V6 IF pull-up rail
collapsing in 0.7 ms couples through C37 and C38 into the U45 stages that drive VIN), while 3V3D, which feeds CLK and PDWN through U6 and the FPGA, is held up by 82.57 uF. The
peak charge through the CLK clamp is {{fact:dn_clk_nc}} nC and through the VIN clamp {{fact:dn_vin_nc}} nC. The AD9237 sheet states no clamp current it tolerates, so
the result is a fail by the stated limit (the voltage) and the current is reported for the user to judge. With a one-way U39 output: CLK {{fact:ns_clk_over}} V over, {{fact:ns_clk_ma}} mA;
VIN no clamp current; PDWN {{fact:ns_pdwn_ma}} mA.

# 7. CLK and PDWN in steady state

{{fact:md_steady}}

At nominal the CLK high level equals the limit (3V3D 3.3 V, AVDD 3.0 V + 0.3 V): the margin is {{fact:st_nom_over}} V. At 3V3D +2 % and 3V0 -2 % the peak is {{fact:st2_peak}} V against {{fact:st2_lim}} V ({{fact:st2_over}} V over; mean clamp
current {{fact:st2_mean}} uA); at +/-5 % it is {{fact:st5_peak}} V against {{fact:st5_lim}} V ({{fact:st5_over}} V over, {{fact:st5_ma}} mA peak, {{fact:st5_mean}} uA mean). PDWN held high by the FPGA is the same ({{fact:st2_pdwn_over}} V over at +2 %).
Raising R15 to 100 ohm does not change the pin voltage (over {{fact:f3b_over}} V): it limits only the clamp current. A divider does: F3a (R15 68 ohm and 680 ohm to GND at the pin)
gives {{fact:f3a_peak}} V ({{fact:f3a_over}} V) at +2 % and {{fact:f3a5_peak}} V ({{fact:f3a5_over}} V) at +5 %, rise {{fact:f3a_rise}} ns and duty {{fact:f3a_duty}} % at 40 MHz.

# 8. FPGA order

DS181 recommends VCCINT, VCCBRAM, VCCAUX, VCCO and the reverse to power off (p.8); that is 1V0, 1V8, 3V3D. 3V3D follows 1V8 by the U23 PG to U25 EN chain (design), and VCCO - VCCAUX
never exceeds {{fact:vcco_vccaux_max}} V in any case ({{fact:vcco_vccaux_over_ms}} ms over 2.625 V, on the ramp or at removal), so the stated limit holds. 1V0 before 1V8 and 3V3D is timing: U17 and U18 both start from 12 V, and the margin (1V8 90 % time minus 1V0 90 % time) runs from negative
(1V8 reaches 90 % before 1V0, the wrong order) to positive over the corners, see the order map. DS181 gives the order for minimum current and 3-stated I/O; it is not a damage limit. At removal 1V8 and 3V3D both fall after 1V0 (the wrong order), and 3V3D falls just before 3V0.
The fast LD39200 corner reads 0.10 ms from GND to 90 %, below the 0.2 ms minimum ramp of DS181 p.9 Table 7 (the fit to Figure 23 gives {{fact:ld_t90}} us).

# 9. Fixes, with their cost and the room on today's board

{{fact:md_fixes}}

Room: `analysis/11_board_1rx/route_space.py` routes each new connection on the board as it is today (grid router, trace 0.15 mm, clearance 0.15 mm, via 0.46 / 0.254 mm,
route and via counts in the table) and `analysis/15_rx1_powerup/fix_space.py` searches the placement of each new part within 12 mm of its anchor (`place_fix.csv`).
Every fix that adds a part found room. F3a was added here (R15 pad 1 is the anchor, because U8 on `kicad-1rx/` is still the LTC2292 and the AD9237 CLK pin does not exist yet); F4b (Schottky clamps)
has not been searched, for the same reason, and F4a's settling and IF response have not been rerun. Layout and part choices are the user's.

# 10. The waveforms lay-03 should match at bring-up

Capture 12 V, 3V8, 3V0, 3V3A, 1V8, 3V3D, CLK and PDWN; times are from the simulation (12 V rise 1 ms assumed, not on file), so compare the order and the differences more than the absolute times.

{{fact:md_lay03}}

# 11. Result and what the user decides

1. **Order, FPGA:** choose F1c (a supervisor on 1V0, design) or F1b (RC on the U23 EN, timing), or accept 1V0 before 1V8 as timing. Power-off orders have no design fix (F2c).
2. **12 V removal, AD9237 pins:** choose one or accept it. F2a and F2b do not fix it with the TI U39 model; F4a lowers the VIN clamp current but not the voltage; no fix is simulated that
   passes every case. The alternative is to judge the {{fact:ns_clk_ma}} to {{fact:dn_clk_ma}} mA CLK clamp current acceptable against a sheet that gives none; a fix that stops the case is not yet simulated.
3. **CLK steady state:** F3a (divider) is the one that works; the choice of values stays open.
4. **Assumption 5 (PG at low VIN)** decides whether power-up passes with {{fact:up_clk_margin}} V of margin or fails by {{fact:vpgmin_2_up_over}} V; lay-03 should measure it.

Changes record: `docs/board-changes.md` rows `U24, U23 enables from 3V0`, `U8 (ADC), 1-RX` and `FPGA rail order` carry the result. A chosen fix becomes a row of `parts/rx1_changes.csv` for rx1-03; none is
chosen yet, so none is added.

Limitation of the saved data: `powerup_sim.py` saves 400 points per trace but 500 points in `up_ms` and `down_ms`; this report rebuilds the time axis from the 400 points and the window (0 to t_off - 1 ms, t_off - 0.5 ms to the stop).
