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

## Things you fetch by hand

A `direct` download that fails (dead link, blocked host, login wall) does not stop
`fetch_sources.py`; it prints the failure and records `fetch_error:` (text and date) on the
entry. `--check` shows that entry, and any form or login entry without a file, as `PENDING`.
Every run regenerates `docs/user-fetch.md` with one row per pending item: what it is, the link,
the path to save it at, why it was not fetched. Save the file there, then run
`./run tools/fetch_sources.py --record`; the hash is pinned and the row goes away.

See section 8 of `MANUAL.md`.
