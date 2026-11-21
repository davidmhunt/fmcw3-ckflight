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

See section 8 of `MANUAL.md`.
