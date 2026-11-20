# Analysis tools on Linux (fnd-05)

Which tools, runnable on Linux, replace LTspice, TI WEBENCH, ADIsimPLL and an EM solver for the
review-plan Phases 2, 3, 6 and 7. Smoke tests ran on 2026-11-20 in the `fmcw3-sim` image
(`docker/Dockerfile.sim`, Ubuntu 24.04). The image has:
- ngspice 42;
- scikit-rf 2.2.0;
- openEMS v0.37.0-83, built from source with its Python bindings;
- Wine 9.0 with wine32, and xvfb.

The first build takes about 25 minutes. The candidate survey and raw outputs are in
`runs/fnd-05/notes.md`, which is untracked.

The passing cases are kept as `tests/test_sim_smoke.py`, with fixtures in `tests/sim/`. Run on the
host with `python3 -m pytest tests/test_sim_smoke.py -q`, they give **4 passed** (about 22 s). Run
through `./run` (inside `fmcw3-tools`, which has no Docker), all four **skip** with the reason "sim
image absent". So the directive's Verify line proves only the skip path; the real run needs the host.
See amendment 1 at the end.

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
| LTspice under Wine | LTspice | Wine 9.0 with wine32, under xvfb | ADI freeware, not open | **partial**: `LTspice64.msi` downloads without registration (145 MB) and installs headless with `wine msiexec /i ... /qn` (needs wine32). Batch `LTspice.exe -b rc.net` started but wrote no `.log` or `.raw` within 200 s: **fail** for unattended batch | GUI use by the user only; not kept in tests (licence, 145 MB) |

## Vendor models (Phase 6, items 1 to 3)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| ADI LT6232 model in ngspice | LTspice model library | ngspice | ADI terms | **fail**: LT6232 is not in LTspice's bundled `lib/sub`, and the analog.com model URL timed out (curl exit 28; exit 92 HTTP/2 stream error). Substitute LT1007 from bundled `LTC.lib` in ngspice: `MIF-ERROR - unable to find definition of model` and `no such function 'uplim'`, also with `set ngbehavior=ltpsa` | ADI LTC.lib models use LTspice-only devices and functions. Fallback: a datasheet macro-model (GBW, output resistance, slew) in ngspice |
| TI PSpice models (LMR51420, LP5907, LD3920) in ngspice PSpice mode (`set ngbehavior=psa`) | PSpice, WEBENCH simulation | ngspice | TI terms | not attempted: the ti.com zip download is behind a web form (`ti.com/lit/zip/snvmb09` returned 302) | The user must fetch the zips; encrypted models would not load. Fallback: behavioural LDO (PSRR curve from the datasheet) and an averaged buck model |
| Ferrite-bead vendor models (Murata, TDK, Wurth) | vendor simulators | ngspice subcircuit netlists | vendor terms | not attempted: no download tried. Murata SimSurfing is believed to be a free download; not confirmed | Fallback: RLC fit to the datasheet impedance curve |

## Buck design (Phase 6, item 2)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| TI WEBENCH | itself | web browser, TI account | TI web service | not attempted: no unattended route | The user runs it by hand from a checklist |
| Hand calculation from the LMR51420 datasheet (Python) | WEBENCH sizing | any Python | repo (GPLv3) | not attempted here: plain arithmetic written in sim-02, tested there against the datasheet's worked example | Ripple, peak current against inductor saturation, output ripple; loop stability only from the datasheet's recommended L and C ranges unless the TI model loads |

## PLL (Phase 6, item 4, and Phase 7)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| ADIsimPLL | itself | Windows GUI; Wine at best | ADI freeware | not attempted. Believed, not confirmed: a Windows GUI installer behind ADI registration, with no batch mode | Cross-check for the user only |
| Python loop model (scipy.signal, numpy) | ADIsimPLL | `fmcw3-tools` or `fmcw3-sim` | repo (GPLv3) | not attempted here: written and tested in sim-03 against a textbook third-order loop | Must be derived and validated in sim-03 (`[heavy]` step) |

## RF cascade and S-parameters (Phase 2)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| scikit-rf 2.2.0 | spreadsheet cascades, vendor RF tools | Python; `fmcw3-sim` | BSD-3 | **pass**: -3 dB attenuator cascaded with a +20 dB amplifier gives S21 = +17.000 dB; lossy line 0.1 Np/m x 0.2 m = -0.1737 dB (`test_scikit_rf_two_stage_cascade`). The same test computes the Friis NF by hand without scikit-rf, so that part checks nothing about the tool | Needs vendor `.s2p` files (par-02) for real stages; reading a `.s2p` file is not smoke-tested |

## Transmission lines (Phase 3)

| Tool | Replaces | How it runs | Licence | Smoke | Limits |
|---|---|---|---|---|---|
| KiCad Calculator Tools | itself | KiCad GUI, native | GPLv3 | not attempted: GUI-only, no `kicad-cli` command | The user's independent hand check for three cases (rf-02 step 2) |
| Python script: Hammerstad-Jensen microstrip and grounded CPW (scipy elliptic integrals) | calculators | any Python | repo (GPLv3) | not attempted here: written and tested in rf-02 against published values and the plan's numbers (microstrip 0.23 mm, er 4.5 = 43.0 ohm; CPWG 0.2 mm gap = 47.5 ohm) | Quasi-static only |
| scikit-rf `media.MLine`, `media.CPW` | calculators | Python | BSD-3 | covered by the scikit-rf install above | Quasi-static cross-check for the script |
| openEMS v0.37 (FDTD) | CST, HFSS | `fmcw3-sim`, built from source with Python bindings | GPLv3 | **pass**: microstrip h 1.0 mm, er 4.3, w 1.95 mm gives Z0 = 48.8 ohm from the port (Hammerstad-Jensen about 49 to 50), S11 max -33 dB, S21 -0.02 dB, 370k cells, about 21 s (`test_openems_microstrip_about_50_ohm`) | Geometry is set up by hand. Pitfalls: the port must run strip to ground (start z = h, stop z = 0); read Z from CalcPort without `ref_impedance`; h5py must be pip-installed next to pip numpy |

## Verdict

One primary tool per later analysis:

- **rf-01 (RF level plan): scikit-rf.** It passed the cascade check and runs unattended. Reading
  vendor `.s2p` files is a documented library feature but was not smoke-tested here; rf-01's first
  real stage file tests it.
- **rf-02 (impedance): the repo's Python Hammerstad-Jensen and CPWG script.** Phase 3 asks for a
  committed script. scikit-rf media is the cross-check and the KiCad calculator is your hand check.
  **openEMS** (passed, 48.8 ohm) is used only for the SMA launch and the LO via.
- **sim-01 (supply noise to the VCO): ngspice.** It passed both smoke tests and runs headless. The
  regulators use behavioural PSRR models from the datasheets until the vendor models are fetched.
- **sim-02 (buck and IF filter): Python hand calculation for the buck and ngspice for the IF
  filter.** WEBENCH has no unattended route and the TI model is behind a download form.
- **sim-03 (PLL): a Python loop model (scipy).** ADIsimPLL is believed to be a Windows-only GUI
  with no batch mode (not confirmed), so it has no unattended route either way.
- **sim-04 (frequency plan): plain Python.** No external tool is needed.

LTspice is not chosen: under Wine it installs, but batch mode wrote no output.

## Tools the user must obtain

| What | Link | Needed for | Without it |
|---|---|---|---|
| ADI LT6232 SPICE model | analog.com LT6232 product page, "Tools and simulations" | sim-02 IF amplifier, sim-01 | Datasheet macro-model in ngspice |
| TI LMR51420 PSpice model zip | ti.com LMR51420 product page, "Design and development" (`snvmb09`) | sim-02 buck stability cross-check | Datasheet L and C ranges only |
| TI LP5907 and LD3920 models | ti.com product pages | sim-01 PSRR | Behavioural PSRR from the datasheet curve |
| Ferrite-bead netlists for the fitted beads | Murata SimSurfing, TDK SEAT or Wurth REDEXPERT | sim-01 | RLC fit to the datasheet curve |
| TI WEBENCH session (TI account) | webench.ti.com | sim-02 optional cross-check | Hand calculation |
| ADIsimPLL (ADI registration, Windows) | analog.com ADIsimPLL page | sim-03 optional cross-check | Python model only |

Model files go under `datasheets/models/` (not committed if their licence forbids it); each
directive that uses one checks its licence first.

## Proposed amendments to sim-spurs and rf-review

These are proposals; the directives themselves are not edited here.

1. **All sim-spurs directives and rf-02's openEMS step: run the simulations on the host.** Today
   `./run uv run pytest tests/test_sim_smoke.py` skips every test, because `fmcw3-tools` has no
   Docker inside it. Add a `./run --sim` mode that runs a command in `fmcw3-sim`, and put real
   simulation checks into Verify through it.
2. **sim-01:** replace "vendor models" with "the vendor model if the user has supplied it, else a
   behavioural PSRR model from the datasheet curve". Name the files expected under
   `datasheets/models/`.
3. **sim-02:** primary is the hand calculation plus ngspice. The TI model cross-check runs only if
   the zip is supplied. Keep the WEBENCH checklist as an optional step for you.
4. **sim-03:** step 3 (ADIsimPLL) becomes optional and user-run. The Python model is the only
   automated route.
5. **rf-02:** step 4 may use openEMS, since it passed (`fmcw3-sim`). Model only the SMA launch and
   the LO layer-change via, and record the port-orientation pitfall above.
6. **rf-01:** scikit-rf is confirmed. Stage S-parameters come from par-02's datasheet manifest.
