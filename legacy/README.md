# legacy/

Upstream (`ckflight/FMCW3-Kicad`) exports and old-format files kept for reference only.
Nothing in `kicad/` reads them and none is used to build or check the board. They are
superseded by the KiCad 10 project in `kicad/` (see `docs/surveys/upstream-survey.md`,
"Legacy files" and "Safe to delete").

| file | what it is |
|---|---|
| `fmcw3.sch` | 2023 KiCad 5 root schematic sheet |
| `fmcw3.net` | KiCad netlist export of an older state; regenerable from `kicad/` |
| `fmcw3.xml` | 2024 XML netlist of an older iteration |
| `fmcw3.csv` | 2026-05-24 BOM export with DNP lines; superseded by `parts/parts.csv` |
| `fmcw3-cache.lib` | KiCad 5 schematic symbol cache (42 retired symbols) |
| `fmcw3-rescue.lib` | KiCad 5 rescue library (13 retired symbols) |
| `fmcw3.pdf` | upstream schematic plot of an older board state |
| `fmcw3*.plt` | upstream HPGL plots of the root and sheet schematics (older state) |

Kept elsewhere on purpose: `libs/` (moves to `kicad/libs/`) stays as the part-ideas
reference until goal `parts` is done (fnd-01 decision, 2026-11-19). `production/` is the
as-ordered fab package and is untouched.
