# fnd-04: Report and deck pipeline with target sets and a baseline report
Status: done
Goal: foundation
Node: any
Deliverable: code
Accept: user
Verify: ./run uv run pytest tests -q && ./run tools/build_report.py analysis/00_baseline --check
Hardware: none

## Goal
One command turns an analysis folder into a PDF report and a `.pptx` deck in `reports/`, and
every analysis reads its system targets from a named target set. It holds when
`./run tools/build_report.py analysis/00_baseline` produces both files from scripts and data in
the repo, with no hand-made figure.

## Steps
1. Convention, documented in `analysis/README.md`: each analysis is `analysis/NN_name/` with
   `writeup.md` (the full write-up; not `report.md`, which Claude Code refuses to let subagents
   write; amendment approved by the user 2026-11-20), `deck.yaml` (slide list: title, bullets, figure or table
   reference, speaker note), `figures.py` (regenerates every figure and table into `build/`,
   gitignored) and optional data files. Every report starts with: question, inputs and
   assumptions (target set name and values), method, findings, open decisions for the user.
2. `tools/build_report.py <analysis dir> [--targets NAME] [--check]`: runs `figures.py`, builds
   `reports/NN_name.pdf` from `writeup.md` with pandoc, and `reports/NN_name.pptx` from
   `deck.yaml` with python-pptx using one shared 16:9 template (`tools/deck_template.py`:
   title, bullet, figure, table and "decisions needed" layouts). `--check` fails on a missing
   figure, an unresolved reference, or text that overflows a slide's text box (estimate from
   character count and font size per layout; unit-tested).
3. Targets: `analysis/targets/default.yaml` (max range, range resolution or chirp bandwidth,
   chirp duration, sample rate, TX power, antenna gain and isolation, board quantity) with
   values marked `assumed` until the user sets them, a schema check, and
   `tools/targets.py` to load a set by name. Reports print the target set they used.
4. Git LFS: `.gitattributes` tracks `reports/*.pdf` and `reports/*.pptx`. Before committing any
   LFS object, push one small test object to `origin` on the goal branch; GitHub can refuse LFS
   uploads to a fork. If refused, commit built files as normal git files, say so in
   `reports/README.md`, and note it in `runs/fnd-04/notes.md`.
5. First real report, `analysis/00_baseline/`: the state of the board as inherited. ERC/DRC
   counts by type from `checks/` with a bar chart, what each type means and which goal handles
   it, the folder map, the roadmap. Build it and commit `reports/00_baseline.pdf` and `.pptx`.
6. Tests in `tests/`: target loading and schema errors, deck overflow check, a build of a tiny
   fixture analysis. Document the commands in `README.md` and `CLAUDE.md`.
7. Built files are not committed (amendment approved by the user 2026-11-20, because the LFS
   route in step 4 was refused). `git rm --cached` `reports/00_baseline.pdf` and `.pptx`, and
   gitignore `reports/*.pdf` and `reports/*.pptx`. Add `tools/build_all.py`, which rebuilds every
   `analysis/NN_*/` that has a `deck.yaml` into `reports/` and supports `--check`. Rewrite
   `reports/README.md` (built locally, never committed, how to rebuild) and the matching lines in
   `README.md` and `CLAUDE.md`. This replaces the commit parts of steps 4 and 5.
8. (Amendment approved by the user 2026-11-20 after reviewing the deck.)
   - Deck PDF: every build also exports the deck to `reports/NN_name_ppt.pdf` with LibreOffice
     Impress headless, added to the `fmcw3-tools` image. `build_all.py` and `--check` cover it;
     it is gitignored like the other built files. Gitignore `.~lock*` (LibreOffice lock files).
   - Targets in two groups in `analysis/targets/default.yaml`, both schema-checked:
     - `design` (required; printed first in every writeup and deck): `freq_min_ghz` and
       `freq_max_ghz` (assumed 5.725 and 5.875, the 5.8 GHz ISM band), chirp bandwidth, ADC
       sample rate, TX power, TX/RX isolation, board quantity;
     - `performance` (optional extras, printed after): max range, chirp duration, antenna gain.
   - Range resolution is derived from the bandwidth (c / 2B) and printed as derived, never set.
   - The schema check fails when the chirp bandwidth exceeds `freq_max - freq_min`.
   - Values stay `assumed` until the user sets them. Update the tests and rebuild
     `analysis/00_baseline`.

## Review
- Run `./run tools/build_all.py`, then open `reports/00_baseline.pptx` and
  `reports/00_baseline.pdf`. `git status` shows no built file. Is the deck style, level of
  detail and slide density what you want for every later analysis. Say what to change now; the
  template is reused by all later goals.
- Open `analysis/targets/default.yaml`: are these the right parameters to carry as targets.
- Open `reports/00_baseline_ppt.pdf`: the slides as a PDF. Check that the design targets are
  printed first and range resolution is shown as derived.

## Out of scope
- Any new analysis beyond summarising the existing ERC/DRC baseline.
- Online documents (Claude Docs, Google Slides).

## Allowed commands
- `./run *`
- `git lfs track *`

## Log

### 2026-11-20
Commits:
- 0c6c9bc fnd-04: analysis folder convention in analysis/README.md; ignore build/
- 25fa072 fnd-04: tools/build_report.py and shared deck template, with tests
- efd92ec fnd-04: target sets (default.yaml, schema check, tools/targets.py); reports print the set used
- c6c2652 fnd-04: LFS refused by public fork; reports stay normal git files, documented in reports/README.md
- 5450efb Plan: fnd-04 analysis source is writeup.md, not report.md (user-approved amendment); repo rule
- 558144a fnd-04: baseline report (reports/00_baseline.pdf/.pptx); analysis source is writeup.md
- dfe3a56 fnd-04: document report build and test commands in README.md and CLAUDE.md
- 934b30b fnd-04: report tables, counts and target set come from build/ and --targets, not typed by hand
Notes:
- Step 4 LFS test: tracked reports/*.pdf and reports/*.pptx, staged a 23-byte test object (oid abfaac6fb092...), ran `git lfs push origin --object-id <oid>`.
- GitHub refused: "@davidmhunt can not upload new objects to public fork davidmhunt/fmcw3-ckflight".
- Fallback taken: no LFS rules in .gitattributes (removed), test file unstaged and deleted, built reports will be committed as normal git files. Documented in reports/README.md.
- Nothing was pushed to a branch; only the LFS batch upload was attempted.
Verify: Verify passed: ./run uv run pytest tests -q && ./run tools/build_report.py analysis/00_baseline --check
Independent review: not recorded
Blocked: review gaps remain: commit 221b9d15224d12989546f63041eba5830f351439 (docs/surveys/upstream-survey.md): 'friday commits fnd-04' still lists this commit as untracked: it has no 'Directive:' trailer and touches more than plan docs.; commit e88157fffb023671f97b40eafb599110544f9fa5 (.claude/friday.json): 'friday commits fnd-04' still lists this commit as untracked: it has no 'Directive:' trailer and touches more than plan docs.

### 2026-11-20
Unblocked: was blocked: review gaps remain: commit 221b9d15224d12989546f63041eba5830f351439 (docs/surveys/upstream-survey.md): 'friday commits fnd-04' still lists this commit as untracked: it has no 'Directive:' trailer and touches more than plan docs.; commit e88157fffb023671f97b40eafb599110544f9fa5 (.claude/friday.json): 'friday commits fnd-04' still lists this commit as untracked: it has no 'Directive:' trailer and touches more than plan docs.

### 2026-11-20
Commits:
- 0c6c9bc fnd-04: analysis folder convention in analysis/README.md; ignore build/
- 25fa072 fnd-04: tools/build_report.py and shared deck template, with tests
- efd92ec fnd-04: target sets (default.yaml, schema check, tools/targets.py); reports print the set used
- c6c2652 fnd-04: LFS refused by public fork; reports stay normal git files, documented in reports/README.md
- 5450efb Plan: fnd-04 analysis source is writeup.md, not report.md (user-approved amendment); repo rule
- 558144a fnd-04: baseline report (reports/00_baseline.pdf/.pptx); analysis source is writeup.md
- dfe3a56 fnd-04: document report build and test commands in README.md and CLAUDE.md
- 934b30b fnd-04: report tables, counts and target set come from build/ and --targets, not typed by hand
Notes:
- Step 4 LFS test: tracked reports/*.pdf and reports/*.pptx, staged a 23-byte test object (oid abfaac6fb092...), ran `git lfs push origin --object-id <oid>`.
- GitHub refused: "@davidmhunt can not upload new objects to public fork davidmhunt/fmcw3-ckflight".
- Fallback taken: no LFS rules in .gitattributes (removed), test file unstaged and deleted, built reports will be committed as normal git files. Documented in reports/README.md.
- Nothing was pushed to a branch; only the LFS batch upload was attempted.
Verify: Verify passed: ./run uv run pytest tests -q (24 passed) and ./run tools/build_report.py analysis/00_baseline --check (check ok, 10 slides)
Independent review: Independent review: two content gaps fixed in 934b30b (target-set values printed in the PDF; every table and count generated by figures.py into build/ via placeholders). Remaining: 221b9d1 and e88157f listed untracked; main-session commits made before fnd-04 started, not fnd-04 work (davidmhunt/friday#30). The writeup.md amendment 5450efb was approved by the user 2026-11-20.

Rejected by user: 2026-11-20 Amended step 7: built reports not committed, rebuild by script

### 2026-11-20
Unblocked: was blocked: Amended step 7: built reports not committed, rebuild by script

### 2026-11-20
Commits:
- 0c6c9bc fnd-04: analysis folder convention in analysis/README.md; ignore build/
- 25fa072 fnd-04: tools/build_report.py and shared deck template, with tests
- efd92ec fnd-04: target sets (default.yaml, schema check, tools/targets.py); reports print the set used
- c6c2652 fnd-04: LFS refused by public fork; reports stay normal git files, documented in reports/README.md
- 5450efb Plan: fnd-04 analysis source is writeup.md, not report.md (user-approved amendment); repo rule
- 558144a fnd-04: baseline report (reports/00_baseline.pdf/.pptx); analysis source is writeup.md
- dfe3a56 fnd-04: document report build and test commands in README.md and CLAUDE.md
- 934b30b fnd-04: report tables, counts and target set come from build/ and --targets, not typed by hand
- 1a8dd5b fnd-04: built reports not committed; tools/build_all.py rebuilds all analyses
Notes:
- Step 4 LFS test: tracked reports/*.pdf and reports/*.pptx, staged a 23-byte test object (oid abfaac6fb092...), ran `git lfs push origin --object-id <oid>`.
- GitHub refused: "@davidmhunt can not upload new objects to public fork davidmhunt/fmcw3-ckflight".
- Fallback taken: no LFS rules in .gitattributes (removed), test file unstaged and deleted, built reports will be committed as normal git files. Documented in reports/README.md.
- Nothing was pushed to a branch; only the LFS batch upload was attempted.
Verify: Verify passed: ./run uv run pytest tests -q && ./run tools/build_report.py analysis/00_baseline --check
Independent review: no gaps

Rejected by user: 2026-11-20 Step 8: deck pdf export; targets split into design and performance groups

### 2026-11-20
Unblocked: was blocked: Step 8: deck pdf export; targets split into design and performance groups

### 2026-11-20
Commits:
- 0c6c9bc fnd-04: analysis folder convention in analysis/README.md; ignore build/
- 25fa072 fnd-04: tools/build_report.py and shared deck template, with tests
- efd92ec fnd-04: target sets (default.yaml, schema check, tools/targets.py); reports print the set used
- c6c2652 fnd-04: LFS refused by public fork; reports stay normal git files, documented in reports/README.md
- 5450efb Plan: fnd-04 analysis source is writeup.md, not report.md (user-approved amendment); repo rule
- 558144a fnd-04: baseline report (reports/00_baseline.pdf/.pptx); analysis source is writeup.md
- dfe3a56 fnd-04: document report build and test commands in README.md and CLAUDE.md
- 934b30b fnd-04: report tables, counts and target set come from build/ and --targets, not typed by hand
- 1a8dd5b fnd-04: built reports not committed; tools/build_all.py rebuilds all analyses
- 82ac8b5 fnd-04: deck PDF export via LibreOffice; targets split into design and performance, range resolution derived
- 5025121 fnd-04: tolerate float rounding in band check so bandwidth equal to the band passes
Notes:
- Step 4 LFS test: tracked reports/*.pdf and reports/*.pptx, staged a 23-byte test object (oid abfaac6fb092...), ran `git lfs push origin --object-id <oid>`.
- GitHub refused: "@davidmhunt can not upload new objects to public fork davidmhunt/fmcw3-ckflight".
- Fallback taken: no LFS rules in .gitattributes (removed), test file unstaged and deleted, built reports will be committed as normal git files. Documented in reports/README.md.
- Nothing was pushed to a branch; only the LFS batch upload was attempted.
Verify: Verify passed: ./run uv run pytest tests -q && ./run tools/build_report.py analysis/00_baseline --check
Independent review: gaps fixed in second review: 1. /home/david/Documents/pcb_work/fmcw3-ckflight/tools/targets.py:97-99: The band check rejects valid target sets. It computes the band width in floating point, '(fmax - fmin) * 1e9', and compares it strictly with 'bw > span_hz', with no tolerance. For many common band edges this span comes out a little under the true value, so a chirp bandwidth exactly equal to 'freq_max - freq_min' fails the schema check. Step 8 only asks it to fail when the bandwidth *exceeds* the band. The default set passes only because 5.875 - 5.725 happens to round up (150000000.00000036). The tests cover just that case, at /home/david/Documents/pcb_work/fmcw3-ckflight/tests/test_targets.py in test_bandwidth_must_fit_band. (evidence: Running './run uv run python -c ...' with freq_min_ghz=5.75, freq_max_ghz=5.85 and chirp_bandwidth_hz=100e6 makes tg.validate return ['targets: chirp_bandwidth_hz (1e+08) exceeds freq_max_ghz - freq_min_ghz (1e+08 Hz)']. Also, (5.85-5.75)*1e9 = 99999999.9999996 and (5.8-5.7)*1e9 = 99999999.99999964. A user who sets the bandwidth to the full band, as the default does, would be wrongly rejected and the report build would stop.)

Accepted by user: 2026-11-20
