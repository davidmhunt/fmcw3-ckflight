# checks/

ERC/DRC gate for the KiCad project in `kicad/` (KiCad 10.0.5 `kicad-cli`).

Run `checks/run_checks.sh`. It runs ERC and DRC into a temp dir and exits 0 only when
error counts are not above `baseline.json`, and DRC has 0 unconnected items and 0
schematic-parity issues. Warning counts are printed, never compared (DRC jitters:
`solder_mask_bridge` varies by +/-1 on identical input). `checks/run_checks.sh --record`
rewrites `baseline.json`, `erc.json` and `drc.json` from the current project.

`erc.json` and `drc.json` are one representative run on the restructured project.

## Native vs Docker (fnd-03 step 6, compared once)

Both `./run --native checks/run_checks.sh` and `./run --docker checks/run_checks.sh` PASS with
identical errors (ERC 1, DRC 4, 0 unconnected, 0 parity). Raw reports of both were compared by
type:

- DRC: identical by type (409 items; `solder_mask_bridge` 199 in both this time, it jitters).
- ERC errors and `endpoint_off_grid`, `lib_symbol_mismatch`, `pin_to_pin`: identical.
- ERC warnings differ: native 1118 total, Docker 1139. Docker has 7 more
  `footprint_link_issues` (342 vs 335: libraries `Package_DFN_QFN` 5, `Connector_USB` 1,
  `Oscillator` 1 "not in the current configuration") and 14 more `lib_symbol_issues`
  (540 vs 526: libraries `Jumper` 12, `Device` 2, `Connector` 1 not configured; native
  instead reports one "symbol `USB_C_Receptacle_USB2.0` not found in `Connector`").
  These are KiCad stock libraries that the host's global library tables resolve and the
  container's do not (the container runs as the caller's uid without the host's KiCad user
  config). They are environment-library warnings, not design findings, and warnings are
  never compared by the gate. Record the baseline with `--native`.

## Before / after counts (as forked, cf34c04, vs after fnd-02 step 4)

Before (old `reports/`) is upstream as forked; after is the re-recorded baseline after the
library tables were rewritten (step 4). No schematic or board file content changed.

| Check | Type | Severity | Before | After |
|-------|------|----------|-------:|------:|
| ERC | power_pin_not_driven | error | 1 | 1 |
| ERC | lib_symbol_issues | warning | 558 | 526 |
| ERC | lib_symbol_mismatch | warning | 0 | 32 |
| ERC | footprint_link_issues | warning | 335 | 335 |
| ERC | endpoint_off_grid | warning | 222 | 222 |
| ERC | pin_to_pin | warning | 2 | 2 |
| DRC | clearance | error | 4 | 4 |
| DRC | solder_mask_bridge | warning | 200 | 200 |
| DRC | lib_footprint_issues | warning | 199 | 199 |
| DRC | isolated_copper | warning | 6 | 6 |
| DRC | nonmirrored_text_on_back_layer | warning | 1 | 1 |
| DRC | unconnected items / schematic parity | - | 0 / 0 | 0 / 0 |

ERC total is unchanged (1118); 32 symbols moved from "library symbol issue" to "library
symbol differs from schematic copy" because their libraries now resolve. Pre-existing
findings are left for goal `layout-review`.

Netlist equality (before vs after the move, step 6): components and nets are identical.
The only difference is the netlist `(libraries ...)` block, which lost 11 libraries that
existed only at `/home/ck` on upstream's machine and cannot be restored. The user accepted
this on 2026-11-19 as library metadata, not an electrical change.
