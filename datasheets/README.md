# datasheets/

Part datasheets and vendor simulation models, listed in `manifest.yaml` and downloaded by
`./run tools/fetch_sources.py` into `datasheets/files/`, which is gitignored (vendor files are
not redistributed unless the licence allows it; `commit: no` is the default).

- Verify: `./run tools/fetch_sources.py --check`.
- Add a file: `./run tools/fetch_sources.py --add URL --id ID --kind datasheet --title "Maker
  PART rev (refdes)" --file datasheets/files/<vendor>/<name>.pdf [--licence TEXT]`. It
  downloads, hashes and appends the entry; it refuses a duplicate id and reports a dead link
  without adding anything. Put the refdes and the revision in the title.
- Use the manufacturer's URL; a web.archive.org capture is allowed if the host will not answer,
  and the title says so.
- Through DigiKey (par-06): an entry with `digikey: <MPN>` is fetched from the datasheet link
  the DigiKey Product Information API returns for that MPN (keys from `.env`, answers cached
  under `parts/cache/digikey/`), then from its own `url`; the download must be a PDF. This
  replaces par-02's "manufacturer URL, not a distributor mirror" for those entries, because the
  maker sites block scripted downloads. Only the API and its returned links are used; digikey.com
  pages are never scraped.
- `./run tools/fetch_sources.py --from-bom` adds a `commit: no` entry
  (`datasheets/files/digikey/<mpn>.pdf`) for every BOM MPN without one; a second run adds
  nothing. Entries that still fail become pending, and their row in `docs/user-fetch.md` links
  the DigiKey product page.

## Things you fetch by hand

A `direct` download that fails (dead link, blocked host, login wall) does not stop
`fetch_sources.py`; it prints the failure and records `fetch_error:` (text and date) on the
entry. `--check` shows that entry, and any form or login entry without a file, as `PENDING`.
Every run regenerates `docs/user-fetch.md` with one row per pending item: what it is, the link,
the path to save it at, why it was not fetched (with the DigiKey product link when the API gave one). Save the file there, then run
`./run tools/fetch_sources.py --record`; the hash is pinned and the row goes away.

See section 8 of `MANUAL.md`.
