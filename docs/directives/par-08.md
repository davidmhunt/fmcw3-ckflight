# par-08: Simulation models for every part the planned analyses need
Status: approved
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
