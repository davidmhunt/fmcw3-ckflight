# reports/

Built report PDFs and `.pptx` decks for the analyses in `analysis/`. ERC/DRC output lives in
`checks/`, not here.

## Built locally, never committed

`reports/*.pdf` and `reports/*.pptx` are gitignored. Git LFS was tried and refused (`origin` is
a public fork, and GitHub rejects LFS uploads to it), and binaries do not belong in normal git
history, so the sources are committed and the outputs are rebuilt on demand.

Rebuild everything (every `analysis/NN_*/` with a `deck.yaml`):

```
./run tools/build_all.py              # build all into reports/
./run tools/build_all.py --check      # validate all, build nothing
./run tools/build_report.py analysis/NN_name [--targets NAME] [--check]   # one analysis
```

Only this README is tracked in this folder.
