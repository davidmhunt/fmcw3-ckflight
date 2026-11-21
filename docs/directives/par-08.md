# par-08: Simulation models for every part the planned analyses need
Status: done
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_models.py -q && ./run tools/check_models.py && ./run tools/fetch_sources.py --check
Hardware: none

## Goal
When the parts goal lands, every part model a planned analysis needs is either on file with a
pinned hash or a listed user-fetch row. This covers S-parameters, SPICE or PSpice models, and
ferrite-bead models. It holds when `tools/check_models.py` finds no needed model missing from
the manifests. (Added 2026-11-21 at the user's request: the parts list must carry everything
the later analyses and the redesign need.)

## Steps
1. `parts/models_needed.csv` (committed): one row per needed model. Columns:
   - refdes and MPN;
   - model kind (`s2p`, `snp`, `spice`, `pspice`, `bead`);
   - the analysis or directive that needs it (each sim-*, rf-* and lay-* directive, and
     `docs/analysis-tools.md`);
   - why that analysis needs it;
   - the manifest id that satisfies it.
   The MPNs come from `parts/decisions.csv`. The replacement PA from par-07 is one row; while
   par-07 is undecided, the row carries the MPN `TBD-par-07`. Every option still open in a
   user choice that an analysis must check before the choice is final also gets rows. For example,
   FB4's option BLM18KG221SN1D needs its Murata S-parameter and SPICE models for sim-01's 5 V
   branch, and the QPA9501 is already on file. (Amended 2026-11-21 at the user's request.)
2. Add a `vendor-model` entry to `datasheets/manifest.yaml` for every row that has none yet:
   - use the vendor's model page, or the DigiKey product page from par-06 as the user-fetch
     link;
   - a model the vendor does not publish is recorded as `none published`, with the page checked
     and the date, and the row names the stand-in the analysis will use (for example, a
     datasheet-derived model).
3. `tools/check_models.py`: exits non-zero when a needed-model row has no manifest entry, or
   names an id that does not exist. It also fails while a row has the MPN `TBD-par-07` and
   par-07 is done, so the PA row has to be filled once the PA is chosen. It prints a summary:
   on file, user-fetch, none published. Tests in `tests/test_models.py` on fixture files.
4. Datasheets DigiKey does not carry (par-06 left 25 pending, mostly FH and Uniroyal passives).
   Use the JLC database's `Datasheet` link (LCSC) as the next source. A test on 2026-11-21
   returned an HTML page for one of these links, so a PDF has to be found behind it; if none
   can be found, the user-fetch row links the LCSC page.
   Also remove duplicate entries for parts an existing entry already covers (par-06 added
   `dk-ft2232hl-reel` next to `ftdi-ft2232h-datasheet`).
5. Run `./run tools/fetch_sources.py` and then `--record`. The models still pending go to
   `docs/user-fetch.md`. Add `tools/check_models.py` to `MANUAL.md` section 8 and
   `datasheets/README.md`.

## Rules
- Never commit a vendor model unless its licence allows it (`commit: no` by default).
- A model counts only once its file is downloaded and hashed, or it is listed as a user-fetch;
  never from memory.

## Out of scope
- Running any simulation, or checking model accuracy (the sim goals).
- Choosing parts.

## Allowed commands
- `./run *`

## Log

### 2026-11-21
Commits:
- 44eb9b5 parts: files fetched through the browser (TDK and Murata bead S-parameters and SPICE, Johanson balun s3p and current datasheet, MLG1005, MPZ2012, QPA9501); balun code confirmed; par-08 approved by the user; goal rule: JLC-stocked parts first
- 6d50d62 parts: pin hashes for the LCSC passive datasheets, the AWL9924 datasheet and the QPA9501 S-parameters (fetched through the browser)
- 9eeb3b5 parts: FB4 bead choice (BLM18KG221SN1D option); docs/board-changes.md change record and goal rule; par-08 also covers models of open-choice options
- e54549d par-08 step 1: parts/models_needed.csv, one row per model the planned analyses need (43 rows; FB4 option B, inductor options, QPA9501 included)
- aa3fb16 par-08 step 2: vendor-model manifest entries for the 30 models_needed ids that had none (all user-fetch rows with stand-ins named; TI LP2985 and TLV172 model zips found on the TI pages)
- 01a718c par-08 step 3: tools/check_models.py and tests (rows need a manifest entry; TBD-par-07 fails once par-07 is done); manual and datasheets README
- 491326f par-08 step 4: drop dk-ft2232hl-reel and dk-usb4105-gf-a (covered by ftdi-ft2232h-datasheet and gct-usb4105-datasheet, titles now name the MPN); fetch run refreshes user-fetch.md
- dacdb96 par-08: answer the step 2 model questions: LP5907 3.0 V model (SNVMAP8) added and used for U20/U39; LMR51420YFDDCR has no published model (TI page checked 2026-11-21), XF stand-in recorded; stale 'step 2' wording removed
Verify: Verify passed: ./run uv run pytest tests/test_models.py -q && ./run tools/check_models.py && ./run tools/fetch_sources.py --check
Independent review: gaps fixed in second review: 1. parts/models_needed.csv:8-9 (U20/U39 LP5907MFX-3.0 row and U17-U19 LMR51420YFDDCR row); datasheets/manifest.yaml entries ti-lp5907-1p8-pspice and ti-lmr51420xf-pspice: Two rows hand a model question to 'step 2', and step 2 never answered it. The LMR51420 row points at the XF-variant model (SLUM825) and says 'whether it covers the fitted YF is read from the TI model page in step 2'. The LP5907 row uses the 1.8 V model 'as the stand-in until a 3.0 V one is found on the TI model page (step 2)'. Step 2 (aa3fb16) only added entries for ids that had none. It did not check either TI page or record the result. So the model on file for the fitted buck variant (YF) is not confirmed, and the directive's own step 2 rule was not applied: a model the vendor does not publish is recorded as 'none published' with the page checked and the date, and the row names the stand-in. This matters for sim-01, sim-02, sim-04 and sim-05, which need the fitted LMR51420 variant's switching behaviour. The Bourns (line 16) and FH (line 30) rows still say 'step 2' too, but their entries were filled in, so only their wording is out of date. (evidence: Line 9 why text: 'the file on file is the XF variant (SLUM825, TI-encrypted), so whether it covers the fitted YF is read from the TI model page in step 2'. The manifest entry ti-lmr51420xf-pspice still reads 'TI LMR51420XF PSpice transient model (SLUM825; TI-encrypted)', with no YF note or check date. ti-lp5907-1p8-pspice still reads 'TI LP5907 1.8 V unencrypted PSpice transient model (SNVMAP9)', with no note that a 3.0 V model was looked for. The diff of commit aa3fb16 touches neither entry, and its message lists only the 30 new ids.)
