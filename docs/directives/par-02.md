# par-02: Datasheets and vendor models for the critical parts, through the sources pipeline
Status: done
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_sources.py -q && ./run tools/fetch_sources.py --check
Hardware: none

## Goal
`./run tools/fetch_sources.py` gives every collaborator the same datasheet revisions and vendor
models for the critical parts, without committing them. It holds when every critical part has a
`datasheets/manifest.yaml` entry whose file downloads (or is a listed user-fetch) and matches its
recorded SHA-256. (Amended 2026-11-21 at the user's request: foundation already built the
pipeline, `datasheets/manifest.yaml` plus `tools/fetch_sources.py`, so this directive fills it
instead of adding a second manifest and script.)

## Steps
1. Add `datasheets/manifest.yaml` entries (kind `datasheet`) for: the ten critical parts of the
   review plan (ADF4158, HMC431LP4, TQP5525, SKY65404, TRF37A73, ADL5802, 5400BL15B0050, LT6232,
   LTC2292, XC7A35T/100T including the FTG256 package pinout file), the regulators (LMR51420,
   LP5907; the ST LD39200 entry exists), the reference oscillator and clock buffer, FT2232H, the
   flash, the attenuator pads and the ferrite beads. Take refdes and part names from the
   schematic BOM export. Use the manufacturer's URL, not a distributor mirror, where one exists;
   if the manufacturer's host will not answer, a web.archive.org capture of that URL is allowed
   and said so in the title. Put the refdes and the revision or date in `title`.
2. Confirm U22-U24 (the same "LD3920" symbol as U25) against the `st-ld39200-datasheet` file:
   value, footprint and pin use. Record the result in the entry's title or a comment.
3. Add vendor simulation inputs where vendors publish them (S-parameter files for the RF parts,
   SPICE models named in `docs/analysis-tools.md`) as kind `vendor-model` entries in the same
   manifest. Models already listed stay as they are.
4. `tools/fetch_sources.py --add URL --id ID --kind KIND --title TEXT --file PATH`: downloads
   the URL, computes the hash and appends an entry with `licence` and `commit: no` filled from
   flags. Tests in `tests/test_sources.py` with a fake opener: good add, duplicate id refused,
   dead link reported. Update `MANUAL.md` section 8 and `datasheets/README.md`.
5. Things the user fetches by hand (added 2026-11-21 at the user's request). A `direct` download
   that fails (dead link, blocked host, login wall) does not stop the run and is not dropped:
   - `fetch_sources.py` keeps going, prints the failure, and records it on the entry
     (`fetch_error:` with the error text and date); `--check` lists such an entry, and any
     form or login entry without a file, as `PENDING`, not failed, until a hash is pinned;
   - every run writes `docs/user-fetch.md` (committed, regenerated): one row per pending item
     across all four manifests, with what it is, the link, the exact path to save it at, why it
     was not fetched, and the command to run afterwards (`./run tools/fetch_sources.py --record`);
   - tests with a fake opener: a failing download becomes a pending row, a saved file plus
     `--record` removes it.

   Document this as "Things you fetch by hand" in `MANUAL.md` section 8 and in
   `datasheets/README.md`.
6. Run `./run tools/fetch_sources.py --record` so every new entry that downloaded has its hash;
   leave the rest in `docs/user-fetch.md` for the user.

## Rules
- Never commit a vendor PDF or model unless its licence allows it (`commit: no` by default).
- An entry counts only once its file was downloaded and its hash recorded, never from memory.

## Out of scope
- Datasheets for generic passives.
- Reading the datasheets for part decisions (par-03).

## Allowed commands
- `./run *`

## Log

### 2026-11-21
Commits:
- 1af6e4a par-02 step 1: datasheet manifest entries for the critical parts, regulators, clocking, FT2232H, flash, pads, ferrites
- 8a1853f par-02 step 2: U22-U24 LD3920 confirmed against the LD39200 datasheet (DFN8 ADJ, pins, dividers); title and comments in manifest
- 9303a8d par-02 step 3: vendor-model entries (TRF37A73 S-parameters downloaded; balun, TQP5525, SKY65404, ADL5802 S-parameters as user-fetch); hashes recorded for step 1 downloads
- 74df18f par-02 step 4: fetch_sources.py --add downloads, hashes and appends a manifest entry; tests, MANUAL section 8, datasheets README
- 2d8921d par-02 step 5: failed downloads become pending user-fetch items (fetch_error, PENDING, docs/user-fetch.md); tests, MANUAL section 8, datasheets README
- 39c7ec1 par-02 review fixes: fetch_all/--record patch the manifest text so comments survive; restore the LD39200 U22-U24 check and manifest header; add ferrite-bead vendor-model user-fetch entries (Murata, TDK)
Notes:
- step 6: `./run tools/fetch_sources.py --record` ran; no tracked files changed (all downloaded entries already had hashes). `--check` ends "sources check: ok".
- 9 entries remain PENDING for the user, listed in docs/user-fetch.md: TQP5525 datasheet and S-parameters, PAT1220 datasheet, BLM18PG181SN1D, MPZ2012S101AT000, Johanson balun s2p, SKY65404-31 s2p, ADL5802 S-parameters, PSpice for TI installer.
Verify: Verify passed: ./run uv run pytest tests/test_sources.py -q && ./run tools/fetch_sources.py --check
Independent review: gaps fixed in second review: 1. datasheets/manifest.yaml:2-11 (st-ld39200-datasheet entry); root cause tools/fetch_sources.py:225: Step 2 asks for the U22-U24 check of value, footprint and pin use to be recorded in the entry's title or a comment. Commit 8a1853f wrote the full result as a YAML comment: the footprint against Table 9, the pin map against Table 2, the ADJ divider values for U22, U23 and U24, PG wiring, and the note that 'LD3920' is not an orderable code, which is meant for par-03. In the next par-02 commit (9303a8d, step 3), 'fetch_sources.py --record' rewrote the manifest with 'yaml.safe_dump({'entries': entries})'. That deleted every comment, including this one and the manifest's header block. What survives in HEAD is only the title: 'U22, U23, U24 ''LD3920'' = LD39200DPUR, DFN8 4x4, ADJ'. The pin-use confirmation, the footprint details and the par-03 note are no longer in the deliverable. The same rewrite path also runs whenever step 5's new 'fetch_error' handling sets 'changed = True'. So any normal fetch or '--record' run deletes comments in all three manifests, including the comment block in docs/references/manifest.yaml that docs/analysis-tools.md:225 points to. 'add_entry' was written to keep comments, but 'fetch_all' throws them away on the next run. (evidence: 'git show 9303a8d -- datasheets/manifest.yaml' shows the removed lines: the 4-line header ('# Datasheets and vendor models. Read by tools/fetch_sources.py ...') and the 8-line '# par-02 step 2, checked against this file (Rev 3, Sept 2018): ... Pins match Table 2: IN 7+8 tied, OUT 1+2 tied, ADJ 3 ... Gap: value ''LD3920'' is not an orderable code ...' comment. tools/fetch_sources.py:224-225: 'if changed: mpath.write_text(yaml.safe_dump({'entries': entries}, sort_keys=False, width=100))'. The current datasheets/manifest.yaml has no comments at all. No test covers keeping comments through fetch_all or --record.) 2. datasheets/manifest.yaml (vendor-model entries, lines 225-292): Step 3 asks for vendor-model entries for the SPICE models named in docs/analysis-tools.md, where vendors publish them. That file names ferrite-bead vendor models twice: line 56 (Murata, TDK, Wurth) and line 153 ('Ferrite-bead netlists for the fitted beads | Murata SimSurfing, TDK SEAT ...', needed for sim-01). No vendor-model entry was added for the BLM18PG181SN1D or MPZ2012S101AT000 models, not even as a form/user-fetch item. Only the LP5907 and LMR51420 entries, which already existed, and the five S-parameter entries are present. The commit message for step 3 does not explain why these were left out. (evidence: The vendor-model ids in HEAD are ti-lp5907-1p8-pspice, ti-lmr51420xf-pspice (both from before par-02), ti-trf37a73-sparams, johanson-5400bl15b050-sparams, qorvo-tqp5525-sparams, skyworks-sky65404-sparams and adi-adl5802-sparams. There is no murata or tdk vendor-model entry. docs/user-fetch.md has no row for a ferrite-bead model.)
