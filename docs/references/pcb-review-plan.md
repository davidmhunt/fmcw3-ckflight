# fmcw3-ckflight PCB Review Plan

Nov 18, 2026 · @David

## Summary

Review `davidmhunt/fmcw3-ckflight` on `main` (commit `b0dbb27`). Upstream says this version was tested on real hardware with the 100T FPGA (Aug 2026). The other upstream branches are already merged into `main`, except `oshpark_version`, which is older and out of date. Fab files (gerbers, drill, pick-and-place) are complete. The open work is parts bookkeeping and a careful RF review, not a redesign.

Work in this order, because each phase feeds the next:

1. **Parts and availability**: confirm everything can be bought before spending time on circuits that may change.
2. **RF chain**: understand each stage and check gain and power levels against the datasheets.
3. **Impedance and 50 Ω**: confirm the traces, stackup and fab choice give 50 Ω lines.
4. **Testability**: decide how you will check each stage when the board arrives.
5. **Schematic and layout checks**: triage the ERC/DRC reports and check power and grounding.
6. **Circuit simulation**: SPICE the supply-noise path to the VCO, the changed buck inductor and the IF filter.
7. **Spurs**: build a frequency plan of every clock and check it against the IF band and the PLL.

Phases 6 and 7 build on the Phase 2 level plan and feed the decisions on test points and filters in Phases 4 and 7, which must be settled before ordering.

Tonight's head start: the RF chain is traced from the KiCad files, the stackup is extracted, and first-pass impedance numbers are computed (Phase 3). The part-number lookups wait for tomorrow.

## Board at a glance

A 6-layer, 1.6 mm board with an Artix-7 FPGA, a 5.8 GHz chirp transmitter and two receive channels. Its stackup puts 0.11 mm of prepreg between each outer layer and a ground plane (L2 and L5), which suits narrow 50 Ω lines.

&#91;embedded content: fmcw3-ckflight RF chain · TX/LO path and two RX channels\]

The LO is tapped off the PA output through the printed coupler (highlighted), so TX power directly sets the mixer drive. That is the most important level to check in Phase 2.

## Phase 1: Critical parts and availability

The goal: every part has an exact, orderable part number and stock for 5 boards. Your last DigiKey run (`parts/availability.csv`) found 10 Active, 20 No-result, 2 needs-David and 1 NFND. The 20 No-results are base part numbers without ordering suffixes, not missing parts.

- [ ] Decide **XC7A35T vs XC7A100T** (U30). The BOM says 35T, but upstream's verified build says 100T. Both are FTG256 parts, so they share the footprint. The firmware repo ships bitstreams for both.
- [ ] Resolve suffixes for the 20 No-result rows into a new `parts/suffix_decisions.csv`, copying the format of `fmcw3`'s `kicad10-build` branch. For each part: open the ordering table in the datasheet and pick the code whose package matches the footprint.
- [ ] Decide `LTC2292` grade (C 0–70 °C vs I −40–85 °C). A UAV mount outdoors argues for I.
- [ ] Pick a USB-C receptacle that fits the `GCT_USB4105` footprint (USB4105-GF-A is the matching part).
- [ ] Replace `SRR6040A-330M` (L5–L7, NFND) with an active 33 µH part in the same 6×6 mm footprint. Check its saturation current against the LMR51420 buck's peak current.
- [ ] Re-run `python parts/check_digikey.py --boards 5` on your laptop and confirm no Obsolete or NFND parts remain.
- [ ] Fill LCSC part numbers (0 of 84 lines today) if JLCPCB will assemble. Check RF and specialty parts first: ADF4158, HMC431, ADL5802, SKY65404, TRF37A73, TQP5525, the 5400BL15 baluns and the PAT1220 pads. Those are the most likely to be Extended or consigned parts.

**Critical parts to review in depth** (datasheet first page, ordering table, recommended layout):

| Ref | Part | Role | Why it is critical |
| --- | --- | --- | --- |
| U1 | ADF4158 | Chirp PLL | Sets chirp linearity, so it limits range resolution |
| U10 | HMC431LP4 | 5.5–6.1 GHz VCO | Phase noise and tuning range |
| U14 | TQP5525 | TX power amp | Output power and heat; sets range |
| U11, U16 | SKY65404 | RX LNAs | Sets the receiver noise figure |
| U9, U13 | TRF37A73 | RX gain blocks | Compression point and gain |
| U29 | ADL5802 | Dual mixer | LO drive level and IF output |
| U26–U28 | 5400BL15B0050 | Baluns | Single-ended to differential for the mixer |
| U45 | LT6232 | IF amp / filter | Sets IF gain before the ADC |
| U8 | LTC2292 | Dual 12-bit ADC | Sample rate and input range |
| U30 | XC7A35T / 100T | FPGA | Variant must match the firmware |

## Phase 2: RF chain review

The goal: know the signal power at every node and confirm each part runs inside its limits. Build a **level-plan spreadsheet**: one row per stage, with columns for gain or loss (dB), output P1dB (dBm) and noise figure (dB). Then add a running total of power. Take every number from the datasheet at 5.8 GHz, not the headline figure.

**Transmit and LO path**

1. VCO (U10) output. Note its power at 5.8 GHz from the HMC431 datasheet.
2. Resistive splitter (R9, R11, R12, 16.9 Ω each). A 3-resistor star splitter has 6 dB loss to each output and stays matched at 50 Ω. Check: 50/3 = 16.7 Ω, so 16.9 Ω is the nearest standard value.
3. PLL branch: R12 → C11 → ADF4158 RFIN (C8 grounds RFINB). Check the power stays inside the ADF4158's RFIN range.
4. TX branch: R11 → 3 dB pad (U12) → C300 → PA (U14). Check the PA input level against its datasheet drive level, and the output against the 5.8 GHz ISM power limit you need.
5. PA → printed 15 dB coupler (Z1) → TX SMA (U15). R17 (49.9 Ω) terminates the isolated port.
6. LO: coupled port → 6 dB pad (U3) → `/LO` (drops to the bottom layer through vias F1/F2) → balun U26 → ADL5802 LO input. **Key check:** PA out − 15 dB − 6 dB − balun loss should land in the ADL5802's recommended LO drive range. Because the LO comes off the PA, the PA enable state changes the LO level. Confirm the mixer still works at the power level you'll actually run.

**Receive path (two identical channels)**

1. RX SMA (P1, P2) → 0.5 pF shunt (C48, C57), a matching element at the LNA input.
2. LNA SKY65404 (U11, U16) → 18 pF DC block → gain block TRF37A73 (U9, U13). L1/L3 (9.9 nH) are the TRF37A73's output bias chokes.
3. 18 pF → balun (U27, U28) → ADL5802 RF inputs.
4. Mixer IF out → LT6232 IF amp → LTC2292 ADC → FPGA.

**Checks for each stage**

- [ ] Gain, noise figure and P1dB at 5.8 GHz, entered in the level plan.
- [ ] Cascade noise figure (Friis). The LNA plus anything before it (connector, C48, trace loss) dominates.
- [ ] Strongest expected return (nearby targets plus TX→RX leakage between antennas) stays below the TRF37A73 and mixer P1dB.
- [ ] DC-block capacitors resonate near 5.8 GHz or are low-loss there. A typical 18 pF 0402 (about 0.4 nH of parasitic inductance) resonates near 2 GHz, so at 5.8 GHz it may look inductive. Pull the actual part's S-parameters and check its loss at 5.8 GHz.
- [ ] Bias networks: choke inductor self-resonance is above 5.8 GHz, and each VCC pin has the datasheet's decoupling.
- [ ] IF chain: beat frequency for your max range and chirp slope sits inside the LT6232 filter passband and below the ADC's Nyquist frequency.

Tools: a spreadsheet is enough for the level plan. For a quick cascade check, Python with `scikit-rf` reads the vendors' S-parameter (`.s2p`) files.

## Phase 3: Impedance and 50 Ω analysis

First-pass result: the 0.23 mm RF traces are about 50 Ω **only if they are grounded coplanar waveguide (CPWG)** with a 0.2 mm gap to a top-layer ground pour. As plain microstrip they come out at 43–45 Ω. Confirm which one the layout actually is; that is the main open question in this phase.

**What the board file says**

- Top-layer RF traces: 0.23 mm, narrowing to 0.17 mm at the IC pads. The LO net runs mostly on the bottom layer at 0.17 mm.
- Dielectric under the top layer: 0.1107 mm prepreg to L2 (GND). The bottom layer mirrors it to L5 (GND). Finished copper is 0.0432 mm.
- Top ground pour clearance: 0.2 mm. There are many keepout areas on the top layer, likely RF clearance zones.
- The file uses **εr 4.5 and tan δ 0.02**, which are KiCad's defaults, not the fab's numbers. Get the fab's real prepreg thickness and εr at around 5.8 GHz (FR4 prepregs are often nearer 4.1 at these frequencies).

**Computed impedance** (Hammerstad–Jensen microstrip; conductor-backed CPW from the elliptic-integral formula; `Python script, can be committed to the repo`)

| Trace width | Microstrip, εr 4.5 | Microstrip, εr 4.1 | CPWG 0.2 mm gap, εr 4.5 | CPWG 0.2 mm gap, εr 4.1 |
| --- | --- | --- | --- | --- |
| 0.17 mm | 50.3 Ω | 52.4 Ω | 56.8 Ω | 59.2 Ω |
| 0.20 mm | 46.3 Ω | 48.2 Ω | 51.7 Ω | 53.9 Ω |
| 0.23 mm | 43.0 Ω | 44.7 Ω | 47.5 Ω | 49.6 Ω |

Dielectric loss at 5.8 GHz with tan δ 0.02 is about 0.17 dB/cm, before copper loss. Keep the RX input runs short. A quarter wavelength on these lines is about 7.2 mm.

**Steps**

- [ ] In KiCad, measure the actual gap from each RF trace to the top ground pour, and check that the pour runs along both sides of each trace. A gap that widens to a keepout means microstrip for that stretch.
- [ ] Re-run the numbers in KiCad's Calculator Tools (Transmission Lines → Coplanar wave guide with ground plane) with the fab's εr and thickness. That checks this script independently.
- [ ] Order with the fab's **controlled-impedance** option and their exact stackup, and give them the 50 Ω target, layer and reference plane. Then set εr and thickness in KiCad's Board Setup → Physical Stackup to match.
- [ ] Check stitching vias along each RF trace's ground pour, spaced well under a quarter wavelength (roughly every 1–2 mm here).
- [ ] Check the LO layer change at F1/F2: ground-return vias right beside the signal via, and a 50 Ω line on the bottom layer as well. At 0.17 mm with a 0.2 mm gap, the bottom run computes to 57–59 Ω.
- [ ] Check the 0.4 mm balun-to-mixer traces. They are about 32 Ω single-ended, which is fine only if they are very short, are meant as a differential pair, or match the balun's output impedance.
- [ ] Check pad transitions: the 0.17 mm necks into QFN/DFN pads, and the SMA launch footprint (CONSMA003.062) versus the 0.23 mm line. Connector launches are the most common source of mismatch.
- [ ] Optional, if time allows: simulate the SMA launch and the LO via in openEMS (free 3D EM solver) for S11 at 5.8 GHz.

## Phase 4: Testability

The board can be split into stages for debugging at the IF and digital end, but not in the RF chain. There are no test points on the power rails and no RF test ports between stages. Decide tonight or tomorrow whether to add any before ordering, because afterwards the only fix is rework.

**What exists**

| Access | Refs | What it lets you do |
| --- | --- | --- |
| Solder jumpers, mixer IF → IF amp | JP9–JP12 | Cut the mixer off and inject a test tone into the IF amp, or probe the raw mixer output |
| Solder jumpers, IF amp → ADC | JP5–JP8 | Test the ADC alone from a signal generator |
| Solder jumpers, FT2232 → FPGA JTAG | JP1–JP4 | Use an external JTAG programmer if the FT2232 path fails |
| 2×8 header, 12 FPGA pins + 3V3 + GND | J2 | Debug GPIO, logic-analyzer taps, triggers |
| RX SMAs, TX SMA | P1, P2, U15 | Whole-chain RF tests only |
| LEDs, 2 buttons, SD card | D1–D7, SW1–SW2, CON1 | Status and basic I/O |

**Gaps worth closing before you order**

- [ ] Add a test pad (or 0402 0 Ω link) on each regulator output: 12 V, 10 V, 5V6, 5 V, 3V8, 3V3A, 3V3D, 3V0, 1V8, 1V0. That lets you bring up one rail at a time and measure current.
- [ ] Consider a coax test point on `/LO` and at the PA output before the coupler: a u.FL footprint left unpopulated, or a 0402 that can be rotated to divert the signal. You can't easily probe 5.8 GHz any other way.
- [ ] Add a probe pad on the ADF4158 MUXOUT and on VTUNE (with a ground pad next to each) so you can watch PLL lock and the chirp ramp on a scope.

**Bring-up order** (each step passes before you power the next)

1. Bare board: check for shorts from each rail to GND with a meter.
2. Power from a current-limited bench supply at 12 V. Check every rail voltage and the total current.
3. FT2232 enumerates over USB, then JTAG sees the FPGA, then a bitstream loads (from the firmware repo, matching 35T or 100T).
4. Program the ADF4158. Check MUXOUT lock detect, then VTUNE with a scope while chirping.
5. TX out on a spectrum analyzer (through an attenuator): frequency, sweep and power.
6. Loop TX → attenuator → RX SMA. Check the IF beat tone at the JP9–JP12 pads, then in ADC samples.
7. Antennas on, a corner reflector at a known range, and check the range FFT.

**Equipment**: a current-limited bench supply, scope, multimeter, spectrum analyzer covering 6 GHz (a TinySA Ultra is a cheap option, but it is not a precision instrument), SMA attenuators (20–30 dB), and ideally a VNA for S11 of the SMA ports and antennas (a LiteVNA reaches 6 GHz).

## Phase 5: Schematic and layout checks

The check reports look much worse than the board is. Of 1,118 ERC and 410 DRC items, about 1,500 are library, grid or cosmetic warnings. DRC shows **0 unconnected items and 0 schematic/PCB mismatches**, so layout and schematic agree.

| Report | Count | Type | What it means | Action |
| --- | --- | --- | --- | --- |
| ERC | 558 | lib\_symbol\_issues | Symbols differ from your installed libraries | Ignore, or update symbols later |
| ERC | 335 | footprint\_link\_issues | Footprint library names not found locally | Fix the lib tables so the project's own libraries load |
| ERC | 222 | endpoint\_off\_grid | Wires off grid | Cosmetic, ignore |
| ERC | 2 | pin\_to\_pin | Flash U40 WP/HOLD tied to the 3.3 V LDO output (U25) | Fine: these pins should be pulled high. Exclude it |
| ERC | 1 | power\_pin\_not\_driven | GND has no power flag | Add a PWR\_FLAG on GND |
| DRC | 200 | solder\_mask\_bridge | Mask web between fine-pitch pads | Check against your fab's minimum mask web; usually fine |
| DRC | 199 | lib\_footprint\_issues | Footprints differ from library copies | Ignore |
| DRC | 6 | isolated\_copper | Islands of 12V (L6), 5V6 and 3V3A (L3) pour | Remove the islands (set the zones to drop islands) |
| DRC | 4 | clearance | The printed 15 dB coupler Z1's copper shape touches its own pads | Expected for a printed footprint. Confirm the shape matches the intended coupler geometry, then exclude |

**Checks the reports can't do for you**

- [ ] Each IC's power pins: decoupling values and placement match its datasheet's recommended layout (smallest capacitor closest to the pin).
- [ ] Exposed pads on QFN/DFN parts (PA, LNAs, VCO, mixer, regulators) have the via counts the datasheets ask for. That matters for both grounding and heat. The TQP5525 needs the most.
- [ ] Buck regulators (U17–U19, LMR51420): switch-node copper is small and kept away from the RF area. Their switching noise should not land in the IF band.
- [ ] Continuous ground under every RF trace on L2 and L5, with no splits or slots.
- [ ] RX and TX SMA spacing and antenna isolation (TX→RX leakage feeds the RX compression check in Phase 2).
- [ ] Delete the stray `~_autosave-fmcw3.kicad_pcb.lck` file before opening the board in the KiCad GUI.
- [ ] Re-run ERC/DRC in the KiCad version you'll order from. Opening the KiCad 9 project in KiCad 10 converts it on save.

## Phase 6: Circuit simulation (SPICE)

Simulate where the board's behaviour can hurt the radar or where you are changing a part. Skip rails that upstream already proved on hardware and that you aren't touching. In an FMCW radar, ripple on the VCO and PLL supplies becomes spurs and false targets in the range FFT. That makes supply noise the main reason to simulate here.

**Power tree (from the board file)**: 12 V → three LMR51420 bucks (U17–U19) → low-noise LDOs. 3V8 → LP5907 (U20) → 3V0 → ferrite beads → VCO, LNAs and gain blocks. 3V8 → LD3920 (U24) → 3V3A → PLL and IF amp. 5V6 → LD3920 (U22) → 5V → ferrite beads → mixer and PA. 3V8 also feeds 1V8 and 3V3D for the digital side. U21 and U7 make the 10 V tuning supply.

| Priority | What to simulate | Why | Tool |
| --- | --- | --- | --- |
| 1 | Buck ripple → LP5907 → ferrite bead + capacitors → VCO supply (3V0 branch) | Ripple that gets through becomes FM spurs in the chirp. Ferrite-bead-plus-capacitor filters can also peak (resonate) and amplify noise at one frequency | LTspice, with the LDO's PSRR curve from its datasheet and the bead's impedance model from its vendor |
| 2 | The buck with your replacement 33 µH inductor (L5–L7) | A new inductor changes ripple current, saturation margin and loop stability | TI WEBENCH or TI's PSpice model for the LMR51420 |
| 3 | IF amp and filter (LT6232) AC response | Confirms the passband covers your beat frequencies and rolls off below the ADC's Nyquist frequency | LTspice (ADI's LT parts have built-in models) |
| 4 | PLL loop filter and VTUNE drive (ADF4158 + U7) | Loop bandwidth sets chirp linearity and settling time | ADIsimPLL (ADI's free tool), better suited than SPICE |
| Skip | Digital rails (1V0, 1V8, 3V3D), LDO DC operating points | Low risk, and already proven on upstream hardware | — |

- [ ] For each simulation, write down the pass limit before you run it, for example "ripple at VCO VCC below X µV". Derive X from the HMC431's pushing figure (MHz/V) and the spur level you can tolerate.
- [ ] SPICE ignores layout parasitics, so treat these results as best case. Confirm with a spectrum analyzer on the TX output at bring-up: look for spurs offset from the carrier by the buck switching frequency.

## Phase 7: Spurs and their effect on the RF chain

In an FMCW radar, a spur in the IF band shows up as a fake target at a fixed range. In SAR imagery that becomes a stripe across the image. Spurs on the chirp itself (FM sidebands) make ghost copies beside every strong target. The goal of this phase is a **frequency plan**: every clock on the board and its harmonics, checked against the IF band and against offsets from the carrier.

**Spur sources on this board**

| Source | Frequency | Path into the radar | Shows up as |
| --- | --- | --- | --- |
| Buck converters U17–U19 | LMR51420 switching frequency (check which variant is fitted) and its harmonics | Supply ripple → VCO pushing; also directly into the IF amp and ADC supplies | Sidebands at ±f\_sw on TX; a fixed tone in the IF band if f\_sw or its harmonics fall inside it |
| Reference TCXO Y2 via buffer U6 | Likely 40 MHz (check the ECS part's datasheet) | PLL reference, ADC clock and FPGA clock share it | PLL reference spurs at ±PFD frequency; clock coupling into the IF |
| ADF4158 fractional-N | Integer-boundary spurs where the RF frequency nears a multiple of the PFD frequency | Inside the PLL | Spurs that move as the chirp sweeps, so they may appear only at certain parts of the chirp |
| USB crystal Y1, FT2232 | 12 MHz, and the 60 MHz USB clock | Digital ground and supply noise | Tones in the IF or ADC data |
| FPGA and ADC data lines | System clock, ADC sample rate, data-bus activity | Ground bounce, coupling into the IF traces | Tones in the IF; aliasing if the anti-alias filter is weak |
| PA and VCO harmonics | 11.6 GHz, 17.4 GHz | **No filter between the coupler and the TX SMA** | Out-of-band emissions; a regulatory issue more than a radar one |
| TX→RX leakage | Beat at near-zero range | Antenna coupling and board coupling | A very strong close-range tone that can compress the RX chain (Phase 2) |

**Steps**

- [ ] Fill the frequency column with actual numbers: buck f\_sw, TCXO frequency, PFD frequency, ADC sample rate, FPGA clocks.
- [ ] Compute the IF band: maximum beat frequency = 2 × max range × chirp slope / c. List every clock harmonic that lands inside it. A short Python script does this.
- [ ] Model the PLL in ADIsimPLL (reference spurs, fractional spurs, phase noise) with the actual PFD frequency and loop filter. Move the PFD frequency or chirp band if a fractional spur lands in band.
- [ ] Turn the Phase 6 VCO-supply ripple result into a spur level: FM sideband ≈ 20 log10(K\_push × V\_ripple / (2 f\_sw)) dBc, using the HMC431's pushing figure.
- [ ] Phase noise: check that the noise at the IF offsets of your strongest close target (TX leakage) doesn't raise the floor where weak targets sit. Range correlation cancels some of it at short range.
- [ ] Decide whether to add a low-pass or band-pass filter footprint before the TX SMA. Harmonics at 11.6 GHz count against the ISM-band emission limits.
- [ ] At bring-up, take a capture with the TX terminated in a load and no antennas. Every peak in that range FFT is an internal spur. Then a spectrum-analyzer sweep of the TX output, looking for sidebands at ±f\_sw and ±PFD around the carrier.

## Open questions

- [ ] FPGA: XC7A35T or XC7A100T?
- [ ] Fab and assembly: JLCPCB full assembly, or bare boards plus hand or consigned assembly for the RF parts? This decides whether LCSC numbers matter.
- [ ] Fab stackup: which controlled-impedance 6-layer stackup, and its εr and prepreg thickness? This sets the final trace widths.
- [ ] KiCad 9 or KiCad 10 for this board (and the Docker vs native question from your KiCad agent setup)?
- [ ] Add power-rail test pads and RF tap points before ordering (Phase 4), or build as-is first?
- [ ] Target TX power and maximum range, which feed the PA drive and IF-band checks.
- [ ] Antennas: which ones, and their 5.8 GHz match and TX/RX isolation?
- [ ] Licence: upstream is GPLv3. Is that fine for how you plan to use and share this board?
