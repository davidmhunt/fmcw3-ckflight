# par-02: Datasheets and vendor models for the critical parts, through the sources pipeline
Status: approved
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
