---
title: "FMCW3 board: state as inherited"
---

# 1. Question

What is the state of the FMCW3 board (6-layer, Artix-7, 5.8 GHz FMCW radar, fork of
`ckflight/FMCW3-Kicad`) as inherited, before any review work: how many ERC and DRC items
does it carry, what do they mean, and which goal handles each?

# 2. Inputs and assumptions

- No result in this report depends on the target values; the set used is shown here.

{{targets}}


- Counts: `checks/baseline.json`, recorded with KiCad 10.0.5 by `checks/run_checks.sh --record`.
- Upstream is not ERC/DRC clean. The gate `checks/run_checks.sh` passes when errors do not
  exceed this baseline.
- DRC is nondeterministic: `solder_mask_bridge` jitters by +/-1 on identical input, so no
  conclusion here rests on an exact warning count.

# 3. Method

`figures.py` reads `checks/baseline.json`, splits each check into error and warning counts by
type, attaches a meaning and a handling goal to each type, and writes the bar chart and tables
into `build/`. The build tool fills the tables and numbers below from those files, and the target set from the `--targets` option. Nothing is edited by hand.

# 4. Findings

## Totals

{{table:summary.csv}}

![Violations by type as inherited](build/counts_by_type.png)

## ERC types

{{table:erc_types.csv}}

## DRC types

{{table:drc_types.csv}}

## Which goal handles what

All types are triaged by goal `layout-review` (first directive: a disposition per type, fix,
accept or waive). The bulk (library, footprint and grid warnings: {{fact:metadata_items}} of {{fact:total_items}} items) is library metadata, not electrical. The items with electrical meaning are the
{{fact:errors_total}} errors, the U40 WP/HOLD `pin_to_pin` warnings, the {{fact:isolated_copper}} copper islands and, pending a check
against the JLCPCB mask-web limit, the mask bridges. Goal `parts` covers library and footprint
resolution as part of the BOM work.

## Folder map

{{table:folder_map.csv}}

## Roadmap

{{table:roadmap.csv}}

# 5. Open decisions for the user

1. Target values: confirm the default set or give your own. Evidence: all 9 are assumed.
   Recommendation: set them before `rf-review` starts; this report is unaffected.
2. Triage: approve goal `layout-review` to give each type above a disposition.
   Recommendation: approve; start with the 5 errors and the U40 WP/HOLD pins.
3. Deck style: is this density and layout right for every later analysis? The template is
   reused by all later goals, so say what to change now.
