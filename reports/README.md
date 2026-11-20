# reports/

Built report PDFs and `.pptx` decks for the analyses in `analysis/`. ERC/DRC output lives in
`checks/`, not here.

## Storage: normal git files, not LFS

Git LFS was tried and refused: `origin` is a public fork, and GitHub rejects LFS uploads to it
("can not upload new objects to public fork"). So there is no LFS rule in `.gitattributes`, and
built `.pdf` and `.pptx` files are committed as normal git files. Rebuild with
`./run tools/build_report.py analysis/NN_name`. If the repo moves to a non-fork remote, LFS can
be enabled with `git lfs track "reports/*.pdf" "reports/*.pptx"` and `git lfs migrate`.
