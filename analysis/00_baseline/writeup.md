---
title: "FMCW3 board: state as inherited"
---

# 1. Question

What is the state of the FMCW3 board (6-layer, Artix-7, 5.8 GHz FMCW radar, fork of
`ckflight/FMCW3-Kicad`) as inherited, before any review work: how many ERC and DRC items
does it carry, what do they mean, and which goal handles each?

# 2. Inputs and assumptions

- Target set: `default` (`analysis/targets/default.yaml`). All 9 values are marked `assumed`.
  No result in this report depends on them; the set is printed by the build tool.
- Counts: `checks/baseline.json`, recorded with KiCad 10.0.5 by `checks/run_checks.sh --record`.
- Upstream is not ERC/DRC clean. The gate `checks/run_checks.sh` passes when errors do not
  exceed this baseline.
- DRC is nondeterministic: `solder_mask_bridge` jitters by +/-1 on identical input, so no
  conclusion here rests on an exact warning count.

# 3. Method

`figures.py` reads `checks/baseline.json`, splits each check into error and warning counts by
type, attaches a meaning and a handling goal to each type, and writes the bar chart and tables
into `build/`. Nothing is edited by hand.

# 4. Findings

## Totals

| Check | Errors | Warnings | Other |
|-------|-------:|---------:|-------|
| ERC   | 1      | 1117     | -     |
| DRC   | 4      | 406      | no unconnected items, no schematic-parity issues |

![Violations by type as inherited](build/counts_by_type.png)

## ERC types

| Type | Count | Severity | Meaning |
|------|------:|----------|---------|
| lib_symbol_issues | 526 | warning | Symbol library not found, or symbol missing from it |
| footprint_link_issues | 335 | warning | Footprint library or footprint not resolved |
| endpoint_off_grid | 222 | warning | Wire or pin end off the schematic grid |
| lib_symbol_mismatch | 32 | warning | Library symbol differs from the schematic copy |
| pin_to_pin | 2 | warning | Pin types forbid the connection (U40 WP/HOLD) |
| power_pin_not_driven | 1 | error | A power input pin (GND) has no power output driving it |

## DRC types

| Type | Count | Severity | Meaning |
|------|------:|----------|---------|
| solder_mask_bridge | 200 | warning | Mask web between pads thinner than the rule |
| lib_footprint_issues | 199 | warning | Board footprint differs from, or is missing in, its library |
| isolated_copper | 6 | warning | Copper island connected to no net |
| clearance | 4 | error | Copper closer than the rule allows (4 items at coupler Z1) |
| nonmirrored_text_on_back_layer | 1 | warning | Back-layer text is not mirrored |

## Which goal handles what

All types are triaged by goal `layout-review` (first directive: a disposition per type, fix,
accept or waive). The bulk (library, footprint and grid warnings: 1314 of 1528 items) is library metadata, not electrical. The items with electrical meaning are the
5 errors, the U40 WP/HOLD `pin_to_pin` warnings, the 6 copper islands and, pending a check
against the JLCPCB mask-web limit, the mask bridges. Goal `parts` covers library and footprint
resolution as part of the BOM work.

## Folder map

| Folder | Content |
|--------|---------|
| `kicad/` | KiCad 10 project, root sheet `fmcw3.kicad_sch` |
| `production/` | As-ordered XC7A35T fab package, never regenerated |
| `checks/` | ERC/DRC gate, baseline and recorded reports |
| `analysis/`, `reports/`, `tools/` | Report sources, built PDF and decks, pipeline |
| `parts/`, `datasheets/`, `docs/`, `legacy/`, `docker/`, `runs/` | BOM, manifests, plans, old exports |

## Roadmap

| Goal | Covers | Review-plan phase |
|------|--------|-------------------|
| foundation | Repo layout, environment, report pipeline, tools | setup |
| parts | BOM, DigiKey and JLCPCB checks, datasheets | 1 |
| rf-review | RF level plan, 50 ohm impedance | 2, 3 |
| layout-review | ERC/DRC triage, layout checks, bring-up | 4, 5 |
| sim-spurs | Supply noise, IF filter, PLL, frequency plan | 6, 7 |

# 5. Open decisions for the user

1. Target values: confirm the default set or give your own. Evidence: all 9 are assumed.
   Recommendation: set them before `rf-review` starts; this report is unaffected.
2. Triage: approve goal `layout-review` to give each type above a disposition.
   Recommendation: approve; start with the 5 errors and the U40 WP/HOLD pins.
3. Deck style: is this density and layout right for every later analysis? The template is
   reused by all later goals, so say what to change now.
