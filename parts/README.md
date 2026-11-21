# parts/

Grouped BOM from the schematic, checked against DigiKey and the JLCPCB parts library for N
boards. A read, not a fix: nothing is ordered and no substitute is chosen (par-03 does that).

## How it works

`./run parts/bom.py --boards 5` does the whole job:

1. Exports every symbol headless with `kicad-cli sch export bom` (nothing under `kicad/` is
   written) and merges `parts/decisions.csv` (columns `ref` plus any of `MPN`, `Manufacturer`,
   `LCSC`, `DigiKey PN`, `DNP`, and the spec fields `Tolerance`, `Voltage`, `Dielectric`) into
   empty fields. A schematic field always wins. The spec fields split groups and narrow the
   DigiKey parametric search for generic passives; unset, only value and package are searched.
2. Groups by value, footprint and the part-number fields, and gives each group a class:
   `mpn` (an MPN, LCSC or DigiKey number is known), `generic` (a C, R, L or FB defined by value
   and package), `dnp` (not fitted), `nopart` (no part number and not a generic passive).
3. Looks every line up on JLCPCB (`check_jlc.py`, a local copy of the parts database) and on
   DigiKey (`check_digikey.py`, the Product Information API) for `qty x boards + spares`.
4. Writes one verdict per line and the JLCPCB-format BOM and CPL.

Options: `--targets NAME` (target set giving `board_quantity`, default `default`), `--boards N`
(overrides it), `--spares N` (extra parts per line), `--offline` (caches only, no network),
`--check` (exit 1 when a placed part has no MPN, generic passives included; only vias, pads,
mounting holes, the printed coupler and not-fitted lines do not count).

## Files

| File | What |
|------|------|
| `bom.py` | The command above. |
| `check_digikey.py`, `check_jlc.py` | The two sources: importable, each with a quick CLI (`--boards`, `--spares`, `--limit`; `check_jlc.py` also `--refresh`, `--offline`). |
| `out/bom.csv` | Grouped BOM: `class, refs, qty, value, footprint, MPN, Manufacturer, LCSC, DigiKey PN`. |
| `out/availability.csv` | One row per group, both sources side by side (columns below). |
| `out/jlc/bom.csv`, `out/jlc/cpl.csv` | JLCPCB BOM (`Comment, Designator, Footprint, LCSC Part #`) and CPL for the lines JLC places (assemble, consigned, unresolved with a blank LCSC). CPL coordinates are KiCad's board frame; JLC's per-package rotation corrections are not applied. |
| `cache/` | Gitignored: the JLCPCB database (about 830 MB unpacked) and DigiKey answers (no credentials in them). |
| `legacy/` | Superseded upstream-era files (below). |
| `manufacturing_check.md` | Facts-only snapshot of `production/` on `main`: gerber and CPL completeness, LCSC coverage. Still true; kept in place. |

`legacy/`: `parts.csv` (84-group BOM built from `production/bom.csv`), `availability.csv` (old
DigiKey run) and `fields_to_apply.csv` (per-ref spec-only fields) are replaced by `out/bom.csv`
and `out/availability.csv`. `bom.py` compares its refs with `legacy/parts.csv`: the same 370 refs,
83 groups against 84. The old DigiKey lookups for U8, U10 and U33 are the starting point for
par-03's decisions.

## Columns of `out/availability.csv`

- `verdict`, `reason`: one of `JLC assemble` (in stock at JLC for the quantity, exact or
  same-package match), `consign from DigiKey` (not at JLC, DigiKey has stock; JLC assembles
  consigned parts), `hand-solder` (same, through-hole line), `unresolved` (no part number, no
  stock, or only a near match), `not fitted` (DNP), `no part` (via, pad, hole, coupler).
- `class, refs, qty, need, value, footprint, MPN, Manufacturer, LCSC, DigiKey PN`: the line;
  `need = qty x boards + spares`.
- `jlc_*`: `status` (Available, Low stock, Out of stock, No-result, n/a), `lcsc`, `library`
  (Basic, Preferred, Extended; Extended adds a per-part setup fee at JLC), `stock`, `unit_price`
  at `price_qty`, `mpn`, `mfr`, `package`, `match`, `url`, `query` (what was searched).
- `dk_*`: `status` (Active, Low stock, NFND, Obsolete, No-result, Suggested, No-match, n/a;
  Not-checked and Not-cached offline), `lifecycle`, `stock`, `unit_price` at `price_qty`,
  `lead_weeks`, `datasheet`, `url`, `mpn`, `mfr`, `pn`, `match` (`exact` or `parametric`),
  `suggested_mpn`, `query`.

## Why the plugin database, not jlcsearch

`check_jlc.py` reads the parts database that the `kicad-jlcpcb-tools` plugin publishes
(`bouni.github.io/kicad-jlcpcb-tools`: SQLite FTS5, 821k parts, about 186 MB zipped and 831 MB
unpacked). It needs no key, gives the same answer on every run, works offline after one
download, and carries stock, Basic/Preferred/Extended, price breaks, MPN and package. The
`jlcsearch.tscircuit.com` API was rejected as the primary source: searching the exact MPN
GRM155R71C104KA88D returned no rows, stock was null for C71629, it has no manufacturer field,
and it is a live third-party service, so a run is not repeatable. It is not a fallback.

The plugin itself on KiCad 10 (for GUI use): release 2026.04.03 declares `kicad_version` 6.0
with no `kicad_version_max` in its PCM metadata, so the Plugin and Content Manager permits it
on 10.0.5. It has not been installed or run in the KiCad 10 GUI here, so GUI use is untested.
`bom.py` does not need the plugin, only its database file.

## Match confidence

`jlc_match` says how far to trust the JLC hit:

- `exact`: the part's MPN (compared ignoring case, spaces and dashes) or LCSC number equals the
  one on the line. Safe to use.
- `package`: a generic passive with the same value and package. Tolerance, voltage and
  dielectric are not compared; read the description before using it.
- `review`: a near hit for a person to check: an MPN that only starts with the line's MPN (the
  ordering suffix differs), or a part number typed into the Value field. Never counted as
  `JLC assemble`; the line stays `unresolved` unless DigiKey has the part.
- empty: nothing found.

`dk_match` is `exact` (MPN or DigiKey number equal) or `parametric` (a generic passive: the
best Active in-spec search hit, offered as `dk_suggested_mpn`; the value and package are
matched, an unspecified tolerance, voltage or dielectric is not).

## How to add keys

DigiKey needs an API client: copy `.env.example` to `.env` at the repo root and fill in
`DIGIKEY_CLIENT_ID` and `DIGIKEY_CLIENT_SECRET` (setup: `docs/setup.md`). `.env` is gitignored;
the tools read it at run time and never print or log the keys, and `DIGIKEY_*` environment
variables override it. Without keys `bom.py` still runs: DigiKey columns come from cached
answers or read `Not-cached`. JLCPCB needs no key; the first run without `--offline` downloads
the database (about 190 MB) into `parts/cache/jlcpcb/`, `--refresh` on `check_jlc.py` fetches
it again.

To give a line a part number, add the `MPN`, `Manufacturer`, `LCSC` or `DigiKey PN` field to
the symbol (par-04), or a row in `parts/decisions.csv` until then.
