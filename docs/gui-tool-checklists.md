# GUI-tool checklists (fnd-05 step 8)

Tools with no unattended Linux route. The agent could not download or install any of the three
(see the trial results below), so each is a user-run checklist. Record the outputs under
`analysis/<NN_name>/user_runs/` (screenshots plus a short `.md` of the numbers), so a later
analysis can cite them. Do not commit an installer.

## Trial results (2026-11-20, host Ubuntu 24.04, image `fmcw3-sim` has wine 9.0, wine32, xvfb)

| Tool | Download | Wine install | Batch or CLI mode |
|---|---|---|---|
| ADIsimPLL | not obtained: `www.analog.com` timed out from this host (curl exit 28, HTTP/1.1, 25 s and 40 s, every page tried); `download.analog.com` answers but has no ADIsimPLL path (404 on `/tools/...`, `/sw/`) | not attempted, no installer | none known; unverified, not found in any source read here |
| ADIsimRF | same as ADIsimPLL | not attempted, no installer | none known; unverified |
| Saturn PCB Toolkit | page `https://saturnpcb.com/saturn-pcb-toolkit/` reads "freeware ... download our PCB Toolkit today for free", but the Download button opens a popup with an email form (Ninja Forms), so there is no direct file URL | not attempted, no installer | none known; unverified (it is a Windows GUI calculator, "does not use JAVA") |
| JLCPCB impedance calculator | `https://jlcpcb.com/pcb-impedance-calculator` returns HTTP 200, title "Controlled Impedance Calculator - JLCPCB"; browser tool, needs JavaScript | not applicable (web) | none; browser only |

The analog.com URLs are the product pages the user can open in a browser; they were not verified
from here, so find the installer link on the page. Once the user has an installer, the Wine
trial is: `xvfb-run -a wine msiexec /i Z:\path\setup.msi /qn` (MSI) or `wine setup.exe /S`
(NSIS-style silent switch, may differ), in a scratch `WINEPREFIX`, then check the install
directory and run the exe with `/?`.

## ADIsimPLL (ADF4158 chirp PLL; review plan Phase 6 item 4 and Phase 7)

Obtain: ADI site, ADIsimPLL page (user-fetch, registration may be needed).

Inputs to enter:
- [ ] Part ADF4158; reference frequency and PFD frequency from the firmware config
- [ ] Output band 5.8 GHz chirp, start and stop frequency and ramp time from the firmware
- [ ] VCO: the part and its Kv (from the datasheet, U-refdes in the schematic)
- [ ] Charge-pump current and the actual loop filter values (R, C) from `kicad/` (VTUNE branch, U7 drive)
- [ ] Loop bandwidth and phase margin as designed

Outputs to record:
- [ ] Loop bandwidth, phase margin, lock time (numbers)
- [ ] Phase noise plot at the VCO output (screenshot) and integrated jitter
- [ ] Reference spur and fractional spur levels (dBc) and their offsets
- [ ] The saved project file (small, if licence allows) and the tool version

## ADIsimRF (RF cascade; review plan Phase 2)

Obtain: ADI site, ADIsimRF page (user-fetch).

Inputs to enter:
- [ ] Stage list in order from the traced chain (HMC431, ADL5802, SKY65404, TRF37A73, TQP5525, baluns, pads), each with gain, NF, P1dB, OIP3 from the datasheet
- [ ] Source level and bandwidth, losses of lines and connectors

Outputs to record:
- [ ] Cascaded gain, noise figure, P1dB, OIP3 and the stage that limits each
- [ ] Per-stage level table (screenshot or export); compare with the scikit-rf cascade in `tests/test_sim_smoke.py` style script

## Saturn PCB Toolkit (impedance cross-check; review plan Phase 3)

Obtain: `https://saturnpcb.com/saturn-pcb-toolkit/`, Download button, email form (free).

Inputs to enter:
- [ ] Microstrip and coplanar-with-ground calculators: er and prepreg height from the fab stackup (0.11 mm prepreg on L1 to L2), copper weight, trace width and gap of the 50 ohm lines, frequency 5.8 GHz
- [ ] The known cases from the plan: 0.23 mm microstrip with er 4.5 (script gives 43.0 ohm), CPWG 0.2 mm gap (47.5 ohm)

Outputs to record:
- [ ] Z0 and effective er for each case; difference to the repo script and to KiCad's calculator
- [ ] Tool version

## JLCPCB impedance calculator (the fab's own reference; browser, user-run)

URL: `https://jlcpcb.com/pcb-impedance-calculator` (page text: computes track width and
recommended stack-ups from layer count, thickness, copper weight, target impedance, spacing and
coplanar gap).

Inputs to enter:
- [ ] Layers 6, thickness 1.6 mm, copper weight, target 50 ohm single-ended, the reference layer (L2 or L5)
- [ ] Trace type: microstrip or coplanar with ground, spacing for CPWG

Outputs to record:
- [ ] The stackup JLCPCB proposes (layer names, prepreg and core thickness, er) and the track width it returns
- [ ] Screenshot and date; compare with the repo script (this is the fab's reference for its own stackups, so it decides the final widths)
