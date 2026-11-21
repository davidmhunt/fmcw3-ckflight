# fnd-05: Choose and smoke-test Linux tools for the simulation and RF analyses
Status: done
Goal: foundation
Node: any
Deliverable: doc
Accept: user
Verify: ./run --sim python3 -m pytest tests/test_sim_smoke.py -q && ./run uv run pytest tests -q && ./run tools/fetch_sources.py --check
Hardware: none

## Goal
A tested answer to "which tools, runnable on Linux, replace LTspice, TI WEBENCH, ADIsimPLL and
an EM solver for this review". It holds when `docs/analysis-tools.md` gives a verdict per
analysis backed by a smoke test that was actually run, and lists anything the user must obtain.

## Steps
1. For each need in review-plan Phases 2, 3, 6 and 7, list candidates and how each would run
   (native package, Docker image, Wine, web browser):
   SPICE (ngspice, KiCad's built-in simulator, Qucs-S, LTspice under Wine);
   vendor models (ADI LT6232 and LD3920/LP5907 models in ngspice, TI LMR51420 PSpice model in
   ngspice's PSpice-compatibility mode, ferrite-bead vendor models);
   buck design (TI WEBENCH in a browser, hand calculation from the datasheet equations);
   PLL (ADIsimPLL under Wine, open Python PLL loop-filter and phase-noise models);
   RF cascade and S-parameters (scikit-rf); transmission lines (KiCad calculator, a Python
   script, openEMS for the SMA launch and LO via).
2. Smoke-test each candidate that can run unattended, in a container built from
   `docker/Dockerfile.sim` (kept separate from `fmcw3-tools`): an RC low-pass AC sweep in
   ngspice checked against the formula; one vendor op-amp model loading and running; a scikit-rf
   two-stage cascade checked by hand; an openEMS microstrip line returning about 50 ohm; LTspice
   or ADIsimPLL under Wine starting in batch mode if it can be installed without a GUI. Record
   pass, fail or not attempted, with the error text. Keep the passing cases as
   `tests/test_sim_smoke.py` (skipped with a reason when the sim image is absent).
3. Write `docs/analysis-tools.md`: a table per need (tool, replaces, how it runs, licence, smoke
   result, limits), `## Verdict` (the tool chosen for each later directive in `sim-spurs` and
   `rf-review`), and `## Tools the user must obtain` (anything GUI-only, licensed or
   registration-walled, with the link and what it is needed for).
4. Propose amendments to the `sim-spurs` and `rf-review` directives that follow from the
   verdict, as a list at the end of the doc. Do not edit those directives here.
5. (Steps 5 to 11 are an amendment the user approved on 2026-11-20 after the first review.
   Prefer validated tools: industry or vendor tools first, and the repo's own code only where
   none fits, each piece backed by a downloaded and checked source.)
   Sources pipeline. `tools/fetch_sources.py` reads two manifests:
   - `datasheets/manifest.yaml` for datasheets and vendor models;
   - `docs/references/manifest.yaml` for papers, textbooks, app notes and documents.

   Each entry has: id, kind, title, a public `url` (so other repos can fetch the same file),
   `access` (`direct`, `form` or `login`), file path, sha256, licence, and `commit: yes/no`.
   Reference entries also have `verified:` items (page, the equation or worked example, a short
   quote), filled in by reading the downloaded file.

   The script downloads `direct` entries, prints a to-do list with links for `form` and `login`
   entries for the user, and stores files under gitignored paths unless the licence allows
   committing. `--check` fails on a missing file, a hash mismatch, or a reference with no
   `verified` item. Add `tests/test_sources.py` with fixtures (no network).

   This pipeline replaces par-02's planned manifest format; par-02 fills it for the critical parts.
6. `./run --sim <cmd>`: run the command in the `fmcw3-sim` image with the repo mounted, the same
   way `./run` runs `fmcw3-tools`. `tests/test_sim_smoke.py` must pass through it, not skip.
7. LTspice through `spicelib` under Wine, in `fmcw3-sim`. Install LTspice non-interactively at
   image build, downloading the installer there and never committing it. Smoke tests:
   - an RC low-pass run through `spicelib` and LTspice, matching the formula;
   - an ADI model from LTspice's bundled library, or LT6232 if the user has supplied it through
     the manifest, running in LTspice;
   - one TI PSpice-format model (public, or the user's LMR51420, LP5907 or LD3920 zip) running
     in both LTspice and ngspice, with the two results compared.

   The last test settles circuits where ADI and TI parts interact, for example a TI LDO feeding
   an ADI op-amp or VCO. These run in LTspice if TI models run there. Record pass or fail with the
   error text.
8. Wine trials for ADIsimPLL, ADIsimRF and Saturn PCB Toolkit: download (or list as user-fetch),
   install unattended under xvfb, and record whether each installs and whether it has any batch
   or command-line mode. For a GUI-only tool, write a short checklist the user follows (inputs,
   and the outputs to record in the repo). Record the JLCPCB online impedance calculator as the
   fab's own reference for its stackups (browser, user-run).
9. References. For each calculation the later analyses implement themselves (microstrip and
   grounded-CPW impedance, the Friis cascade, the radar range equation, the buck power stage, PLL
   loop filter and phase noise, mixing products and spurs), add at least one source to
   `docs/references/manifest.yaml`. Prefer free downloads (TI SLVA477, Banerjee's "PLL
   Performance, Simulation and Design", ADI and Mini-Circuits app notes). List paywalled ones,
   such as Hammerstad and Jensen 1980, as user-fetch. Fetch each one and fill in its `verified`
   items from the file itself.
10. `tests/test_analysis_tools_doc.py`: `docs/analysis-tools.md` has `## Verdict`,
    `## Tools the user must obtain` and `## References`, and every manifest id cited in it exists
    in a manifest. This is a test, not a grep in Verify, because the `bash_file_io` hook denies a
    Verify line that reads files (friday issue #33).
11. Update `docs/analysis-tools.md` with Edit (the file exists; Claude Code refuses subagent Write
    of report-style files):
    - rows for spicelib and LTspice, ADIsimPLL, ADIsimRF, Saturn, the JLCPCB calculator, and
      commercial full-wave solvers (CST, HFSS) with what they would add over openEMS;
    - the Verdict, now preferring validated tools: LTspice for ADI-model and mixed ADI+TI
      circuits, ngspice for TI-only circuits, vendor and fab calculators as references, and the
      repo's own code only for sweeps those tools cannot do, each tied to a reference id;
    - `## References` listing manifest ids, links and verified pages;
    - updated user-fetch items and amendments.

## Acceptance
- Every tool named in review-plan Phases 3 and 6 (LTspice, TI WEBENCH, TI PSpice model,
  ADIsimPLL, KiCad calculator, openEMS, scikit-rf) has a row with a Linux route or "no route".
- Each "pass" in the table corresponds to a test in `tests/test_sim_smoke.py` or a logged command
  and output in the doc.
- `## Verdict` names exactly one primary tool per analysis and says why.
- `## Tools the user must obtain` is present, even if it says none.
- LTspice through `spicelib` has a pass backed by a test in `tests/test_sim_smoke.py`, or a fail
  with its error text.
- The verdict for mixed ADI and TI circuits names one engine and is backed by the cross-engine
  TI model test or a stated failure.
- Every entry in `## References` has a manifest id and a public link, and the manifest has at
  least one `verified` item for it that was read from the downloaded file.
- ADIsimPLL, ADIsimRF and Saturn PCB Toolkit each have a row with an install result, and CST or
  HFSS has a row comparing it with openEMS.

## Rules
- Never commit an installer, a vendor model or a PDF whose licence does not allow it.
- A reference counts only after it has been downloaded and checked against the file, never from
  memory.

## Review
- Open `docs/analysis-tools.md`, `## Verdict` and `## Tools the user must obtain`: do you accept
  the tool choices, and is anything listed that you cannot or do not want to install.

## Out of scope
- Running the actual board simulations (goal `sim-spurs`).
- Windows virtual machines.

## Allowed commands
- `docker build -t fmcw3-sim* *`
- `./run *`

## Log

### 2026-11-20
Commits:
- 5195480 fnd-05: sim image (docker/Dockerfile.sim) and smoke tests for ngspice, scikit-rf, openEMS
- 1e81af4 fnd-05: docs/analysis-tools.md (steps 3-4), written in the main session
Notes:
- fnd-05 step 1: candidate survey (inspection only, nothing installed or run yet; "smoke" column is step 2's job). Host: Ubuntu 24.04, docker present, kicad-cli 10.0.5. Not on host: ngspice, qucs-s, wine, openEMS, scikit-rf. apt (noble) has: ngspice 42+ds-3build1, wine 9.0, python3-scikit-rf 0.30.0. apt has no openems and no qucs-s. PyPI has scikit-rf 2.2.0. Facts about vendor tools below come from general knowledge and need confirming in step 2/3 (marked "verify").
- Need: SPICE engine (Phase 6 items 1-3)
- ngspice: native apt (42) or in Docker; batch mode (-b) works headless; licence BSD-3 / modified BSD. Primary candidate. Replaces LTspice.
- KiCad built-in simulator: it is a front end to ngspice (kicad-cli has `sch export netlist --format spice` and `sch erc`; verify whether KiCad 10 has a CLI simulation command). Needs GUI to run sims interactively, so only the netlist export can be unattended. Use for generating netlists from the board schematic, ngspice for running.
- Qucs-S: GUI front end to ngspice/Xyce; not in apt on noble; would need flatpak/AppImage/source. Unattended use is limited (qucsator_rf CLI exists, verify). Not needed if ngspice works; fallback only.
- LTspice under Wine: wine 9.0 in apt; LTspice (ADI, free, registration-free download from analog.com) installs under Wine, GUI-first; batch via `ltspice -b file.net` works on Windows, under Wine unattended is unproven (verify). Licence: freeware, not open. Not a Linux-native route; try only if models need LTspice-only syntax.
- Need: vendor models (Phase 6 items 1-3)
- ADI LT6232: ADI ships LTspice-library models (LTC.lib / LTC3.lib macro-models), which are mostly SPICE3 subcircuits; many load in ngspice, some use LTspice-only extensions (behavioural B-sources with LTspice syntax, `.param` expressions, `table()`), verify per model. Model file source: analog.com product page / LTspice install dir (the LTspice install is under ADI licence; check redistribution before committing it). Fallback: a simple behavioural op-amp (GBW, Rout, slew) from the datasheet in ngspice.
- LD3920 (TI) and LP5907 (TI): TI supplies PSpice (and for newer parts TINA-TI) models as downloads from ti.com product page (may need a TI login for the download; verify). The PSRR curve matters more than the exact model: fallback is a behavioural LDO (VCVS + RC with a PSRR curve entered from the datasheet) in ngspice.
- TI LMR51420: TI PSpice model (average or switching, verify which) is zip from the ti.com product page. ngspice PSpice-compat: `ngspice` supports `.lib` of PSpice-style subckts with `set ngbehavior=psa` (or `ps`/`ltpsa`); encrypted or vendor-protected models (TI often ships .lib in plain text, but some use encrypted `.ENC`) will fail. Verify by loading the real file in step 2. Fallback: build a buck averaged model by hand in ngspice.
- Ferrite beads: Murata (SimSurfing, S-parameter and SPICE netlists, free download), TDK (SEAT, netlist), Taiyo Yuden, Wurth (REDEXPERT). Murata netlists are plain subckts and load in ngspice. The specific bead part is in the BOM (check parts/parts.csv in step 3). Need a bead impedance-vs-frequency under DC bias; datasheet curve with an RLC fit is the fallback. Netlist files are vendor-downloaded: user may have to fetch them (web forms).
- Need: buck design (Phase 6 item 2)
- TI WEBENCH: web browser only, TI account required, no Linux-native/unattended route (cannot be smoke-tested). Candidate for the user to run by hand; export gives a PSpice-ish schematic and a bill of materials. Replaces nothing needed if hand calc works.
- Hand calculation from the LMR51420 datasheet: inductor ripple dI = Vout*(1-D)/(L*fsw), peak = Iout + dI/2 vs inductor Isat, D = Vout/Vin, plus loop crossover check. A short Python script, unattended, runs anywhere. Primary for the L5-L7 33 uH replacement (ripple and saturation margin); stability from the TI PSpice model in ngspice if it loads, else the datasheet's recommended L/C ranges.
- Need: PLL (Phase 6 item 4, Phase 7)
- ADIsimPLL: Windows-only GUI, free from ADI but registration-walled (verify current status; ADI has been moving users to ADIsimPLL v5/web?). Under Wine: not unattended (GUI, no documented batch mode). Flag as "user must obtain" and as not smoke-testable.
- Open Python models: no maintained ADF4158-specific tool; the loop-filter design is standard 3rd-order passive (scipy.signal for transfer function, loop BW, phase margin) and phase noise is a sum of reference, PFD/CP, VCO and divider contributions with the textbook model (e.g. from ADI application notes AN-1000?, verify) in numpy. Also pyPLL/other PyPI packages exist (verify) but unmaintained. A short script written for this repo is the likely primary; ADIsimPLL is the user's cross-check for the datasheet's ADF4158 specifics. Also ngspice can simulate the loop filter plus VCO KV as a linear block.
- Need: RF cascade and S-parameters (Phase 2)
- scikit-rf: pure Python, BSD-3, `pip install scikit-rf` (2.2.0) or apt python3-scikit-rf 0.30.0; Network, cascade (`**`), s2p read, noise figure via Friis from `Network.noisy`/manual. Runs unattended in the sim container. Primary. Hand check: two-stage cascade of known gains and a lossy line.
- Need: transmission lines (Phase 3)
- KiCad Calculator Tools (PCB Calculator): GUI-only (no kicad-cli command for it); use by hand as the independent check the plan asks for. Native. GPLv3. Not smoke-testable unattended.
- Python script (Hammerstad-Jensen microstrip, conductor-backed CPW with elliptic integrals; scipy.special.ellipk): unattended, committed to the repo; the plan already lists its numbers (microstrip 0.23 mm eps 4.5 = 43.0 ohm; CPWG 0.2 gap 47.5 ohm) so it can be checked against them. Primary for width/gap/eps sweeps.
- scikit-rf also has `skrf.media.CPW` and `MLine` for a quasi-static cross-check against the script.
- openEMS (FDTD, GPLv3): not in Ubuntu noble apt. Routes: build from source (github.com/thliebig/openEMS-Project, needs CSXCAD, hdf5, vtk, boost, cgal etc.) inside Docker; or the openEMS PPA/OBS packages (verify); python bindings `openEMS` and `CSXCAD`. Microstrip 50 ohm smoke test (the openEMS tutorial MSL model) is feasible unattended in a container but the build is heavy; if the build fails, record fail with the error. Use only for the optional SMA launch and LO via check (Phase 3 last item); also needs the footprint geometry (CONSMA003.062) and stackup: model setup is manual. Gerber-import tooling (pcbmodelers/Gerber2CSX) is an option, verify.
- STEP 2 smoke results (image fmcw3-sim from docker/Dockerfile.sim, ubuntu 24.04; ngspice-42, scikit-rf 2.2.0, openEMS v0.37.0-83 built from source with python bindings, wine 9.0 + wine32; builds in ~25 min first time). Run on the host with `python3 -m pytest tests/test_sim_smoke.py`: 4 passed in ~22 s. Under `./run` (fmcw3-tools container has no docker) the 4 tests SKIP with the reason "sim image absent": the Verify line only proves the skip path; the real run needs the host.
- PASS ngspice RC low-pass AC sweep: -3.01 dB at 1 kHz, -20.04 dB at 10 kHz, matches 10log10(1+(f/fc)^2) within 0.02 dB (test_ngspice_rc_lowpass_matches_formula).
- PASS ngspice loads a .lib subckt and runs it (generic 2-pole macro-model, closed-loop gain 10, 0.2 V in -> 2.0 V, 20 dB): test_ngspice_loads_subckt_model_and_runs. This is NOT a vendor model (see next two lines).
- FAIL vendor op-amp model: LT6232 not obtainable unattended (analog.com model URL: curl exit 28 timeout over HTTP/1.1, exit 92 HTTP/2 stream error on the site root; not in LTspice's bundled lib either: no LT6232 in lib/sub/LTC.lib or any lib/sub file). Substitute ADI LT1007 from LTspice's bundled LTC.lib loaded in ngspice-42: `MIF-ERROR - unable to find definition of model 120` on `a.x1.a1 fb in 0 0 0 0 0 0 x1.ota ...` plus `no such function 'uplim'`; same error with `set ngbehavior=ltpsa`. So LTC.lib models use LTspice-only A-device/functions and do not load in ngspice. LT6232 itself: user must fetch from the analog.com product page (or use a datasheet macro-model).
- PASS scikit-rf two-stage cascade (-3 dB attenuator ** +20 dB amp = +17.000 dB S21; Friis NF by hand; lossy line 0.1 Np/m x 0.2 m = -0.1737 dB, adds in dB with the amp): test_scikit_rf_two_stage_cascade.
- PASS openEMS microstrip 50 ohm (h 1.0 mm, er 4.3, w 1.95 mm, tutorial MSL_NotchFilter geometry minus the stub, PML_8 in x): line Z0 extracted from the MSL port 48.8 ohm (Hammerstad-Jensen: ~49-50), S11 max -33 dB, S21 -0.02 dB; 370k cells, ~21 s. Pitfalls found: port z start/stop must be strip->ground (start z = h, stop z = 0) else V/I is garbage; with ref_impedance=50 Z_ref is just 50 by definition, so read Z_ref from CalcPort without ref_impedance; pip numpy 2 (via scikit-rf) shadows apt numpy so h5py must be pip-installed in the venv (--ignore-installed). test_openems_microstrip_about_50_ohm.
- PARTIAL LTspice under Wine: ltspice.analog.com/software/LTspice64.msi downloads unattended (HTTP 200, 145 MB, no registration). Installs headless with `wine msiexec /i Z:\path\LTspice64.msi /qn` under xvfb-run, but only once wine32:i386 is installed (without it: "it looks like wine32 is missing"); then C:\Program Files\ADI\LTspice\LTspice.exe exists. Batch `LTspice.exe -b C:\rc.net` (200 s timeout, xvfb) started (ntlm_auth warnings only) but wrote no rc.log/.raw anywhere: FAIL for unattended batch, not pursued further (the -Run flag and a GUI session not tried). Verdict input: LTspice is a GUI tool for the user to run, ngspice is the unattended route. Not committed/test-kept (licence, 145 MB download).
- NOT ATTEMPTED ADIsimPLL: Windows GUI installer behind ADI registration, no batch mode.
- NOT ATTEMPTED TI PSpice models (LMR51420, LP5907, LD3920) in ngspice psa mode: ti.com zip download is a web form (https://www.ti.com/lit/zip/snvmb09 gave a 302, not followed); user must fetch.
- Open observations for the doc: (1) Phase 3 says "Python script, can be committed", so the transmission-line verdict is the script, KiCad calculator being the independent hand check. (2) Several vendor-model downloads (TI, ADI, Murata) sit behind web forms or accounts: these belong under "Tools the user must obtain" even where ngspice itself is native. (3) Phase 6 lists LTspice/WEBENCH/ADIsimPLL; the Linux replacements are ngspice, hand calc plus ngspice, and a Python PLL script. (4) The container for step 2 must include ngspice, python+scipy+scikit-rf, and an openEMS build; Wine+LTspice as a separate optional layer. The directive's Dockerfile.sim path is `docker/Dockerfile.sim`; docker/ currently has only Dockerfile (fmcw3-tools) and README.md.
Verify: Verify passed via friday verify fnd-05 (exit 0): docs/analysis-tools.md sections present; tests/test_sim_smoke.py 4 skipped under ./run (no sim image inside fmcw3-tools); on the host the same tests give 4 passed (runs/fnd-05/notes.md). The workflow's raw Bash Verify was denied by the bash_file_io hook.
Independent review: Not run by the workflow (Verify gate blocked by the hook). Steps 3-4 doc written in the main session (1e81af4) because subagent writes of it are refused; user reviews it under Accept: user.

Rejected by user: 2026-11-20 Re-run with validated tools

### 2026-11-20
Unblocked: was blocked: Re-run with validated tools

### 2026-11-20
Commits:
- 5195480 fnd-05: sim image (docker/Dockerfile.sim) and smoke tests for ngspice, scikit-rf, openEMS
- 1e81af4 fnd-05: docs/analysis-tools.md (steps 3-4), written in the main session
- 2b979c8 fnd-05: analysis-tools.md claims match the evidence (independent review)
- 937418a fnd-05: sources pipeline (tools/fetch_sources.py, manifests, tests)
- 32bd45d fnd-05: ./run --sim runs a command in the fmcw3-sim image
- f7f9a3b fnd-05: LTspice through spicelib under Wine in fmcw3-sim, with smoke tests
- 9d20c85 fnd-05: step 8, trial results and user checklists for ADIsimPLL, ADIsimRF, Saturn, JLCPCB calculator
- 51f2ac2 fnd-05: step 9, reference manifest for buck, PLL, radar equation, Friis, mixer spurs, microstrip and CPWG
- e57b1e3 fnd-05: step 10, test that analysis-tools.md has its sections and cites only manifest ids
- e2271db fnd-05: step 11, analysis-tools.md with validated-tool verdict, new tool rows, References and amendments
- 4bd4cdd fnd-05: move unverified vendor models out of References, test that cited ids have verified items
Notes:
- fnd-05 step 1: candidate survey (inspection only, nothing installed or run yet; "smoke" column is step 2's job). Host: Ubuntu 24.04, docker present, kicad-cli 10.0.5. Not on host: ngspice, qucs-s, wine, openEMS, scikit-rf. apt (noble) has: ngspice 42+ds-3build1, wine 9.0, python3-scikit-rf 0.30.0. apt has no openems and no qucs-s. PyPI has scikit-rf 2.2.0. Facts about vendor tools below come from general knowledge and need confirming in step 2/3 (marked "verify").
- Need: SPICE engine (Phase 6 items 1-3)
- ngspice: native apt (42) or in Docker; batch mode (-b) works headless; licence BSD-3 / modified BSD. Primary candidate. Replaces LTspice.
- KiCad built-in simulator: it is a front end to ngspice (kicad-cli has `sch export netlist --format spice` and `sch erc`; verify whether KiCad 10 has a CLI simulation command). Needs GUI to run sims interactively, so only the netlist export can be unattended. Use for generating netlists from the board schematic, ngspice for running.
- Qucs-S: GUI front end to ngspice/Xyce; not in apt on noble; would need flatpak/AppImage/source. Unattended use is limited (qucsator_rf CLI exists, verify). Not needed if ngspice works; fallback only.
- LTspice under Wine: wine 9.0 in apt; LTspice (ADI, free, registration-free download from analog.com) installs under Wine, GUI-first; batch via `ltspice -b file.net` works on Windows, under Wine unattended is unproven (verify). Licence: freeware, not open. Not a Linux-native route; try only if models need LTspice-only syntax.
- Need: vendor models (Phase 6 items 1-3)
- ADI LT6232: ADI ships LTspice-library models (LTC.lib / LTC3.lib macro-models), which are mostly SPICE3 subcircuits; many load in ngspice, some use LTspice-only extensions (behavioural B-sources with LTspice syntax, `.param` expressions, `table()`), verify per model. Model file source: analog.com product page / LTspice install dir (the LTspice install is under ADI licence; check redistribution before committing it). Fallback: a simple behavioural op-amp (GBW, Rout, slew) from the datasheet in ngspice.
- LD3920 (TI) and LP5907 (TI): TI supplies PSpice (and for newer parts TINA-TI) models as downloads from ti.com product page (may need a TI login for the download; verify). The PSRR curve matters more than the exact model: fallback is a behavioural LDO (VCVS + RC with a PSRR curve entered from the datasheet) in ngspice.
- TI LMR51420: TI PSpice model (average or switching, verify which) is zip from the ti.com product page. ngspice PSpice-compat: `ngspice` supports `.lib` of PSpice-style subckts with `set ngbehavior=psa` (or `ps`/`ltpsa`); encrypted or vendor-protected models (TI often ships .lib in plain text, but some use encrypted `.ENC`) will fail. Verify by loading the real file in step 2. Fallback: build a buck averaged model by hand in ngspice.
- Ferrite beads: Murata (SimSurfing, S-parameter and SPICE netlists, free download), TDK (SEAT, netlist), Taiyo Yuden, Wurth (REDEXPERT). Murata netlists are plain subckts and load in ngspice. The specific bead part is in the BOM (check parts/parts.csv in step 3). Need a bead impedance-vs-frequency under DC bias; datasheet curve with an RLC fit is the fallback. Netlist files are vendor-downloaded: user may have to fetch them (web forms).
- Need: buck design (Phase 6 item 2)
- TI WEBENCH: web browser only, TI account required, no Linux-native/unattended route (cannot be smoke-tested). Candidate for the user to run by hand; export gives a PSpice-ish schematic and a bill of materials. Replaces nothing needed if hand calc works.
- Hand calculation from the LMR51420 datasheet: inductor ripple dI = Vout*(1-D)/(L*fsw), peak = Iout + dI/2 vs inductor Isat, D = Vout/Vin, plus loop crossover check. A short Python script, unattended, runs anywhere. Primary for the L5-L7 33 uH replacement (ripple and saturation margin); stability from the TI PSpice model in ngspice if it loads, else the datasheet's recommended L/C ranges.
- Need: PLL (Phase 6 item 4, Phase 7)
- ADIsimPLL: Windows-only GUI, free from ADI but registration-walled (verify current status; ADI has been moving users to ADIsimPLL v5/web?). Under Wine: not unattended (GUI, no documented batch mode). Flag as "user must obtain" and as not smoke-testable.
- Open Python models: no maintained ADF4158-specific tool; the loop-filter design is standard 3rd-order passive (scipy.signal for transfer function, loop BW, phase margin) and phase noise is a sum of reference, PFD/CP, VCO and divider contributions with the textbook model (e.g. from ADI application notes AN-1000?, verify) in numpy. Also pyPLL/other PyPI packages exist (verify) but unmaintained. A short script written for this repo is the likely primary; ADIsimPLL is the user's cross-check for the datasheet's ADF4158 specifics. Also ngspice can simulate the loop filter plus VCO KV as a linear block.
- Need: RF cascade and S-parameters (Phase 2)
- scikit-rf: pure Python, BSD-3, `pip install scikit-rf` (2.2.0) or apt python3-scikit-rf 0.30.0; Network, cascade (`**`), s2p read, noise figure via Friis from `Network.noisy`/manual. Runs unattended in the sim container. Primary. Hand check: two-stage cascade of known gains and a lossy line.
- Need: transmission lines (Phase 3)
- KiCad Calculator Tools (PCB Calculator): GUI-only (no kicad-cli command for it); use by hand as the independent check the plan asks for. Native. GPLv3. Not smoke-testable unattended.
- Python script (Hammerstad-Jensen microstrip, conductor-backed CPW with elliptic integrals; scipy.special.ellipk): unattended, committed to the repo; the plan already lists its numbers (microstrip 0.23 mm eps 4.5 = 43.0 ohm; CPWG 0.2 gap 47.5 ohm) so it can be checked against them. Primary for width/gap/eps sweeps.
- scikit-rf also has `skrf.media.CPW` and `MLine` for a quasi-static cross-check against the script.
- openEMS (FDTD, GPLv3): not in Ubuntu noble apt. Routes: build from source (github.com/thliebig/openEMS-Project, needs CSXCAD, hdf5, vtk, boost, cgal etc.) inside Docker; or the openEMS PPA/OBS packages (verify); python bindings `openEMS` and `CSXCAD`. Microstrip 50 ohm smoke test (the openEMS tutorial MSL model) is feasible unattended in a container but the build is heavy; if the build fails, record fail with the error. Use only for the optional SMA launch and LO via check (Phase 3 last item); also needs the footprint geometry (CONSMA003.062) and stackup: model setup is manual. Gerber-import tooling (pcbmodelers/Gerber2CSX) is an option, verify.
- STEP 2 smoke results (image fmcw3-sim from docker/Dockerfile.sim, ubuntu 24.04; ngspice-42, scikit-rf 2.2.0, openEMS v0.37.0-83 built from source with python bindings, wine 9.0 + wine32; builds in ~25 min first time). Run on the host with `python3 -m pytest tests/test_sim_smoke.py`: 4 passed in ~22 s. Under `./run` (fmcw3-tools container has no docker) the 4 tests SKIP with the reason "sim image absent": the Verify line only proves the skip path; the real run needs the host.
- PASS ngspice RC low-pass AC sweep: -3.01 dB at 1 kHz, -20.04 dB at 10 kHz, matches 10log10(1+(f/fc)^2) within 0.02 dB (test_ngspice_rc_lowpass_matches_formula).
- PASS ngspice loads a .lib subckt and runs it (generic 2-pole macro-model, closed-loop gain 10, 0.2 V in -> 2.0 V, 20 dB): test_ngspice_loads_subckt_model_and_runs. This is NOT a vendor model (see next two lines).
- FAIL vendor op-amp model: LT6232 not obtainable unattended (analog.com model URL: curl exit 28 timeout over HTTP/1.1, exit 92 HTTP/2 stream error on the site root; not in LTspice's bundled lib either: no LT6232 in lib/sub/LTC.lib or any lib/sub file). Substitute ADI LT1007 from LTspice's bundled LTC.lib loaded in ngspice-42: `MIF-ERROR - unable to find definition of model 120` on `a.x1.a1 fb in 0 0 0 0 0 0 x1.ota ...` plus `no such function 'uplim'`; same error with `set ngbehavior=ltpsa`. So LTC.lib models use LTspice-only A-device/functions and do not load in ngspice. LT6232 itself: user must fetch from the analog.com product page (or use a datasheet macro-model).
- PASS scikit-rf two-stage cascade (-3 dB attenuator ** +20 dB amp = +17.000 dB S21; Friis NF by hand; lossy line 0.1 Np/m x 0.2 m = -0.1737 dB, adds in dB with the amp): test_scikit_rf_two_stage_cascade.
- PASS openEMS microstrip 50 ohm (h 1.0 mm, er 4.3, w 1.95 mm, tutorial MSL_NotchFilter geometry minus the stub, PML_8 in x): line Z0 extracted from the MSL port 48.8 ohm (Hammerstad-Jensen: ~49-50), S11 max -33 dB, S21 -0.02 dB; 370k cells, ~21 s. Pitfalls found: port z start/stop must be strip->ground (start z = h, stop z = 0) else V/I is garbage; with ref_impedance=50 Z_ref is just 50 by definition, so read Z_ref from CalcPort without ref_impedance; pip numpy 2 (via scikit-rf) shadows apt numpy so h5py must be pip-installed in the venv (--ignore-installed). test_openems_microstrip_about_50_ohm.
- PARTIAL LTspice under Wine: ltspice.analog.com/software/LTspice64.msi downloads unattended (HTTP 200, 145 MB, no registration). Installs headless with `wine msiexec /i Z:\path\LTspice64.msi /qn` under xvfb-run, but only once wine32:i386 is installed (without it: "it looks like wine32 is missing"); then C:\Program Files\ADI\LTspice\LTspice.exe exists. Batch `LTspice.exe -b C:\rc.net` (200 s timeout, xvfb) started (ntlm_auth warnings only) but wrote no rc.log/.raw anywhere: FAIL for unattended batch, not pursued further (the -Run flag and a GUI session not tried). Verdict input: LTspice is a GUI tool for the user to run, ngspice is the unattended route. Not committed/test-kept (licence, 145 MB download).
- NOT ATTEMPTED ADIsimPLL: Windows GUI installer behind ADI registration, no batch mode.
- NOT ATTEMPTED TI PSpice models (LMR51420, LP5907, LD3920) in ngspice psa mode: ti.com zip download is a web form (https://www.ti.com/lit/zip/snvmb09 gave a 302, not followed); user must fetch.
- Open observations for the doc: (1) Phase 3 says "Python script, can be committed", so the transmission-line verdict is the script, KiCad calculator being the independent hand check. (2) Several vendor-model downloads (TI, ADI, Murata) sit behind web forms or accounts: these belong under "Tools the user must obtain" even where ngspice itself is native. (3) Phase 6 lists LTspice/WEBENCH/ADIsimPLL; the Linux replacements are ngspice, hand calc plus ngspice, and a Python PLL script. (4) The container for step 2 must include ngspice, python+scipy+scikit-rf, and an openEMS build; Wine+LTspice as a separate optional layer. The directive's Dockerfile.sim path is `docker/Dockerfile.sim`; docker/ currently has only Dockerfile (fmcw3-tools) and README.md.
- STEP 7 (commit f7f9a3b) LTspice 26.1.1 under Wine 9.0 through spicelib 1.6.4, in fmcw3-sim. Run: ./run --sim python3 -m pytest tests/test_sim_smoke.py -q -> 10 passed (host and ./run --sim); ./run uv run pytest tests -q -> 33 passed, 10 skipped (sim tests skip in fmcw3-tools); fetch_sources --check ok.
- Correction of the step 2 LTspice FAIL: batch mode did work-able; the hang was LTspice's first-run dialog "Anonymously Share LTspice Usage Data" (seen with xwininfo and a screenshot under Xvfb) which blocks -b until answered. Fix: ini key CaptureAnalytics=false in drive_c/users/root/AppData/Roaming/LTspice.ini, written at image build. First run also unpacks lib.zip into AppData/Local/LTspice/lib (the ADI model library); the build does a warm-up run for that.
- Wine refuses a prefix not owned by the caller (host uid differs from build root). Fix: prefix baked at /opt/wineprefix, chmod a+rwX; tests/sim/ltspice_smoke.py makes a per-run dir of symlinks into it and sets USER=root so the baked profile is reused. No 1.7 GB copy needed.
- spicelib: set LTSPICEFOLDER/LTSPICEEXECUTABLE to the baked LTspice.exe; run under xvfb-run. Pass SimRunner.run_now a netlist PATH, not a SpiceEditor: the editor parses included vendor libs and fails on TI's "VALUE { + IF(...) }" continuation lines. LTspice also writes <tag>.op.raw beside <tag>.raw (run_now may return the op one); RawRead.get_axis fails on these files, read the first trace instead. ngspice raw needs RawRead(dialect="ngspice") and lower-case trace names.
- PASS RC low-pass in LTspice via spicelib: 41 points 10 Hz-100 kHz, worst error 7e-15 dB vs 10log10(1+(f/fc)^2), -3.010 dB at 1 kHz.
- PASS ADI model in LTspice: LT6232 is not a subckt of its own in LTspice's bundled lib, but the LT6232 symbol (lib/sym/OpAmps/LT6232.asy, description "Quad 215 MHz ... Op Amp") has SYMATTR SpiceModel LTC2.lib and Value2 LT6231, i.e. it uses the LT6231 subckt in lib/sub/LTC2.lib. LT6231 non-inverting gain of 10 on +/-2.5 V: 20.000 dB at 1 kHz, DC out 2.045 V for 0.2 V in. Caveat found: the model reproduces the real input range limit; on a single 5 V supply (V- = 0) a 1 V follower gives 1.27 V and the gain-of-10 test with 0.25 V in gave a railed output; it is the model (inputs near V- clamp), not Wine. LT6232 pins: 1 IN+, 2 IN-, 3 OUT, 4 VCC, 5 VEE.
- FAIL (expected) the same LT6231 in ngspice 42: "Error on line: a.x1.a1 fb in 0 0 0 0 0 0 x1.ota ... MIF-ERROR - unable to find definition of model 33.5" (LTspice A-device OTA). So ADI LTC*.lib models need LTspice.
- PASS TI PSpice model in both engines: public TI LP5907 1.8 V unencrypted model (https://www.ti.com/lit/zip/snvmap9, plain text, downloads without login with a normal User-Agent; the "unencrypted" PSpice models on the LP5907 page are plain). 3.6 V ramp in 100 us, 180 ohm load, 1 uF in/out: Vout(2 ms) 1.8001 V in LTspice and in ngspice-42 with .options ngbehavior=psa; max difference between the engines at 6 times from 50 us to 2 ms is 0.0010 V. So TI PSpice models run in LTspice and (when unencrypted) in ngspice.
- PASS mixed circuit in LTspice: TI LP5907 PSpice model feeding an ADI LT6231 follower (+/-3.3 V rails) in one netlist: LDO out 1.8001 V, buffer out 1.8001 V. On +/-2.5 V rails the follower gives 1.70 V (input range clamp), another reminder of the LT6231 input range. Verdict input: LTspice is the one engine that runs both ADI LTC models and TI PSpice models; use it for mixed ADI+TI circuits.
- FAIL (expected) TI LMR51420XF model (https://www.ti.com/lit/zip/slum825, 295 KB, direct download): the .LIB is TI-encrypted ("**$ENCRYPTED_LIB", Cadence $CDNENCSTART_ADV2 blocks). LTspice: "Z:\...\LMR51420XF.lib(942): Expected device instantiation or directive here." followed by the encrypted hex lines and "$CDNENCFINISH_ADV2". ngspice: encrypted lines reported as "missing tokens Line no. 1077 ...". LMR51420 therefore needs a hand-built averaged buck model in either engine. The LP5907 page also lists encrypted variants; pick the "Unencrypted" ones. LP5907 has only fixed-voltage models per option (1.2 to 4.5 V). LD3920 not looked for (the product name in the plan may be LD39200: ti.com/product/LD39200 returned 404, ST part?).
- Manifest: datasheets/manifest.yaml now has ti-lp5907-1p8-pspice and ti-lmr51420xf-pspice (direct, commit no, files under datasheets/files/ti/, sha256 recorded). Installer is deleted at build and never committed; the image is about 7 GB.
Verify: Verify passed: ./run --sim python3 -m pytest tests/test_sim_smoke.py -q && ./run uv run pytest tests -q && ./run tools/fetch_sources.py --check
Independent review: not recorded
Blocked: review gaps remain: plan commit 5c230bf (docs/directives/fnd-05.md lines 7, 38-93, 106-114): This plan edit was made after the directive started, and it changes the directive's Verify line, adds steps 5-11, adds Acceptance bullets and adds the ## Rules section. Under the review rules that is a gap unless the user approved it. The evidence points to approval but I cannot confirm it from the repo, so the caller should check with the user and close this.

### 2026-11-20
Unblocked: was blocked: review gaps remain: plan commit 5c230bf (docs/directives/fnd-05.md lines 7, 38-93, 106-114): This plan edit was made after the directive started, and it changes the directive's Verify line, adds steps 5-11, adds Acceptance bullets and adds the ## Rules section. Under the review rules that is a gap unless the user approved it. The evidence points to approval but I cannot confirm it from the repo, so the caller should check with the user and close this.

### 2026-11-20
Commits:
- 5195480 fnd-05: sim image (docker/Dockerfile.sim) and smoke tests for ngspice, scikit-rf, openEMS
- 1e81af4 fnd-05: docs/analysis-tools.md (steps 3-4), written in the main session
- 2b979c8 fnd-05: analysis-tools.md claims match the evidence (independent review)
- 937418a fnd-05: sources pipeline (tools/fetch_sources.py, manifests, tests)
- 32bd45d fnd-05: ./run --sim runs a command in the fmcw3-sim image
- f7f9a3b fnd-05: LTspice through spicelib under Wine in fmcw3-sim, with smoke tests
- 9d20c85 fnd-05: step 8, trial results and user checklists for ADIsimPLL, ADIsimRF, Saturn, JLCPCB calculator
- 51f2ac2 fnd-05: step 9, reference manifest for buck, PLL, radar equation, Friis, mixer spurs, microstrip and CPWG
- e57b1e3 fnd-05: step 10, test that analysis-tools.md has its sections and cites only manifest ids
- e2271db fnd-05: step 11, analysis-tools.md with validated-tool verdict, new tool rows, References and amendments
- 4bd4cdd fnd-05: move unverified vendor models out of References, test that cited ids have verified items
Notes:
- fnd-05 step 1: candidate survey (inspection only, nothing installed or run yet; "smoke" column is step 2's job). Host: Ubuntu 24.04, docker present, kicad-cli 10.0.5. Not on host: ngspice, qucs-s, wine, openEMS, scikit-rf. apt (noble) has: ngspice 42+ds-3build1, wine 9.0, python3-scikit-rf 0.30.0. apt has no openems and no qucs-s. PyPI has scikit-rf 2.2.0. Facts about vendor tools below come from general knowledge and need confirming in step 2/3 (marked "verify").
- Need: SPICE engine (Phase 6 items 1-3)
- ngspice: native apt (42) or in Docker; batch mode (-b) works headless; licence BSD-3 / modified BSD. Primary candidate. Replaces LTspice.
- KiCad built-in simulator: it is a front end to ngspice (kicad-cli has `sch export netlist --format spice` and `sch erc`; verify whether KiCad 10 has a CLI simulation command). Needs GUI to run sims interactively, so only the netlist export can be unattended. Use for generating netlists from the board schematic, ngspice for running.
- Qucs-S: GUI front end to ngspice/Xyce; not in apt on noble; would need flatpak/AppImage/source. Unattended use is limited (qucsator_rf CLI exists, verify). Not needed if ngspice works; fallback only.
- LTspice under Wine: wine 9.0 in apt; LTspice (ADI, free, registration-free download from analog.com) installs under Wine, GUI-first; batch via `ltspice -b file.net` works on Windows, under Wine unattended is unproven (verify). Licence: freeware, not open. Not a Linux-native route; try only if models need LTspice-only syntax.
- Need: vendor models (Phase 6 items 1-3)
- ADI LT6232: ADI ships LTspice-library models (LTC.lib / LTC3.lib macro-models), which are mostly SPICE3 subcircuits; many load in ngspice, some use LTspice-only extensions (behavioural B-sources with LTspice syntax, `.param` expressions, `table()`), verify per model. Model file source: analog.com product page / LTspice install dir (the LTspice install is under ADI licence; check redistribution before committing it). Fallback: a simple behavioural op-amp (GBW, Rout, slew) from the datasheet in ngspice.
- LD3920 (TI) and LP5907 (TI): TI supplies PSpice (and for newer parts TINA-TI) models as downloads from ti.com product page (may need a TI login for the download; verify). The PSRR curve matters more than the exact model: fallback is a behavioural LDO (VCVS + RC with a PSRR curve entered from the datasheet) in ngspice.
- TI LMR51420: TI PSpice model (average or switching, verify which) is zip from the ti.com product page. ngspice PSpice-compat: `ngspice` supports `.lib` of PSpice-style subckts with `set ngbehavior=psa` (or `ps`/`ltpsa`); encrypted or vendor-protected models (TI often ships .lib in plain text, but some use encrypted `.ENC`) will fail. Verify by loading the real file in step 2. Fallback: build a buck averaged model by hand in ngspice.
- Ferrite beads: Murata (SimSurfing, S-parameter and SPICE netlists, free download), TDK (SEAT, netlist), Taiyo Yuden, Wurth (REDEXPERT). Murata netlists are plain subckts and load in ngspice. The specific bead part is in the BOM (check parts/parts.csv in step 3). Need a bead impedance-vs-frequency under DC bias; datasheet curve with an RLC fit is the fallback. Netlist files are vendor-downloaded: user may have to fetch them (web forms).
- Need: buck design (Phase 6 item 2)
- TI WEBENCH: web browser only, TI account required, no Linux-native/unattended route (cannot be smoke-tested). Candidate for the user to run by hand; export gives a PSpice-ish schematic and a bill of materials. Replaces nothing needed if hand calc works.
- Hand calculation from the LMR51420 datasheet: inductor ripple dI = Vout*(1-D)/(L*fsw), peak = Iout + dI/2 vs inductor Isat, D = Vout/Vin, plus loop crossover check. A short Python script, unattended, runs anywhere. Primary for the L5-L7 33 uH replacement (ripple and saturation margin); stability from the TI PSpice model in ngspice if it loads, else the datasheet's recommended L/C ranges.
- Need: PLL (Phase 6 item 4, Phase 7)
- ADIsimPLL: Windows-only GUI, free from ADI but registration-walled (verify current status; ADI has been moving users to ADIsimPLL v5/web?). Under Wine: not unattended (GUI, no documented batch mode). Flag as "user must obtain" and as not smoke-testable.
- Open Python models: no maintained ADF4158-specific tool; the loop-filter design is standard 3rd-order passive (scipy.signal for transfer function, loop BW, phase margin) and phase noise is a sum of reference, PFD/CP, VCO and divider contributions with the textbook model (e.g. from ADI application notes AN-1000?, verify) in numpy. Also pyPLL/other PyPI packages exist (verify) but unmaintained. A short script written for this repo is the likely primary; ADIsimPLL is the user's cross-check for the datasheet's ADF4158 specifics. Also ngspice can simulate the loop filter plus VCO KV as a linear block.
- Need: RF cascade and S-parameters (Phase 2)
- scikit-rf: pure Python, BSD-3, `pip install scikit-rf` (2.2.0) or apt python3-scikit-rf 0.30.0; Network, cascade (`**`), s2p read, noise figure via Friis from `Network.noisy`/manual. Runs unattended in the sim container. Primary. Hand check: two-stage cascade of known gains and a lossy line.
- Need: transmission lines (Phase 3)
- KiCad Calculator Tools (PCB Calculator): GUI-only (no kicad-cli command for it); use by hand as the independent check the plan asks for. Native. GPLv3. Not smoke-testable unattended.
- Python script (Hammerstad-Jensen microstrip, conductor-backed CPW with elliptic integrals; scipy.special.ellipk): unattended, committed to the repo; the plan already lists its numbers (microstrip 0.23 mm eps 4.5 = 43.0 ohm; CPWG 0.2 gap 47.5 ohm) so it can be checked against them. Primary for width/gap/eps sweeps.
- scikit-rf also has `skrf.media.CPW` and `MLine` for a quasi-static cross-check against the script.
- openEMS (FDTD, GPLv3): not in Ubuntu noble apt. Routes: build from source (github.com/thliebig/openEMS-Project, needs CSXCAD, hdf5, vtk, boost, cgal etc.) inside Docker; or the openEMS PPA/OBS packages (verify); python bindings `openEMS` and `CSXCAD`. Microstrip 50 ohm smoke test (the openEMS tutorial MSL model) is feasible unattended in a container but the build is heavy; if the build fails, record fail with the error. Use only for the optional SMA launch and LO via check (Phase 3 last item); also needs the footprint geometry (CONSMA003.062) and stackup: model setup is manual. Gerber-import tooling (pcbmodelers/Gerber2CSX) is an option, verify.
- STEP 2 smoke results (image fmcw3-sim from docker/Dockerfile.sim, ubuntu 24.04; ngspice-42, scikit-rf 2.2.0, openEMS v0.37.0-83 built from source with python bindings, wine 9.0 + wine32; builds in ~25 min first time). Run on the host with `python3 -m pytest tests/test_sim_smoke.py`: 4 passed in ~22 s. Under `./run` (fmcw3-tools container has no docker) the 4 tests SKIP with the reason "sim image absent": the Verify line only proves the skip path; the real run needs the host.
- PASS ngspice RC low-pass AC sweep: -3.01 dB at 1 kHz, -20.04 dB at 10 kHz, matches 10log10(1+(f/fc)^2) within 0.02 dB (test_ngspice_rc_lowpass_matches_formula).
- PASS ngspice loads a .lib subckt and runs it (generic 2-pole macro-model, closed-loop gain 10, 0.2 V in -> 2.0 V, 20 dB): test_ngspice_loads_subckt_model_and_runs. This is NOT a vendor model (see next two lines).
- FAIL vendor op-amp model: LT6232 not obtainable unattended (analog.com model URL: curl exit 28 timeout over HTTP/1.1, exit 92 HTTP/2 stream error on the site root; not in LTspice's bundled lib either: no LT6232 in lib/sub/LTC.lib or any lib/sub file). Substitute ADI LT1007 from LTspice's bundled LTC.lib loaded in ngspice-42: `MIF-ERROR - unable to find definition of model 120` on `a.x1.a1 fb in 0 0 0 0 0 0 x1.ota ...` plus `no such function 'uplim'`; same error with `set ngbehavior=ltpsa`. So LTC.lib models use LTspice-only A-device/functions and do not load in ngspice. LT6232 itself: user must fetch from the analog.com product page (or use a datasheet macro-model).
- PASS scikit-rf two-stage cascade (-3 dB attenuator ** +20 dB amp = +17.000 dB S21; Friis NF by hand; lossy line 0.1 Np/m x 0.2 m = -0.1737 dB, adds in dB with the amp): test_scikit_rf_two_stage_cascade.
- PASS openEMS microstrip 50 ohm (h 1.0 mm, er 4.3, w 1.95 mm, tutorial MSL_NotchFilter geometry minus the stub, PML_8 in x): line Z0 extracted from the MSL port 48.8 ohm (Hammerstad-Jensen: ~49-50), S11 max -33 dB, S21 -0.02 dB; 370k cells, ~21 s. Pitfalls found: port z start/stop must be strip->ground (start z = h, stop z = 0) else V/I is garbage; with ref_impedance=50 Z_ref is just 50 by definition, so read Z_ref from CalcPort without ref_impedance; pip numpy 2 (via scikit-rf) shadows apt numpy so h5py must be pip-installed in the venv (--ignore-installed). test_openems_microstrip_about_50_ohm.
- PARTIAL LTspice under Wine: ltspice.analog.com/software/LTspice64.msi downloads unattended (HTTP 200, 145 MB, no registration). Installs headless with `wine msiexec /i Z:\path\LTspice64.msi /qn` under xvfb-run, but only once wine32:i386 is installed (without it: "it looks like wine32 is missing"); then C:\Program Files\ADI\LTspice\LTspice.exe exists. Batch `LTspice.exe -b C:\rc.net` (200 s timeout, xvfb) started (ntlm_auth warnings only) but wrote no rc.log/.raw anywhere: FAIL for unattended batch, not pursued further (the -Run flag and a GUI session not tried). Verdict input: LTspice is a GUI tool for the user to run, ngspice is the unattended route. Not committed/test-kept (licence, 145 MB download).
- NOT ATTEMPTED ADIsimPLL: Windows GUI installer behind ADI registration, no batch mode.
- NOT ATTEMPTED TI PSpice models (LMR51420, LP5907, LD3920) in ngspice psa mode: ti.com zip download is a web form (https://www.ti.com/lit/zip/snvmb09 gave a 302, not followed); user must fetch.
- Open observations for the doc: (1) Phase 3 says "Python script, can be committed", so the transmission-line verdict is the script, KiCad calculator being the independent hand check. (2) Several vendor-model downloads (TI, ADI, Murata) sit behind web forms or accounts: these belong under "Tools the user must obtain" even where ngspice itself is native. (3) Phase 6 lists LTspice/WEBENCH/ADIsimPLL; the Linux replacements are ngspice, hand calc plus ngspice, and a Python PLL script. (4) The container for step 2 must include ngspice, python+scipy+scikit-rf, and an openEMS build; Wine+LTspice as a separate optional layer. The directive's Dockerfile.sim path is `docker/Dockerfile.sim`; docker/ currently has only Dockerfile (fmcw3-tools) and README.md.
- STEP 7 (commit f7f9a3b) LTspice 26.1.1 under Wine 9.0 through spicelib 1.6.4, in fmcw3-sim. Run: ./run --sim python3 -m pytest tests/test_sim_smoke.py -q -> 10 passed (host and ./run --sim); ./run uv run pytest tests -q -> 33 passed, 10 skipped (sim tests skip in fmcw3-tools); fetch_sources --check ok.
- Correction of the step 2 LTspice FAIL: batch mode did work-able; the hang was LTspice's first-run dialog "Anonymously Share LTspice Usage Data" (seen with xwininfo and a screenshot under Xvfb) which blocks -b until answered. Fix: ini key CaptureAnalytics=false in drive_c/users/root/AppData/Roaming/LTspice.ini, written at image build. First run also unpacks lib.zip into AppData/Local/LTspice/lib (the ADI model library); the build does a warm-up run for that.
- Wine refuses a prefix not owned by the caller (host uid differs from build root). Fix: prefix baked at /opt/wineprefix, chmod a+rwX; tests/sim/ltspice_smoke.py makes a per-run dir of symlinks into it and sets USER=root so the baked profile is reused. No 1.7 GB copy needed.
- spicelib: set LTSPICEFOLDER/LTSPICEEXECUTABLE to the baked LTspice.exe; run under xvfb-run. Pass SimRunner.run_now a netlist PATH, not a SpiceEditor: the editor parses included vendor libs and fails on TI's "VALUE { + IF(...) }" continuation lines. LTspice also writes <tag>.op.raw beside <tag>.raw (run_now may return the op one); RawRead.get_axis fails on these files, read the first trace instead. ngspice raw needs RawRead(dialect="ngspice") and lower-case trace names.
- PASS RC low-pass in LTspice via spicelib: 41 points 10 Hz-100 kHz, worst error 7e-15 dB vs 10log10(1+(f/fc)^2), -3.010 dB at 1 kHz.
- PASS ADI model in LTspice: LT6232 is not a subckt of its own in LTspice's bundled lib, but the LT6232 symbol (lib/sym/OpAmps/LT6232.asy, description "Quad 215 MHz ... Op Amp") has SYMATTR SpiceModel LTC2.lib and Value2 LT6231, i.e. it uses the LT6231 subckt in lib/sub/LTC2.lib. LT6231 non-inverting gain of 10 on +/-2.5 V: 20.000 dB at 1 kHz, DC out 2.045 V for 0.2 V in. Caveat found: the model reproduces the real input range limit; on a single 5 V supply (V- = 0) a 1 V follower gives 1.27 V and the gain-of-10 test with 0.25 V in gave a railed output; it is the model (inputs near V- clamp), not Wine. LT6232 pins: 1 IN+, 2 IN-, 3 OUT, 4 VCC, 5 VEE.
- FAIL (expected) the same LT6231 in ngspice 42: "Error on line: a.x1.a1 fb in 0 0 0 0 0 0 x1.ota ... MIF-ERROR - unable to find definition of model 33.5" (LTspice A-device OTA). So ADI LTC*.lib models need LTspice.
- PASS TI PSpice model in both engines: public TI LP5907 1.8 V unencrypted model (https://www.ti.com/lit/zip/snvmap9, plain text, downloads without login with a normal User-Agent; the "unencrypted" PSpice models on the LP5907 page are plain). 3.6 V ramp in 100 us, 180 ohm load, 1 uF in/out: Vout(2 ms) 1.8001 V in LTspice and in ngspice-42 with .options ngbehavior=psa; max difference between the engines at 6 times from 50 us to 2 ms is 0.0010 V. So TI PSpice models run in LTspice and (when unencrypted) in ngspice.
- PASS mixed circuit in LTspice: TI LP5907 PSpice model feeding an ADI LT6231 follower (+/-3.3 V rails) in one netlist: LDO out 1.8001 V, buffer out 1.8001 V. On +/-2.5 V rails the follower gives 1.70 V (input range clamp), another reminder of the LT6231 input range. Verdict input: LTspice is the one engine that runs both ADI LTC models and TI PSpice models; use it for mixed ADI+TI circuits.
- FAIL (expected) TI LMR51420XF model (https://www.ti.com/lit/zip/slum825, 295 KB, direct download): the .LIB is TI-encrypted ("**$ENCRYPTED_LIB", Cadence $CDNENCSTART_ADV2 blocks). LTspice: "Z:\...\LMR51420XF.lib(942): Expected device instantiation or directive here." followed by the encrypted hex lines and "$CDNENCFINISH_ADV2". ngspice: encrypted lines reported as "missing tokens Line no. 1077 ...". LMR51420 therefore needs a hand-built averaged buck model in either engine. The LP5907 page also lists encrypted variants; pick the "Unencrypted" ones. LP5907 has only fixed-voltage models per option (1.2 to 4.5 V). LD3920 not looked for (the product name in the plan may be LD39200: ti.com/product/LD39200 returned 404, ST part?).
- Manifest: datasheets/manifest.yaml now has ti-lp5907-1p8-pspice and ti-lmr51420xf-pspice (direct, commit no, files under datasheets/files/ti/, sha256 recorded). Installer is deleted at build and never committed; the image is about 7 GB.
Verify: Verify passed: ./run --sim pytest tests/test_sim_smoke.py (sim tests run in fmcw3-sim, incl. LTspice via spicelib), ./run uv run pytest tests (36 passed, 10 sim skipped outside the sim image), fetch_sources --check ok
Independent review: Independent review: Acceptance met. Fixed: two vendor-model ids moved out of References (no verified items), test added. Remaining notes: plan commit 5c230bf (steps 5-11) was approved by the user in session on 2026-11-20 ('let's try what you recommended... spicelib'), recorded in its commit message and the reject reason; 5195480 carries fnd-01 carry-overs, disclosed in 2b979c8.

Accepted by user: 2026-11-20
