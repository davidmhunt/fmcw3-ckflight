# parts/

Baseline availability check for `fmcw3-ckflight`, mirroring
`hardware/fmcw3/parts/` so the two boards' BOMs are comparable (hw-18, feeds
hw-19). No parts ordered, no substitutions chosen — a read, not a fix.

| File | What |
|------|------|
| `parts.csv` | One row per `production/bom.csv` group (84 groups, 370 refs). Built from the pinned `production/bom.csv` on `main`. `kind` = `mpn` (exact part, looked up), `generic` (spec only, no MPN), `dnp`, `nopart` (via, test point, mounting hole, pin header, printed coupler). Same columns as `hardware/fmcw3/parts/parts.csv`. |
| `check_digikey.py` | Copied from `hardware/fmcw3/parts/check_digikey.py` (not forked/diverged). Looks up every `kind=mpn` row on DigiKey and writes `availability.csv` + `fields_to_apply.csv`. `python parts/check_digikey.py [--boards N]` from this submodule's root. |
| `availability.csv` | Last run's output. `status` is never blank: Active / NFND / No-result / needs-David / generic-spec-only / DNP / no-part. HMC431LP4 (U10), FT2232H (U33), LTC2292 (U8) resolved per fmcw3's hw-02 suffix precedent (`HMC431LP4ETR`, `FT2232HL-REEL`, and LTC2292's C/I temp-grade left `needs-David`). |
| `fields_to_apply.csv` | Written by `check_digikey.py`; not applied to the schematic in this directive (no schematic edits in scope). |
| `manufacturing_check.md` | Facts-only snapshot of `production/` on `main`: gerber completeness, CPL completeness, LCSC part-number coverage in the BOM. |

`check_digikey.py` reads credentials from `.digikey.env` at this submodule's
root (same relative location as the fmcw3 fork). That file is gitignored;
never commit it.
