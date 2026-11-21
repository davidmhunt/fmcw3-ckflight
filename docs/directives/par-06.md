# par-06: Datasheets through DigiKey for every BOM part, with a DigiKey link for what still fails
Status: done
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_sources.py -q && ./run tools/fetch_sources.py --check
Hardware: none

## Goal
Every BOM part with an MPN has a datasheet that `./run tools/fetch_sources.py` fetches without
the user, taken from the datasheet link the DigiKey Product Information API returns for that
part, and every part it still cannot fetch has a row in `docs/user-fetch.md` that links the
part's DigiKey product page. It holds when the tests pass and `--check` reports every entry
either fetched with its hash or PENDING. (Added 2026-11-21 at the user's request: DigiKey hosts
most of these datasheets, and the manufacturer sites block scripted downloads. This replaces
par-02's rule "manufacturer URL, not a distributor mirror" for the entries it touches.)

## Steps
1. Manifest field `digikey: <MPN>` on a datasheet entry. `fetch_sources.py`, for an entry
   that has it and no file yet, asks the DigiKey Product Information API for that MPN through
   `parts/check_digikey.py`'s client (same `.env` keys, same gitignored cache under
   `parts/cache/digikey/`). It downloads the returned datasheet URL (a `//` URL becomes
   `https://`), and checks the file is a PDF before keeping it. Order: the DigiKey datasheet
   URL, then the entry's own `url`. When both fail, the entry is pending as in par-02 step 5,
   and its `docs/user-fetch.md` row links the DigiKey product page from the API (the
   `ProductUrl`), and says why the download failed.
2. `fetch_sources.py --from-bom`: adds one entry (kind `datasheet`, `digikey: <MPN>`,
   `commit: no`, title with the refdes) for every unique MPN in `parts/out/availability.csv`
   and `parts/decisions.csv` that no manifest entry covers yet. This includes generic passives,
   because the user asked for all parts. Files go to `datasheets/files/digikey/<mpn>.pdf`.
   Running it a second time adds nothing. Existing entries still pending (TQP5525 S-parameters,
   TDK MPZ2012S101AT000, Johanson balun and the others in `docs/user-fetch.md`) get the
   `digikey:` field, so they are retried through DigiKey. Entries that already have a file and a
   hash keep their URL.
3. Tests in `tests/test_sources.py` with a fake opener and a fake DigiKey client:
   - the DigiKey URL is downloaded and its hash recorded;
   - a `//` URL is fixed;
   - an HTML page in place of a PDF is refused;
   - with no API result, the entry falls back to its `url`;
   - when both fail, the entry becomes a pending row that carries the DigiKey product link;
   - `--from-bom` runs twice without adding duplicates;
   - the API keys never appear in output or in the manifest.
4. Run `./run tools/fetch_sources.py --from-bom`, then a normal run, then `--record`. In the Log,
   give the number of datasheets fetched through DigiKey, through the maker's URL, and still
   pending (with their refdes).
5. Update `MANUAL.md` section 8 ("Things you fetch by hand": the DigiKey link) and
   `datasheets/README.md`.

## Rules
- Never commit a downloaded datasheet: `datasheets/files/` stays gitignored and new entries are
  `commit: no`.
- Use the DigiKey API and the datasheet links it returns only. Never scrape digikey.com
  pages and never log in.
- Never print or commit the `.env` keys.

## Out of scope
- S-parameter and SPICE models (DigiKey rarely hosts them): those rows only gain the DigiKey
  product link.
- Changing any part choice, or filling the `datasheet_id` cells of `parts/decisions.csv`
  (par-03 follow-up).

## Allowed commands
- `./run *`

## Log

### 2026-11-21
Commits:
- 71a3ed4 par-06 step 1: digikey: <MPN> manifest field; fetch_sources asks the DigiKey API for the datasheet URL, falls back to the entry url, checks for a PDF, and links the DigiKey product page on a pending row
- fde7827 par-06 step 2: fetch_sources --from-bom adds a pending digikey: datasheet entry for every BOM MPN no entry covers (50 added), idempotent; pending entries get digikey: (models only gain the product link)
- 5e47eab par-06 step 4: run --from-bom, a normal fetch and --record: 21 datasheets fetched through DigiKey, 0 through a maker URL, 30 still pending with their user-fetch rows
- a2fa71e par-06 step 5: MANUAL.md section 8 and datasheets/README.md describe digikey: entries, --from-bom and the DigiKey product link on pending rows
Verify: Verify passed: ./run uv run pytest tests/test_sources.py -q && ./run tools/fetch_sources.py --check
Independent review: no gaps
