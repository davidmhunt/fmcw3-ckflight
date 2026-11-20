# Analysis tools on Linux (fnd-05)

Which tools, runnable on Linux, replace LTspice, TI WEBENCH, ADIsimPLL and an EM solver for the
review-plan Phases 2, 3, 6 and 7. Smoke tests ran on 2026-11-20 in the `fmcw3-sim` image
(`docker/Dockerfile.sim`, Ubuntu 24.04). The image has:
- ngspice 42;
- scikit-rf 2.2.0;
- openEMS v0.37.0-83, built from source with its Python bindings;
- Wine 9.0 with wine32, and xvfb;
- LTspice 26.1.1 under Wine, driven through spicelib 1.6.4 (installed at image build; the
  installer is downloaded there and never committed).

GUI route: `./run --sim-gui <cmd>` runs a command in this image with a window on your X11
desktop, and `./run --sim-gui ltspice [file]` starts LTspice under Wine, opening an `.asc` or
`.net` file from the repo (X access for your own user only, revoked on exit; `--print` shows the
docker command; example `./run --sim-gui ltspice tests/sim/rc_lowpass_ltspice.net`, LTspice syntax;
`SIM_GUI_DPI`, default 144, scales the text). See `docs/setup.md`. LTspice's interactive plot is therefore available to you;
batch runs still go through spicelib.

The first build takes about 25 minutes (the image is about 7 GB). The candidate survey and raw
outputs are in `runs/fnd-05/notes.md`, which is untracked.

The passing cases are kept as `tests/test_sim_smoke.py`, with fixtures in `tests/sim/`. Run through
`./run --sim python3 -m pytest tests/test_sim_smoke.py -q` (the command runs in the `fmcw3-sim`
image with the repo mounted), they give **10 passed**, with no skips. The same command on the host
gives the same result. Plain `./run` runs inside `fmcw3-tools`, which has no Docker, so the sim
tests skip there. The TI-model tests need the two TI zips from `datasheets/manifest.yaml`
(`./run tools/fetch_sources.py` downloads them) and skip with "not supplied" without them.

"Smoke" values:
- **pass:** ran and matched a hand result; the test is named.
- **fail:** tried; the error is quoted.
- **partial:** some steps worked; it says which.
- **not attempted:** says why.

## SPICE engine (Phase 6, items 1 to 3)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| ngspice 42 | LTspice | native (apt) or `fmcw3-sim`; batch `ngspice -b`, headless | BSD-3 (modified BSD) | **pass**: RC low-pass AC sweep, -3.01 dB at 1 kHz and -20.04 dB at 10 kHz, within 0.02 dB of 10log10(1+(f/fc)^2) (`test_ngspice_rc_lowpass_matches_formula`). **pass**: loads a `.lib` subcircuit and runs it, closed-loop gain 10 (`test_ngspice_loads_subckt_model_and_runs`) | LTspice-library models do not load (see vendor models) |
| KiCad built-in simulator | LTspice GUI | KiCad GUI; it is an ngspice front end | GPLv3 | not attempted: GUI-only for running a simulation | Useful for exporting SPICE netlists from the schematic; ngspice runs them |
| Qucs-S | LTspice GUI | not in Ubuntu 24.04 apt; flatpak, AppImage or source | GPL | not attempted: GUI front end; ngspice covers the need | Fallback only |
| LTspice 26.1.1 under Wine, driven by spicelib 1.6.4 | LTspice on Windows | `fmcw3-sim`: `LTspice64.msi` downloaded and installed at image build (`wine msiexec /i ... /qn`, needs wine32); batch `-b` through spicelib `SimRunner` under `xvfb-run` | ADI freeware, not open; spicelib is GPLv3 | **pass**: RC low-pass, 41 points from 10 Hz to 100 kHz, worst error 7e-15 dB against 10log10(1+(f/fc)^2) (`test_ltspice_spicelib_rc_lowpass_matches_formula`). An earlier trial recorded batch mode as failed: that was LTspice's first-run dialog "Anonymously Share LTspice Usage Data", which blocks `-b`; the image writes `CaptureAnalytics=false` into `LTspice.ini`, which fixes it | Installer not committed (licence, 145 MB). Pass `SimRunner.run_now` a netlist path, not a `SpiceEditor` (the editor fails on TI `VALUE { + IF(...) }` continuation lines). Wine needs a prefix owned by the caller, so the tests symlink the baked prefix |

## Vendor models (Phase 6, items 1 to 3)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| ADI LT6232 model in LTspice | LTspice model library | LTspice (Wine, `fmcw3-sim`) | ADI terms | **pass**: LT6232 has no subcircuit of its own; its symbol (`lib/sym/OpAmps/LT6232.asy`) uses the LT6231 subcircuit in the bundled `LTC2.lib`. Non-inverting gain of 10 on +/-2.5 V: 20.000 dB at 1 kHz, DC out 2.045 V for 0.2 V in (`test_ltspice_adi_model_runs`) | The model reproduces the real input range limit: on a single 5 V supply a 1 V follower gives 1.27 V. This is the model, not Wine |
| ADI LTC*.lib models in ngspice 42 | LTspice model library | ngspice | ADI terms | **fail** (expected, kept as a test): `MIF-ERROR - unable to find definition of model` on the LTspice-only OTA A-device (`test_adi_ltc_model_does_not_load_in_ngspice`); an earlier LT1007 trial also gave `no such function 'uplim'`, also with `set ngbehavior=ltpsa` | ADI models need LTspice. The analog.com download URL timed out from this host, so the bundled library is the source |
| TI LP5907 1.8 V PSpice model (unencrypted, `ti-lp5907-1p8-pspice`) in LTspice and in ngspice (`.options ngbehavior=psa`) | PSpice | both engines | TI model terms; not redistributed | **pass**: 3.6 V ramp in 100 us, 180 ohm load, 1 uF in and out: Vout at 2 ms is 1.8001 V in both; the engines differ by at most 0.0010 V at six times from 50 us to 2 ms (`test_ti_pspice_model_runs_in_ltspice_and_ngspice_and_agrees`) | Fixed-voltage models only (1.2 to 4.5 V). Downloads without login (`ti.com/lit/zip/snvmap9`) |
| TI LDO feeding an ADI op-amp in one netlist (LP5907 into LT6231 follower, +/-3.3 V rails) in LTspice | none | LTspice | as above | **pass**: LDO out 1.8001 V, buffer out 1.8001 V (`test_mixed_ti_ldo_adi_opamp_runs_in_ltspice`). On +/-2.5 V rails the follower gives 1.70 V (LT6231 input range clamp) | LTspice is the only engine that ran both model families |
| TI LMR51420XF PSpice model (`ti-lmr51420xf-pspice`) in LTspice and ngspice | PSpice, WEBENCH simulation | both engines | TI model terms | **fail** in both, kept as a test (`test_encrypted_ti_model_fails_in_both_engines`): the `.LIB` is TI-encrypted (Cadence `$CDNENCSTART_ADV2`). LTspice: `LMR51420XF.lib(942): Expected device instantiation or directive here.`; ngspice: `missing tokens` | Needs a hand-built averaged buck model in either engine. The LP5907 page also lists encrypted variants; choose "Unencrypted". LD3920 was not found: ti.com/product/LD39200 returned 404, so the part name in the plan may differ |
| Ferrite-bead vendor models (Murata, TDK, Wurth) | vendor simulators | ngspice subcircuit netlists | vendor terms | not attempted: no download tried. Murata SimSurfing is believed to be a free download; not confirmed | Fallback: RLC fit to the datasheet impedance curve |

## Buck design (Phase 6, item 2)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| TI WEBENCH | itself | web browser, TI account | TI web service | not attempted: no unattended route | The user runs it by hand from a checklist |
| Hand calculation of the buck power stage (Python), equations from TI SLVA477C (`ti-slva477c`) | WEBENCH sizing | any Python | repo (GPLv3) | not attempted here: plain arithmetic written in sim-02, tested there against the SLVA477C equations and the datasheet's worked example | Ripple, peak current against inductor saturation, output ripple. The TI model is encrypted (above), so loop stability comes from the datasheet's recommended L and C ranges or a hand-built averaged model |

## PLL (Phase 6, item 4, and Phase 7)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| ADIsimPLL | itself | Windows GUI; Wine at best | ADI freeware | **not obtained** (step 8): `www.analog.com` timed out from this host (curl exit 28, every page tried) and `download.analog.com` has no ADIsimPLL path, so there was no installer to try under Wine. No batch or command-line mode was found in any source read | The user's vendor-validated cross-check for ADF4158 specifics: checklist in `docs/gui-tool-checklists.md` |
| Python loop model (scipy.signal, numpy), equations from TI SWRA029 (`ti-swra029`) | ADIsimPLL | `fmcw3-tools` or `fmcw3-sim` | repo (GPLv3) | not attempted here: written and tested in sim-03 against the SWRA029 third-order loop (open-loop gain, phase margin) | Needed only for sweeps ADIsimPLL cannot batch; must be validated against ADIsimPLL output the user records (sim-03, `[heavy]` step) |

## RF cascade tools (Phase 2)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| ADIsimRF | itself | Windows GUI; Wine at best | ADI freeware | **not obtained** (step 8), same reason as ADIsimPLL. No batch mode found | The user's vendor cross-check of the cascade (gain, NF, P1dB, OIP3): checklist in `docs/gui-tool-checklists.md` |

## RF cascade and S-parameters (Phase 2)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| scikit-rf 2.2.0 | spreadsheet cascades, vendor RF tools | Python; `fmcw3-sim` | BSD-3 | **pass**: -3 dB attenuator cascaded with a +20 dB amplifier gives S21 = +17.000 dB; lossy line 0.1 Np/m x 0.2 m = -0.1737 dB (`test_scikit_rf_two_stage_cascade`). The same test computes the Friis NF by hand without scikit-rf, so that part checks nothing about the tool | Needs vendor `.s2p` files (par-02) for real stages; reading a `.s2p` file is not smoke-tested |

## Transmission lines (Phase 3)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| KiCad Calculator Tools | itself | KiCad GUI, native | GPLv3 | not attempted: GUI-only, no `kicad-cli` command | The user's independent hand check for three cases (rf-02 step 2) |
| Saturn PCB Toolkit | itself | Windows GUI; Wine at best | freeware | **not obtained** (step 8): the Download button opens an email form, so there is no direct file URL; nothing was installed | Independent third calculator for the plan's two known cases: checklist in `docs/gui-tool-checklists.md` |
| JLCPCB controlled impedance calculator | itself | browser, JavaScript (`jlcpcb.com/pcb-impedance-calculator`, HTTP 200 from this host) | fab web service | not attempted: browser only, user-run | The fab's own reference for its stackups, so it decides final widths |
| Python script: microstrip and grounded CPW (scipy elliptic integrals), checked against the KiCad calculator source (`kicad-10.0.5-microstrip`, `kicad-10.0.5-coplanar`) and `wikipedia-microstrip` | calculators | any Python | repo (GPLv3) | not attempted here: written and tested in rf-02 against those sources and the plan's numbers (microstrip 0.23 mm, er 4.5 = 43.0 ohm; CPWG 0.2 mm gap = 47.5 ohm) | Quasi-static only. Hammerstad and Jensen 1980 is paywalled (user-fetch), so that the KiCad constants are its f(u) is unconfirmed |
| scikit-rf `media.MLine`, `media.CPW` | calculators | Python | BSD-3 | covered by the scikit-rf install above | Quasi-static cross-check for the script |
| openEMS v0.37 (FDTD) | CST, HFSS | `fmcw3-sim`, built from source with Python bindings | GPLv3 | **pass**: microstrip h 1.0 mm, er 4.3, w 1.95 mm gives Z0 = 48.8 ohm from the port (Hammerstad-Jensen about 49 to 50), S11 max -33 dB, S21 -0.02 dB, 370k cells, about 21 s (`test_openems_microstrip_about_50_ohm`) | Geometry is set up by hand. Pitfalls: the port must run strip to ground (start z = h, stop z = 0); read Z from CalcPort without `ref_impedance`; h5py must be pip-installed next to pip numpy |
| CST Studio Suite, Ansys HFSS (commercial full-wave solvers) | openEMS | Windows (CST also Linux), licensed; not available here | commercial | **not attempted**: no licence, no installer. What follows is general knowledge, not tested here | Over openEMS they would add: a vendor-validated and supported solver; a GUI with CAD and PCB (ODB++, Gerber) import, so the SMA launch and LO via would not be modelled by hand; automatic meshing and adaptive refinement (HFSS); and wider material and port libraries. They add nothing the openEMS microstrip pass (48.8 ohm) shows is missing for two small structures, and cost a licence. The user has CST Studio Suite Learning Edition on a Windows machine (decision 2026-11-20): it is used for 3D structures where its model-size limits allow, run by the user from a checklist, with the `.s2p` files committed (or kept outside the repo and listed in the sources manifest if too large). openEMS is the open, repeatable fallback and cross-check |

## Verdict

Rule: prefer a validated tool (an industry or vendor simulator, or a vendor or fab calculator) and
write the repo's own code only for sweeps those tools cannot do. Each choice names the reference
in `## References` that backs it. One primary tool per later analysis:

- **Any circuit with an ADI model, or ADI and TI parts together: LTspice (through spicelib, in
  `fmcw3-sim`).** It is the one engine that ran both ADI LTC models (LT6231, which is what the
  LT6232 symbol uses) and a TI PSpice model, including a TI LDO feeding an ADI op-amp in one
  netlist. ngspice cannot load the ADI models (`MIF-ERROR`).
- **Any circuit with TI parts only: ngspice.** An unencrypted TI PSpice model matched LTspice to
  0.0010 V in ngspice with `ngbehavior=psa`, and ngspice is open and fast. Encrypted TI models
  (LMR51420XF) load in neither engine.
- **sim-01 (supply noise to the VCO): LTspice** for the LDO to VCO path when an ADI part is in the
  loop, ngspice when it is TI-only. LP5907 uses the unencrypted TI model; the LD3920 and the
  ferrite bead use a datasheet PSRR or RLC fit until their files are supplied.
- **sim-02 (buck and IF filter): the Python power-stage calculation for the buck, backed by
  `ti-slva477c`; LTspice for the IF amplifier filter** (ADI op-amp). The TI buck model is
  encrypted, so a stability check needs a hand-built averaged model. WEBENCH stays an optional
  browser cross-check for you.
- **sim-03 (PLL): ADIsimPLL is the validated tool, run by you from the checklist in
  `docs/gui-tool-checklists.md`; the repo's Python loop model (scipy), backed by `ti-swra029`,
  does the sweeps ADIsimPLL cannot batch.** The Python model is trusted only after it matches the
  ADIsimPLL numbers you record. This is the one analysis whose primary tool has no unattended
  route.
- **rf-01 (RF level plan): scikit-rf**, with ADIsimRF as your vendor cross-check. It passed the
  cascade check and runs unattended. The Friis formulas are in `wikipedia-friis-noise` (secondary
  source; a primary text is still preferable) and the range equation in `mitll-radar-equation`.
  Reading vendor `.s2p` files was not smoke-tested here; rf-01's first real stage file tests it.
- **rf-02 (impedance): the JLCPCB calculator is the reference for the fab's stackups and decides
  final widths; the KiCad calculator and Saturn are your hand checks; the repo's Python microstrip
  and CPWG script does the width, gap and er sweeps.** It is checked against the KiCad source
  (`kicad-10.0.5-microstrip`, `kicad-10.0.5-coplanar`) and `wikipedia-microstrip`.
  **openEMS** (passed, 48.8 ohm) is used only for the SMA launch and the LO via; CST and HFSS add
  nothing needed for those two structures.
- **sim-04 (frequency plan): plain Python**, backed by `minicircuits-an00-009` and
  `minicircuits-an00-011` for the mixing products and IM3. No external tool is needed.

LTspice is chosen where ADI models are involved. The earlier "batch mode fails" result was a
first-run dialog, fixed at image build. GUI-only tools (ADIsimPLL, ADIsimRF, Saturn) could not be
downloaded from this host, so none has an install result; they are user checklists.

## Tools the user must obtain

| What | Link | Needed for | Without it |
|---|---|---|---|
| ADIsimPLL (Windows GUI, ADI site; could not be downloaded from this host) | analog.com ADIsimPLL page | sim-03: the validated PLL tool; its numbers validate the Python loop model | Python model unvalidated against a vendor tool |
| ADIsimRF (Windows GUI, ADI site; same) | analog.com ADIsimRF page | rf-01 vendor cross-check of the cascade | scikit-rf only |
| Saturn PCB Toolkit (free; email form, no direct URL) | https://saturnpcb.com/saturn-pcb-toolkit/ | rf-02 third impedance check | KiCad calculator and JLCPCB only |
| JLCPCB impedance calculator (browser, user-run) | https://jlcpcb.com/pcb-impedance-calculator | rf-02: the fab's stackups and final widths | none; this one decides |
| ADI LT6232 | none: LTspice's bundled `LTC2.lib` LT6231 subcircuit is used (the LT6232 symbol points at it) | sim-01, sim-02 | not needed for the bundled model; a separate LT6232 file is optional |
| TI LMR51420 averaged or unencrypted model | ti.com LMR51420 product page, "Design and development"; the model fetched (`slum825`) is encrypted and loads nowhere | sim-02 buck stability | Hand-built averaged model, datasheet L and C ranges |
| TI LD3920 model | ti.com; part not found (the plan may mean LD39200, which gave 404) | sim-01 PSRR | Behavioural PSRR from the datasheet curve. Confirm the part number |
| Ferrite-bead netlists for the fitted beads | Murata SimSurfing, TDK SEAT or Wurth REDEXPERT | sim-01 | RLC fit to the datasheet curve |
| TI WEBENCH session (TI account) | webench.ti.com | sim-02 optional cross-check | Hand calculation |
| Hammerstad and Jensen 1980 (IEEE Xplore, paywalled); Simons, Coplanar Waveguide Circuits (book); Wadell, Transmission Line Design Handbook (book) | see `## References` | rf-02: primary sources for the microstrip and CPWG equations | secondary sources and the KiCad source only |
| Banerjee, PLL Performance, Simulation and Design (free; no working URL found) | former National Semiconductor, now TI | sim-03 | TI SWRA029 |
| CST Studio Suite Learning Edition (you have it, on your Windows machine) | Dassault Systèmes, student licence | rf-02: the SMA launch and LO via where the model fits the Learning Edition limits | openEMS |

Downloaded models and PDFs go under the gitignored `datasheets/files/` and
`docs/references/files/`, fetched by `./run tools/fetch_sources.py`; tool installers (LTspice,
PSpice for TI) go under the gitignored `software/files/` and are listed in
`software/manifest.yaml` (see `software/README.md`). Nothing is committed whose licence forbids
it.

## Proposed amendments to sim-spurs and rf-review

These are proposals; the directives themselves are not edited here.

1. **All sim-spurs directives and rf-02's openEMS step: put real simulation checks in Verify
   through `./run --sim`** (it exists now: it runs a command in `fmcw3-sim` with the repo mounted).
   Plain `./run` still skips the sim tests.
2. **sim-01:** run ADI-involved and mixed circuits in LTspice through spicelib and TI-only
   circuits in ngspice. Use the unencrypted LP5907 model (`ti-lp5907-1p8-pspice`); for the LD3920
   and ferrite beads use a datasheet PSRR or RLC fit unless the file is supplied. Confirm the
   LD3920 part number.
3. **sim-02:** the buck needs a hand-built averaged model, because TI's LMR51420XF model is
   encrypted and loads in neither engine. Power-stage sizing follows `ti-slva477c`. Drop "run the
   TI model" from the directive. Keep WEBENCH as an optional step for you.
4. **sim-03:** ADIsimPLL becomes the validated tool, user-run from `docs/gui-tool-checklists.md`
   (the agent could not obtain it). The Python loop model is built from `ti-swra029` and compared
   with the numbers you record; do not trust it before that comparison.
5. **rf-01:** scikit-rf is confirmed; ADIsimRF is the optional vendor cross-check (checklist).
   Stage S-parameters come from par-02's datasheet manifest.
6. **rf-02:** add the JLCPCB calculator as the fab reference and Saturn as a third check (both
   user-run). The script is checked against the KiCad source, not just the plan's two numbers.
   Step 4 may use openEMS (`fmcw3-sim`) for the SMA launch and the LO layer-change via only; record
   the port-orientation pitfall above. Fetch Hammerstad and Jensen 1980 before claiming the KiCad
   constants are its equations.
7. **sim-04:** cite `minicircuits-an00-009` and `minicircuits-an00-011` for the spur and IM3
   formulas.

## References

Each entry is a manifest id (in `docs/references/manifest.yaml` unless marked), its public link,
and the pages verified against the downloaded file. The files are gitignored; `./run
tools/fetch_sources.py` downloads them and `--check` confirms the hashes. Details of each
verified item (equation, quote) are in the manifest.

| Id | Link | Verified | Backs |
|---|---|---|---|
| `ti-slva477c` | https://www.ti.com/lit/an/slva477/slva477.pdf | pages 2 and 3: equations 1, 2, 4, 5 and 6 (duty cycle, ripple current, peak switch current, inductor from 20 to 40 percent ripple) | buck power stage (sim-02) |
| `ti-swra029` | https://www.ti.com/lit/an/swra029/swra029.pdf | pages 15, 22, 24, 43: phase noise sum, equations 17, 20 and 21, phase margin, 20log(N) | PLL loop filter and phase noise (sim-03) |
| `mitll-radar-equation` | https://www.ll.mit.edu/sites/default/files/outreach/doc/2018-07/lecture%202.pdf | page 10: N = k Ts Bn and S/N | radar range equation (rf-01) |
| `wikipedia-friis-noise` | https://en.wikipedia.org/w/index.php?title=Friis_formulas_for_noise&oldid=1264867328&action=raw | sections on noise factor and noise temperature (secondary source, fixed revision) | Friis cascade (rf-01) |
| `minicircuits-an00-009` | https://www.minicircuits.com/app/AN00-009.pdf | pages 3, 5, 6: third-order IM frequencies, IP3, rule-of-thumb IM level | mixing products and spurs (sim-04) |
| `minicircuits-an00-011` | https://www.minicircuits.com/app/AN00-011.pdf | page 1: (m x LO) +/- (n x RF) harmonics table | mixer spurs (sim-04) |
| `wikipedia-microstrip` | https://en.wikipedia.org/w/index.php?title=Microstrip&oldid=1356129625&action=raw | section Characteristic impedance (secondary source, fixed revision) | microstrip Z0 (rf-02) |
| `kicad-10.0.5-microstrip` | https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0.5/common/transline_calculations/microstrip.cpp | functions Z0_homogeneous and SynthesizeWidth | the KiCad calculator you compare against (rf-02) |
| `kicad-10.0.5-coplanar` | https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0.5/pcb_calculator/transline/coplanar.cpp | function calcAnalyze, including the backMetal (CPWG) branch | CPWG Z0 (rf-02) |

## Vendor models (not references)

These are in `datasheets/manifest.yaml` with a hash and licence but carry no `verified` items, so
they are not in `## References`. They are tools' inputs, not sources for an equation or number.

- `ti-lp5907-1p8-pspice` (https://www.ti.com/lit/zip/snvmap9): run in LTspice and ngspice by
  `tests/test_sim_smoke.py`. Used for the LP5907 model.
- `ti-lmr51420xf-pspice` (https://www.ti.com/lit/zip/slum825): found encrypted by
  `tests/test_sim_smoke.py`. Not usable as is.

Not yet in the manifest (paywalled or no working link; see the comment block in
`docs/references/manifest.yaml`): Hammerstad and Jensen 1980 (doi 10.1109/MWSYM.1980.1124303),
Simons 2001 (ISBN 9780471161219), Wadell 1991, Banerjee "PLL Performance, Simulation and Design".
The Friis and microstrip entries are Wikipedia revisions and the KiCad entries are implementation
code; neither replaces a primary source for the equations.
