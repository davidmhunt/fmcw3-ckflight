# analysis/

One folder per analysis, named `NN_name` (for example `00_baseline`), holding its inputs, scripts
and the report built from them. `tools/build_report.py` turns a folder into `reports/NN_name.pdf`
and `reports/NN_name.pptx`.

## Folder layout

```
analysis/NN_name/
  report.md     the full write-up (pandoc Markdown, becomes the PDF)
  deck.yaml     the slide list (becomes the .pptx)
  figures.py    regenerates every figure and table into build/
  build/        generated figures and tables (gitignored, never hand-edited)
  <data files>  optional inputs the script reads (CSV, JSON, YAML)
```

No figure or table is made by hand: if it appears in the report or deck, `figures.py` wrote it
into `build/`.

## report.md

Every report starts with these five sections, in this order:

1. Question: what the analysis answers, in one or two sentences.
2. Inputs and assumptions: the target set name (`analysis/targets/<name>.yaml`) and its values as
   used, plus any other input and its source. Values still marked `assumed` are said to be so.
3. Method: how the answer is computed, short enough to be repeated by hand.
4. Findings: results, referencing figures and tables from `build/`.
5. Open decisions for the user: each decision, the options, the evidence and a recommendation.
   Design decisions are the user's; the report prepares them, it does not make them.

## deck.yaml

A list of slides under `slides:`. Each slide has:

- `title`: slide title.
- `layout`: one of `title`, `bullet`, `figure`, `table`, `decisions`.
- `bullets`: list of short strings (bullet and decisions layouts).
- `figure` or `table`: file name in `build/` (figure and table layouts).
- `note`: speaker note.

Every referenced file must exist after `figures.py` runs; the `--check` flag of the build tool
fails on a missing figure, an unresolved reference, or text that overflows its text box.

## figures.py

Run by the build tool with the analysis folder as the working directory's target. It reads the
data files and the chosen target set (through `tools/targets.py`) and writes every figure (PNG)
and table (CSV) into `build/`. It must be re-runnable and deterministic.
