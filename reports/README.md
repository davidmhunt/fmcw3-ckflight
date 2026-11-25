# reports/

Built report PDFs, `.pptx` decks and deck PDFs for the analyses in `analysis/`. ERC/DRC output
lives in `checks/`, not here. Each analysis `NN_name` builds `NN_name.pdf` (the write-up),
`NN_name.pptx` (the deck) and `NN_name_ppt.pdf` (the deck exported by LibreOffice Impress
headless, in the `fmcw3-tools` image).

## Current parts reports

- `13_parts_final`: the final parts record for both boards (`parts/final_parts.csv`).
- `14_*`: the par-14 parts report (not built until par-14 lands).

## Archive

`reports/archive/` holds the older analyses, whose `deck.yaml` has `archive: true`:
`00_baseline`, `01_parts`, `02_pa`, `03_sourcing`, `11_board_1rx`, `12_rail_loads`. Their sources
stay in `analysis/`; `build_all.py` and `build_report.py` write them to `reports/archive/`.

## Built locally, never committed

`reports/*.pdf` and `reports/*.pptx` are gitignored (so is `NN_name_ppt.pdf`, and LibreOffice
`.~lock*` files). Git LFS was tried and refused (`origin` is
a public fork, and GitHub rejects LFS uploads to it), and binaries do not belong in normal git
history, so the sources are committed and the outputs are rebuilt on demand.

Rebuild everything (every `analysis/NN_*/` with a `deck.yaml`):

```
./run tools/build_all.py              # build all into reports/
./run tools/build_all.py --check      # validate all, build nothing
./run tools/build_report.py analysis/NN_name [--targets NAME] [--check]   # one analysis
```

Only this README is tracked in this folder.
