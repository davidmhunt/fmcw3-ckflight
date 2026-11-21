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

### 2026-11-21
Commits:
- 21210ae targets: the user's band 5.60-5.90 GHz, 300 MHz chirp, 25 dBm TX (status set, notes updated); target tests read the values instead of pinning the old ones
- f42ba00 par-07 step 2: PA candidate search; SE5004L and SE5023L datasheets on file, QPA9501 and AWL9924 pending for the user
- d996590 par-07 step 4: 02_pa report and deck: requirements, comparison, one slide per candidate, labelled recommendation
Notes:
- Step 1 (requirements for U14 replacement). Read headless: `kicad-cli sch export netlist` of kicad/fmcw3.kicad_sch (sheet tx), track lengths from kicad/fmcw3.kicad_pcb (read only; KiCad status was closed). Nothing under kicad/ was changed.
- Comparison basis: FMCW is constant envelope, so compare P1dB and Psat at 5.8 GHz and the gain/current at the target power, not the WLAN EVM powers (+18 dBm VHT80, +25 dBm HT40) in the TQP5525 datasheet.
- R1 band: 5.60 to 5.90 GHz (target set `default`, design.freq_min_ghz / freq_max_ghz, status set). Candidate must cover the whole 5.60-5.90 GHz, not only the 5.725-5.875 GHz ISM band.
- R2 TX power: 25 dBm at the antenna (target `default`, design.tx_power_dbm = 25, status set). Required at U14 output = 25 dBm + loss U14 to SMA (R6) = about 25.5 dBm.
- R3 temperature: -40 to +85 C (TQP5525 datasheet qorvo-tqp5525-datasheet p2, TOPERATING at package ground). The board has no stated temperature target of its own, so the TQP5525 range is the baseline.
- R4 U14 connections (netlist, sheet tx; U14 = TQP5525, footprint Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias):
- supply: pins 18 (VCC3), 19 (VCC2) on net Net-(U14-VCC2), pin 20 (VCC1) on Net-(U14-VCC1) joined to VCC2 by R302 27 ohm; all fed from net /5V through ferrite FB4 (BLM18PG181SN1D). Decoupling C301 100n, C302 100n, C303 10u, C304 220p. Pin 9 (VCC3) is NOT on the supply: it sits on Net-(C306-Pad2) with C306 10u to GND and C307 220p + R305 2 ohm to GND (a decoupling-only stub; the datasheet pin table, p8, calls pin 9 "VCC3 Supply voltage"). Worth the user checking against the TQP5525 eval board (datasheet p4 BOM lists 2 ohm resistors R5, R6); not a replacement requirement but a candidate with a different pin 9 function must be checked here.
- rail voltage: /5V = 5.0 V, set by U22 LD3920 (ST LD39200 adjustable) with R43 18k / R44 2k: Vout = 0.5 V x (1 + 18k/2k) = 5.0 V (st-ld39200-datasheet p9 eq. 2, VADJ 0.5 V p6). U22 input is /power/5V6 from the buck U19 LMR51420 (2 A, ti-lmr51420-datasheet p1) via L7 33u.
- regulator limit: LD39200 2 A guaranteed, internally limited at typically 3.5 A (st-ld39200-datasheet p1 and p9). The buck U19 is 2 A continuous. Other loads on /5V: FB2 to ADF4158 VP (U1), FB13 to /mixer/5VF, FB4 to U14 (so U14 shares the 2 A budget with them; their currents not summed in this step).
- ferrite in the supply path: FB4 BLM18PG181SN1D rated 1000 mA (murata-blm18pg181sn1d-datasheet p1, 0.18 ohm max DCR). TQP5525 at +24 dBm needs 600 mA typ / 675 max, at +27.5 dBm 750 / 850 (qorvo-tqp5525-datasheet p3). So the 1 A ferrite is the real current limit of the supply branch, not the regulator: a candidate above about 0.8 A at 25 dBm out needs FB4 changed (and the datasheet derates the BLM18PG at temperature, p4).
- enable: pin 5 PA_EN on net /PA_EN, driven by U30 pin T2 (IO_L8N_T1_34), with R300 1k pull-down and LED D5 (+R301 1k) from /PA_EN. Datasheet: high >= 1.8 V, low <= 0.45 V, 20-100 uA (qorvo-tqp5525-datasheet p2, p3). Bank 34 VCCO not checked here.
- detector: pin 10 DET on Net-(U14-DET): R304 27.4k to GND, C305 220p, R18 0 ohm to /DET_OUT which goes to U30 pin C7 (IO_L5P_T0_AD13P_35, an XADC auxiliary input), plus test pad U36. TQP5525 detector 0.25-0.38 V no RF, 0.80-1.20 V at +27.5 dBm (p3). Pin 7 DET_ALT and NU pins 6, 8 are unconnected. A replacement with a different detector range or none changes what the XADC sees (XADC input range is 0 to 1 V, to be confirmed from ug480; not read here).
- RF input: pin 3 RFIN via C300 10 pF from U12 (PAT1220-3dB attenuator), which is fed from R11 16.9 ohm, one leg of a 3-resistor splitter (R9, R11, R12, 16.9 ohm each) driven by the VCO U10 HMC431LP4 RFOUT (pin 16). The third leg R12 goes through C11 to the PLL (ADF4158 side).
- RF output: pin 13 RFOUT on Net-(U14-RFOUT) goes to Z1, a printed 15 dB directional coupler (footprint Directional_Coupler_15dB_0.169mm_v2): port 1 in from U14, port 2 through to Net-(U15-Pad1) = antenna SMA U15, port 3 coupled to U3 PAT1220-6dB then net /LO (mixer LO via U26 5400BL15B0050001E), port 4 terminated by R17 49.9 ohm.
- R5 drive level at U14 RFIN: HMC431LP4 Pout +2 dBm typ, -1 dBm min at 5.5-6.1 GHz, 3 V (adi-hmc431lp4-datasheet p1). The 16.9/16.9/16.9 ohm resistive splitter loses 6.1 dB per output (computed: Vout/Vin = 0.4965, matched 50 ohm legs). U12 PAT1220-3dB: 3 dB nominal, tolerance +/-0.3 dB (pat1220-attenuator-datasheet p1), but the datasheet operating frequency for PAT1220 is DC to 3 GHz, so its value at 5.8 GHz is outside the rated range (flag). C300 10 pF series loss assumed about 0.1 dB (not from a datasheet). Drive = +2 - 6.1 - 3 - 0.1 = about -7.2 dBm typ; -1 dBm VCO gives about -10.2 dBm. (VCO power at 5.8 GHz over temperature, and its 6 dB output return loss mismatch to the splitter, are not included.) The VCO figure is a 25 C typical; its Vcc/Vtune/temperature plots are on p2-3 of the datasheet and were not read.
- R6 loss U14 to antenna SMA: no datasheet exists (printed coupler). Lower bound 0.14 dB, the through loss of an ideal 15 dB coupler, 10 log10(1 - 10^-1.5). Routing from the PCB: RFOUT stub 0.98 mm plus 2.28 mm to the SMA, all F.Cu at 0.17 mm width, total about 3.3 mm of line plus the coupler body. Working figure for the requirement: 0.5 dB (assumption, labelled as such in the report; not measured).
- Derived requirement: at the SMA 25 dBm means 25.5 dBm out of the PA. Needed gain = 25.5 - (-7.2) = 32.7 dB at typical VCO power (35.7 dB at the -1 dBm VCO minimum). Baseline TQP5525 gain is 29 min / 32 typ / 37 max at 5150-5925 MHz (qorvo-tqp5525-datasheet p2), so the original part gives about 24.8 dBm out typ (about 24.3 dBm at the SMA), i.e. at or slightly under the 25 dBm target; this is a finding for the report, not a decision. P1dB 30 min / 32 typ and Psat +34 typ at 5250-5925 MHz (p3) leave about 4.5 dB of headroom at 25.5 dBm (against the 30 dBm minimum), so the stage is linear at the target and gain, not compression, sets the output.
- Baseline TQP5525 (qorvo-tqp5525-datasheet): 4900-5925 MHz (p1, p2); Vcc 3.15/5/5.25 V (p2); gain 29/32/37 dB at 5150-5925 MHz (p2); P1dB 30/32 dBm and Psat 34 dBm typ at 5250-5925 MHz (p3); current at +24 dBm 600 typ / 675 max, +27.5 dBm 750 / 850 (p3), interpolated at +25.5 dBm about 665 mA typ / 750 mA max; quiescent 350 / 400 mA (p3); theta-jc 17 C/W to the backside paddle (p3); max RFIN +5 dBm (p2); QFN-20 4x4 mm (p1), pinout p8, mounting pattern p10; MSL 1 (p11). Dissipation at 5 V and 25.5 dBm (0.35 W RF out): about 5.25 x 0.75 - 0.35 = about 3.6 W worst case (a computed estimate); junction rise through the paddle 17 C/W x 3.6 W = about 61 C above the paddle, against the 85 C paddle ceiling gives about 146 C vs the 170 C junction limit (p2).
- Rail check for a candidate: needs 5 V (or the board rail changed), current at 25.5 dBm output below about 0.8 A through FB4 (1 A rating, derated) and within the 2 A rail shared with ADF4158 and mixer loads.
- Lifecycle: the user reports TQP5525 discontinued (parts/decisions.csv, 2026-11-21); current stock is a step 2 item.
- Check run: the netlist export and the track/page reads above, no tracked files changed, nothing to commit.
- Step 2 (candidate search, 2026-11-21). Sources: DigiKey Product Information API (parts/check_digikey.py Client, about 30 keyword searches over band, power and family names) and the local JLC parts database (parts/cache/jlcpcb, by MPN and text). Nothing under kicad/ read or changed; decisions.csv and schematic unchanged.
- Remaining-stock option "buy the remaining TQP5525 for this build": DigiKey has no TQP5525 listing (keyword and MPN searches return 0 products: DigiKey stock 0 / not listed). JLC C471153 (Extended, QFN-20-EP 4x4) shows stock 100 on 2026-11-21 (database snapshot); 3 boards need 3 parts. JLC price is in the database column, to be read in step 3. Lifecycle: discontinued per the user (decisions.csv), so the stock is a finite pool to re-check before ordering. No other distributor API was queried.
- Shortlist rule: DigiKey RF amplifiers, status Active, supply range includes 5 V (or the one 3.3 V part noted), frequency range reaching 5.6-5.9 GHz, P1dB at least 30 dBm parametric (need about 25.5 dBm at U14 output, step 1 R2/R6). Four parts plus the TQP5525 stock option (max six).
- C1 Qorvo QPA9501TR13: DigiKey parametric 4.9-5.9 GHz, P1dB 33 dBm, gain 36 dB, 3.15-5.5 V, 20-VFQFN (JLC C2911573 says QFN-20-EP 4x4); DigiKey Active stock 12947, 6.28 USD; JLC stock 20. Datasheet NOT on file: qorvo.com answers every download with HTTP 429 (Vercel bot challenge; DigiKey link, 2 user agents, a 60 s wait). Manifest entry qorvo-qpa9501-datasheet is pending (form, datasheets/files/qorvo/qpa9501.pdf): "for the user to obtain", not scored from memory or from the DigiKey parametric text. Likely the strongest candidate once the PDF is on file (same maker, band and package), so fetching it is the user's first action.
- C2 Skyworks SE5004L-R: DigiKey parametric 5.15-5.85 GHz, P1dB 34 dBm, gain 32 dB, 3-5.5 V, 20-VFQFN; DigiKey Active stock 193272, 4.70 USD; JLC C210263 stock 1181 (a Tokmas-labelled SE5004L-R(TOKMAS), C55090141, stock 3000, is a relabel: treat with care). Datasheet on file: skyworks-se5004l-datasheet (doc 202393B, 23 Oct 2012). Read from the file: QFN-20 pinout p2 matches TQP5525 (VCC1 pin 20, VCC2 19, VCC3 18, RFIN 3, RFOUT 13, DET 10); Vcc 3.0-5.5 V and case -40 to +85 C p3; Icc 600 typ / 800 max mA at 26 dBm (802.11a), Iq 300 mA p3; frequency 5.15-5.85 GHz, P1dB 30 min / 34 typ, gain 30/32 dB at 5.4 GHz p4; detector 0.325 V no RF, 1.0 V at 27 dBm p5. Flags for step 3: range stops at 5.85 GHz (board band goes to 5.90 GHz); figures are at 5.4 GHz, not 5.8 GHz; enable is VREF pin 5 at 2.80-2.90 V analog (p3), not a logic PA_EN, so U30 pin T2 cannot drive it without a 2.85 V reference.
- C3 Skyworks SE5023L-R: DigiKey parametric 5.15-5.85 GHz, P1dB 34 dBm, gain 34 dB, 3-5.5 V, 20-VFQFN; DigiKey Active stock 4761, 4.96 USD; JLC C19271853 stock 0. Datasheet on file: skyworks-se5023l-datasheet (doc 202521B, 23 Sep 2014). Read: same pinout p2, Vcc 3.0-5.5 V and case -40 to +85 C p3, Icc typ 600 mA at 26 dBm and Iq 150-300 mA p3, frequency 5.15-5.85 GHz p4; same VREF 2.85 V enable. Marketed as the +24 dBm 802.11ac part, so P1dB/Psat at 5.8 GHz must come from its tables 5-6 and curves in step 3, not the DigiKey 34 dBm.
- C4 Anadigics AWL9924RS34P8 (active only as Rochester Electronics stock; the maker is gone): DigiKey parametric 4.9-5.9 GHz, P1dB 29 dBm, gain 34 dB, 3-3.6 V only, 24-TFQFN; DigiKey stock 4500, 2.76 USD; not in the JLC database. A 3.3 V part with a 24-pin package: needs a rail change and a footprint and layout change. Datasheet NOT on file: the DigiKey link (rocelec.widen.net) returned an HTML page; manifest entry anadigics-awl9924-datasheet is pending (form): "for the user to obtain". Lifecycle risk: a discontinued maker's stock is a weak replacement for a discontinued part.
- O0 keep TQP5525 (stock above): datasheet on file (qorvo-tqp5525-datasheet); same footprint, rail and pins, no board change.
- Considered and not shortlisted: Obsolete at DigiKey: SE5003L, SE5003L1, SE5003L2, SE5010L, SE5017L, SKY85402-11, LX5531LQ, LX5532LQ, HMC408LP3(E), RMPA5255, RMPA2550, SE2537L, STA-6033Z, FMPA2151, ATR3515, SST11CP15, SKY66288. Too low power, 3.3 V, or band stops at 5.75: SE5022T, SE5005L, PRFS-P5022-008. LNAs and drivers: TL0301H, NJG1175KG1. Wrong supply or band: ZVE-3W-83+ (15 V module), MGA-495940, MGA-515844, QPA0506 (25-28 V GaN), FM/PE modules, QPA0023, MAAP. Front-end modules with switch and LNA, not a PA drop-in: QPF4528, RFFM4558, SKY85743, SKY85614. HMC407MS8GE (JLC C662140, 5-7 GHz, 5 V, MS8 package): JLC stock 0, no DigiKey listing found; not pursued.
- DigiKey parametric data has no Psat or supply current; step 3 takes both from the datasheets, and where DigiKey text and datasheet differ the datasheet is the figure.
- Tracked changes: datasheets/manifest.yaml (+4 entries: skyworks-se5004l-datasheet and skyworks-se5023l-datasheet downloaded and hashed through fetch_sources --add; qorvo-qpa9501-datasheet and anadigics-awl9924-datasheet pending form entries) and docs/user-fetch.md (regenerated, +2 rows). `fetch_sources.py --check` prints "sources check: ok". No MANUAL.md change: no tool or ./run mode changed.
- Step 3 (per-candidate figures, 2026-11-21). Read from the PDFs in datasheets/files (pdftotext and a page render); JLC stock and price from the local JLC database (parts/cache/jlcpcb, snapshot of 2026-11-21); DigiKey stock and price are the step 2 API values (qty-1 price). Page numbers are the printed page numbers, which equal the PDF page numbers. Stock need for 3 boards is 3 parts (plus spares at the user's choice). U14 pin nets re-read headless from the netlist (kicad-cli, KiCad status closed, nothing under kicad/ changed): pin 1 GND, pin 5 /PA_EN, pins 6, 7, 8 unconnected, pin 9 Net-(C306-Pad2) decoupling stub, pin 10 detector net, pin 18 and 19 supply, pin 20 VCC1, pins 2, 4, 11, 12, 14-17 and the paddle (21) GND.
- Supply basis for every candidate: board rail /5V = 5.0 V (step 1 R4), LD39200 2 A guaranteed, FB4 1000 mA (derated). Output needed at U14 = 25.5 dBm; drive at RFIN about -7.2 dBm typ, -10.2 dBm with the -1 dBm VCO minimum (step 1 R5). Dissipation below = 5.0 V x I - RF output 0.355 W (25.5 dBm). Step 1 used 5.25 V for the TQP5525 (3.6 W); at the 5.0 V rail the TQP5525 is typ 0.665 A (interpolated, see step 1) 3.0 W, max 0.75 A 3.4 W.
- O0 TQP5525 (stock option), qorvo-tqp5525-datasheet: frequency 4900-5925 MHz p1, p2 (covers 5.60-5.90). Gain 29/32/37 dB at 5150-5925 MHz p2 (no figure given at 5.8 GHz itself; this is the band spec). P1dB 30 min / 32 typ and Psat 34 typ at 5250-5925 MHz p3. Current 600/675 mA at +24 dBm and 750/850 mA at +27.5 dBm p3; Vcc 3.15/5/5.25 V p2. Thermal: theta-jc 17 C/W to the backside paddle p3, Tj max 170 C p2, operating -40 to +85 C at package ground p2. Package QFN-20 4x4 mm p1, mounting pattern p10, pinout p8; it is the existing footprint and pinout, no board change. Enable PA_EN logic 1.8 V high p2. Detector 0.25-0.38 V no RF, 0.80-1.20 V at +27.5 dBm p3. MSL 1 p11. Lifecycle: discontinued (user report, decisions.csv). Stock: JLC C471153 (Extended) 100, price 7.341 USD at 1, 6.362 at 10 (3 boards: about 22.0 USD for 3 at the 1-piece price); DigiKey not listed (0). Fits existing supply: yes, 0.75 A is under the 1 A ferrite FB4 only with thin margin (step 1). It already is the design, so the finding to carry forward is the original gain shortfall (about 24.8 dBm typ out, about 24.3 dBm at the SMA, below 25 dBm).
- C2 SE5004L-R, skyworks-se5004l-datasheet (doc 202393B): frequency 5.15-5.85 GHz p4 (stops 50 MHz below the 5.90 GHz band edge; 5.85-5.90 uncharacterised). Gain 30 min / 32 typ at 5.4 GHz, Pin -25 dBm p4; gain variation 3 dB within each UNII band p4; no figure at 5.8 GHz (not a stated number). P1dB 30 min / 34 typ at 5.4 GHz, no modulation p4; Psat not given in the datasheet. Output at the drive: 32 dB typ gives 24.8 dBm out of the PA (same as the TQP5525), 30 dB min gives 22.8 dBm; 25.5 dBm is 8.5 dB under typ P1dB (4.5 dB under the 30 dBm min), so it is linear. Supply 3.0-5.5 V p3, board 5.0 V is within; abs max 6 V p3. Current 600 typ / 800 max mA at 26 dBm 802.11a 54 Mbps p3 (a modulated figure; CW at the same power is not given), quiescent 300 mA p3; 0.8 A max is at the edge of FB4's 1 A derated rating and 3.0 W typ / 3.6 W max dissipated at 5.0 V. The 2 A LD39200 is not the limit. Thermal: exposed pad 2.50 mm square p6 (Figure 4), land pattern p7; no theta-jc or thermal resistance in the datasheet (cannot compute junction temperature from the file); Tj max 160 C p3, case max +85 C p3; the margin 160-85 = 75 C over 3.6 W would need theta-jc under about 21 C/W, which the datasheet does not state. Package 20-pin QFN 4x4x0.9 mm, 0.5 mm pitch p1, p6: the same body, pitch and 2.5 mm paddle as the board footprint (QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm), pins 3 RFIN, 13 RFOUT, 10 DET, 18/19/20 VCC identical to the TQP5525 (p2 pinout). Pin differences: pin 5 is VREF, an analog enable of 2.8-2.9 V with about 10 mA bias control current and an internal 2 k pull-down (p3), not a 1.8 V logic input: U30 pin T2 cannot drive it directly (it needs a 2.85 V reference and a switch), a schematic change on sheet tx plus the FPGA side; pins 6 and 7 are SP1 and SP2 (optional EVM capacitors, unconnected on the board, fine); pin 8 is VCC2 (second-stage supply) and is unconnected on the board (it is NU on the TQP5525): whether it must be supplied is not stated in the datasheet and the SE5004L-EK1 eval board schematic is not on file, so this is for the user to check; pin 9 is VCC3 and sits on the decoupling stub like the TQP5525's. Detector 0.325 V no RF, 1.0 V at 27 dBm p5, DC load 26.5 k p5 (board R304 27.4 k). MSL3 p1. Lifecycle: DigiKey Active (step 2); the datasheet is 2012. Stock: DigiKey 193272 at 4.70 USD; JLC C210263 stock 1181 at 4.191 USD (1), 3.909 (10); Tokmas relabel C55090141 stock 3000 at 3.406, not the Skyworks part, treat with care. For 3 boards: about 14.1 USD at DigiKey, 12.6 USD at JLC.
- C3 SE5023L-R, skyworks-se5023l-datasheet (doc 202521B): frequency 5.15-5.85 GHz Table 5 p4 (same 5.85 GHz stop). Gain 28 min / 32 typ / 34 max at 5.4 GHz p4 (the drive gives 24.8 dBm typ out of the PA, 20.8 dBm at the minimum gain and the -1 dBm VCO), variation 3 dB within each UNII band p4, none at 5.8 GHz. P1dB +34 typ only at 5.4 GHz p4 (no minimum, no Psat). Supply 3.0-5.5 V p3. Current 600 typ mA at 26 dBm 802.11a, no maximum given p3, quiescent 150-300 mA p3; the maximum is not stated, so the FB4 1 A check cannot be closed from the file (at the SE5004L's 0.8 A the ferrite is marginal). Dissipation typ 3.0 W at 5.0 V (same arithmetic as above); max not computable. Thermal: exposed pad 2.50 +/- 0.05 mm p7, via pattern 25 holes 0.254 mm and 4 holes 0.457 mm p6; no theta-jc in the datasheet; Tj max 160 C, case +85 C p3. Package 20-pin QFN 4x4x0.9 mm, 0.5 mm pitch, MSL1 p1, p7: same body, pitch and paddle. Pin differences: pin 1 is VREF (the TQP5525 and the board have pin 1 on GND) so a layout change is needed to lift pin 1 off ground, plus pin 5 VREF is the analog 2.80-2.90 V enable (10 mA, 2 k pull-down, p3, p4) as for the SE5004L; pins 6, 7 SP1/SP2 and pin 8 VCC2 as for the SE5004L (p2). Detector 0.22-0.33 V no RF, 0.8-1.2 V at 26 dBm p4, DC load 26.5 k p4. Lifecycle DigiKey Active; datasheet 2014. Stock: DigiKey 4761 at 4.96 USD; JLC C19271853 stock 0 at 5.65 USD (1), so JLC cannot supply 3 boards; DigiKey for 3 boards about 14.9 USD.
- C1 QPA9501TR13 and C4 AWL9924RS34P8: datasheet not on file, so no gain, P1dB, Psat, current, thermal or pinout figure is scored; listed "for the user to obtain" (manifest ids qorvo-qpa9501-datasheet and anadigics-awl9924-datasheet, pending). Listing data only (not datasheet numbers): QPA9501 DigiKey Active, stock 12947, 6.28 USD; JLC C2911573 stock 20, 6.45 USD at 1 (3 boards: 18.8 USD DigiKey, 19.4 USD JLC); package QFN-20-EP 4x4 per JLC, footprint fit unconfirmed until the datasheet is read. AWL9924: DigiKey (Rochester Electronics) stock 4500, 2.76 USD, not in JLC; 24-pin package and 3.0-3.6 V supply per DigiKey parametric, so it would need a rail change and a new footprint (to be confirmed from the datasheet); the maker is gone.
- Cross-cutting findings for the report: (1) neither SE datasheet states Psat, gain at 5.8 GHz, or thermal resistance, and both stop at 5.85 GHz, so only the TQP5525 covers the whole 5.60-5.90 GHz band by datasheet; (2) every SE candidate has the same typ gain as the TQP5525, so the output stays near 24.8 dBm out of the PA, below the 25.5 dBm needed; (3) the SE parts are footprint and pin compatible except the enable (analog VREF 2.85 V) and, for SE5023L, pin 1 VREF; (4) current at 0.6-0.8 A is limited by the 1 A ferrite FB4, not the 2 A regulator. Recommendation is the user's choice; the likely order once the QPA9501 datasheet is on file is QPA9501 first (same maker and band, to be confirmed), then SE5004L.
- Check run: the step 3 figures were read from the PDFs and database as above and are recorded here; no tracked file changed, so nothing to commit. Slides and writeup are step 4.
Verify: Verify passed: ./run tools/build_report.py analysis/02_pa --check
Independent review: no gaps

Rejected by user: 2026-11-21 rerun comparison with QPA9501 and AWL9924 data

### 2026-11-21
Unblocked: was blocked: rerun comparison with QPA9501 and AWL9924 data
