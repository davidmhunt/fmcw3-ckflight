# fmcw3-ckflight manufacturability snapshot (`production/` on `main` @ cf34c04)

Facts only — no fixes applied, no parts ordered. Feeds hw-19's
quickest-to-build comparison.

## Gerbers (`production/fmcw3.zip`)

20 files, consistent with a 6-layer board with one soldermask/silkscreen/
paste layer per side and a separate NPTH/PTH drill pair:

| Layer | File |
|---|---|
| Top copper | `fmcw3-L1_SIG.gtl` |
| Inner 2 | `fmcw3-L2_GND.g1` |
| Inner 3 | `fmcw3-L3_PWR.g2` |
| Inner 4 | `fmcw3-L4_PWR_SIG.g3` |
| Inner 5 | `fmcw3-L5_GND.g4` |
| Bottom copper | `fmcw3-L6_SIG.gbl` |
| Masks | `fmcw3-F_Mask.gts`, `fmcw3-B_Mask.gbs` |
| Silkscreens | `fmcw3-F_Silkscreen.gto`, `fmcw3-B_Silkscreen.gbo` |
| Paste | `fmcw3-F_Paste.gtp`, `fmcw3-B_Paste.gbp` |
| Outline | `fmcw3-Edge_Cuts.gm1` |
| Courtyard / margin (extra, non-fab) | `fmcw3-F_Courtyard.gbr`, `fmcw3-B_Courtyard.gbr`, `fmcw3-Margin.gbr` |
| Drill | `fmcw3-PTH.drl`, `fmcw3-NPTH.drl` + drill maps |

All 6 copper layers present, both mask/silk/paste sides, edge cuts, and a
PTH/NPTH drill pair with maps — the gerber set looks complete for a bare
6-layer fab quote (JLCPCB or otherwise). `fabrication-toolkit-options.json`
(`ALL_ACTIVE_LAYERS: true`, `EXCLUDE DNP: false`) confirms these were
produced by the KiCad Fabrication Toolkit plugin with its default JLCPCB
preset.

## CPL (`production/positions.csv`)

363 placement rows (+ header), one per physical reference matching
`production/designators.csv`'s 363-entry list — a full pick-and-place file
with no visible gaps.

## BOM (`production/bom.csv`)

- 84 BOM line groups, covering 370 reference designators (`parts/parts.csv`,
  §refs).
- **LCSC Part # column: 0 of 84 lines filled.** Every row's `LCSC Part #`
  cell is blank — none of the fast lookup checks below substitute for this;
  a JLCPCB SMT assembly quote needs a resolved LCSC part number per line
  (or "Basic/Extended" part selection done in JLC's own BOM tool), and none
  exist yet here.
- Quantities and footprints are consistent with the schematic groupings
  used to build `parts/parts.csv`.

## Bottom line

The bare-board fab inputs (gerbers, drill, CPL) look complete and
JLC-ready as exported. The assembly BOM is not: it carries footprint/value
but zero LCSC part numbers, so JLCPCB assembly cannot be quoted from
`production/bom.csv` as-is — every line would need an LCSC part chosen
first (DigiKey availability in `parts/availability.csv` is a different
distributor and doesn't map to LCSC catalog numbers). This is a gap, not a
defect in the exported files; resolving it is out of this directive's
scope (no part ordering/selection here).
