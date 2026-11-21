# par-01: BOM export from the schematic and automated DigiKey + JLCPCB checks
Status: done
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_bom.py tests/test_digikey.py tests/test_jlc.py -q && ./run parts/bom.py --boards 5 --offline
Hardware: none

## Goal
One command produces the grouped BOM from the schematic and checks every line against DigiKey
and the JLCPCB parts library for `--boards N`. It holds when the tests pass on recorded
responses and a live run writes `parts/out/availability.csv` with a status on every line.

## Steps
1. `parts/bom.py`: export with `kicad-cli sch export bom` from `kicad/fmcw3.kicad_sch`, group by
   value, footprint and part-number fields, classify each group (`mpn`, `generic`, `dnp`,
   `nopart`), merge decisions from `parts/decisions.csv` (par-03) until the fields are in the
   schematic. Confirm the group and ref counts against `production/bom.csv` (84 groups, 370 refs)
   and explain any difference.
2. DigiKey: refactor `parts/check_digikey.py` into an importable module reading `.env`; per line
   return status, stock, price at quantity, lead time, lifecycle, datasheet URL. Generic passives
   get a parametric search (value, package, tolerance, voltage, dielectric) and a suggested MPN.
3. JLCPCB: `parts/check_jlc.py`. Use the open parts data that the `bouni/kicad-jlcpcb-tools`
   plugin uses (its downloadable parts database) or the `jlcsearch` API; pick whichever works
   unattended today and record why. Per line: LCSC number, stock, Basic/Preferred/Extended,
   price, and match confidence (exact MPN, same package, or needs review). Cache the database
   outside git. Record whether the plugin itself installs on KiCad 10 for GUI use.
4. `parts/bom.py [--targets NAME] [--boards N] [--offline] [--check]`: the board count defaults
   to `board_quantity` in the target set (`analysis/targets/default.yaml`, loaded through
   `tools/targets.py`); `--boards` overrides it. Writes `parts/out/bom.csv`,
   `availability.csv` (both sources side by side, a per-line verdict: JLC assemble, consign from
   DigiKey, hand-solder, unresolved) and a JLCPCB-format BOM and CPL under `parts/out/jlc/`.
   `--offline` uses the cache; `--check` exits non-zero on a placed part without an MPN.
   The upstream files already in `parts/` (`parts.csv`, `availability.csv`,
   `fields_to_apply.csv`, `manufacturing_check.md`) are inputs to compare against: reuse what
   is still right, move superseded ones to `parts/legacy/` with a line in `parts/README.md`.
5. Tests with recorded API responses (no network, no keys): grouping, classification, DigiKey
   and JLC parsing, verdict logic, quantity scaling with spares.
6. `parts/README.md`: how it works, the columns, how to add keys, what "match confidence" means.
   Add `parts/bom.py`, `parts/check_digikey.py` and `parts/check_jlc.py` to `MANUAL.md` (a new
   "Parts and availability" section) and extend `tests/test_manual.py` to cover `parts/*.py`
   command-line tools.

## Rules
- DigiKey keys are read from `.env` at run time only; never print, log or commit them, and
  never write them into recorded test responses (scrub headers and tokens).
- The JLCPCB parts database cache lives under a gitignored path, never in git.
- The schematic is read headless (`kicad-cli`); nothing under `kicad/` is written.

## Out of scope
- Choosing substitutes or resolving suffixes (par-03).
- Editing the schematic (par-04).
- Ordering anything.

## Allowed commands
- `./run *`

## Log

### 2026-11-21
Commits:
- 08102e2 parts/bom.py: grouped BOM from the schematic via kicad-cli, with classes and decisions merge
- 937837c parts/check_digikey.py: importable DigiKey client, per-line result and parametric search for generic passives
- 0aa0de7 parts/check_jlc.py: JLCPCB availability from the kicad-jlcpcb-tools parts database, cached outside git
- b048b4e parts/bom.py: availability.csv with verdicts, JLCPCB BOM and CPL, --targets/--boards/--offline/--check; upstream parts files to parts/legacy/
- ca7cd50 tests/test_bom.py: verdict logic, quantity scaling with spares, availability rows, JLC BOM/CPL, DigiKey cache (no network)
- 485e4a8 parts/README.md and MANUAL.md Parts and availability section; test_manual covers parts/*.py tools
- c21cfdf par-01 review fixes: --check counts generic passives, spec fields reach the DigiKey search, real recorded DigiKey product test, README records source choice
Notes:
- step 3 (check_jlc): source chosen = the plugin's parts database (bouni.github.io/kicad-jlcpcb-tools, current-parts-fts5.db.zip.001-003, 186 MB zipped, 831 MB unpacked, 821k parts, SQLite FTS5 trigram). No key, deterministic, offline after one download; has stock, Basic/Preferred/Extended, price breaks, MPN, package.
- rejected jlcsearch.tscircuit.com as primary: it answers, but searching the exact MPN GRM155R71C104KA88D returned no rows, stock was null for C71629, there is no manufacturer field, and it is a live third-party service (not repeatable). Not implemented as a fallback.
- cache: parts/cache/jlcpcb/ (gitignored).
- live run, 3 boards: every generic and mpn line resolved to an LCSC part (package match for values; review for part numbers typed into Value: FB1.., FB11, L1, L5 which has only 3 in stock). nopart and dnp lines are n/a.
- plugin on KiCad 10: release 2026.04.03 PCM metadata.json has kicad_version 6.0 and no kicad_version_max, so PCM permits it on 10.0.5; the repo's template now says kicad_version_max 10.0. NOT installed or run in the GUI here (needs the user's KiCad), so GUI use is untested.
Verify: Verify passed: ./run uv run pytest tests/test_bom.py tests/test_digikey.py tests/test_jlc.py -q && ./run parts/bom.py --boards 5 --offline
Independent review: gaps fixed in second review: 1. parts/bom.py:381-383 (missing_mpn), used by --check at bom.py:448-453: '--check' is supposed to exit non-zero on any placed part without an MPN, but it only counts 'nopart' groups. Generic passives (class 'generic') have no MPN either and are skipped, so about 300 placed refs never trip the gate. The goal ('--check reports no placed part without an MPN') and par-04's Verify both depend on this gate, and both would pass with every 0402 capacitor and resistor still lacking an MPN. (evidence: './run parts/bom.py --boards 5 --offline --check' prints '83 groups, 370 refs; mpn 0, generic 45, dnp 2, nopart 36' and then '31 lines (48 refs) are placed parts without an MPN'. None of the 45 generic groups are counted. The README (line 22) describes the exclusions as only 'vias, pads, mounting holes and the printed coupler'. tests/test_bom.py:155 asserts that missing_mpn returns only U1, while C1/C2 (generic, no MPN) are left out.) 2. parts/bom.py:46-50 (PART_FIELDS / EXPORT_FIELDS) and merge_decisions at bom.py:112-124; parts/check_digikey.py:233-245 (parametric_query): Step 2 asks for a parametric search on value, package, tolerance, voltage and dielectric. check_digikey.parametric_query reads group['Tolerance'], ['Voltage'] and ['Dielectric'], but bom.py never exports or merges those fields. Neither the kicad-cli field list nor decisions.csv carries them, so the groups bom.py hands over never contain them. The search can only ever use value and package, even after par-03/par-04 add tolerance, voltage or dielectric to the schematic or to decisions.csv. (evidence: EXPORT_FIELDS = ['Reference','Value','Footprint',''{DNP}',''{EXCLUDE_FROM_BOM}'] + ['MPN','Manufacturer','LCSC','DigiKey PN']. merge_decisions copies only PART_FIELDS and DNP. group_rows builds groups from GROUP_KEYS only. In parts/out/availability.csv every generic dk_query is just value plus package (e.g. '100nF 0402').) 3. parts/out/availability.csv (untracked live output); tests/test_digikey.py:1-62: The goal requires a live run that checks every line against DigiKey and JLCPCB. Only JLCPCB was ever queried. Every DigiKey-checkable line in the output reads 'Not-cached', and no DigiKey cache exists, so the DigiKey client and parser have never seen a real API response. The DigiKey tests use hand-built 'recorded-shape' fixtures, not recorded responses, so the v4 field mapping (QuantityAvailable, ProductVariations, ManufacturerLeadWeeks, Parameters text) is unverified against the real API. (evidence: 45 lines in parts/out/availability.csv have dk_status Not-cached (all 45 generic groups; the rest are n/a). 'git ls-files --others --ignored parts/cache' lists only parts/cache/jlcpcb/current-parts-fts5.db, with no parts/cache/digikey/. runs/par-01/notes.md records only a JLC live run. The test_digikey.py docstring says the fixtures 'follow the ... schema, trimmed', i.e. they are synthetic.) 4. parts/check_jlc.py:8-9; parts/README.md: Step 3 says to record why the plugin database was chosen over jlcsearch, and whether the plugin installs on KiCad 10 for GUI use. Both are recorded only in the untracked runs/par-01/notes.md, which will not land with the PR. check_jlc.py's docstring says 'See parts/README.md for why this and not the jlcsearch API', but parts/README.md has no such explanation and no mention of the plugin on KiCad 10. (evidence: A git grep for 'jlcsearch|kicad-jlcpcb-tools|installs on|GUI use' over parts/README.md, MANUAL.md and docs finds only the directive itself. The rationale and the KiCad 10 PCM finding appear only in runs/par-01/notes.md lines 1-5 (untracked).)
