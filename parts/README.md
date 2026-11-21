# parts/

Baseline availability check for `fmcw3-ckflight`, mirroring
`hardware/fmcw3/parts/` so the two boards' BOMs are comparable (hw-18, feeds
hw-19). No parts ordered, no substitutions chosen — a read, not a fix.

| File | What |
|------|------|
| `bom.py` | Grouped BOM from the schematic, then availability and the JLCPCB files: `parts/bom.py [--targets NAME] [--boards N] [--spares N] [--offline] [--check]`. Boards default to `board_quantity` of the target set. Writes `out/bom.csv`, `out/availability.csv` (JLC and DigiKey side by side, one verdict per line: JLC assemble, consign from DigiKey, hand-solder, unresolved; also not fitted and no part), `out/jlc/bom.csv` and `out/jlc/cpl.csv`. `--offline` uses the caches only; `--check` exits 1 on a placed part without an MPN (vias, pads, mounting holes and the printed coupler do not count). |
| `check_digikey.py`, `check_jlc.py` | The two sources, importable and with a quick CLI each. |
| `legacy/` | Superseded upstream-era files (see below). |
| `manufacturing_check.md` | Facts-only snapshot of `production/` on `main`: gerber completeness, CPL completeness, LCSC part-number coverage in the BOM. Still true; kept in place. |

`legacy/`: `parts.csv` (84-group BOM built from `production/bom.csv`), `availability.csv` (old
DigiKey run, status per group) and `fields_to_apply.csv` (per-ref spec-only fields) are replaced by
`out/bom.csv` and `out/availability.csv`. `bom.py` compares its refs with `legacy/parts.csv`: the
same 370 refs, 83 groups against 84. The old DigiKey lookups for U8, U10 and U33 are the starting
point for par-03's decisions.

`check_digikey.py` reads credentials from `.env` at this submodule's
root (same relative location as the fmcw3 fork). That file is gitignored;
never commit it.
