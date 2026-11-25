---
title: "Parts availability, both boards"
---

# 1. Summary

Snapshot **{{fact:snapshot}}** of `parts/out/availability/`, made by `parts/availability_report.py`
from `parts/final_parts.csv` (fitted rows) and `parts/inventory.csv`. JLC database dated
**{{fact:jlc_database_date}}**; DigiKey: {{fact:digikey}}. {{fact:lines}} fitted lines, {{fact:boards}}
boards of each type, {{fact:spares}} spares per line that is not in the JLC Basic library.

Result: **{{fact:short}} short**, **{{fact:thin}} thin**, {{fact:unknown}} unknown, {{fact:ok}} ok.

{{fact:lag_note}}

Need per line is refs per board times boards plus spares. Status: `short` is stock below the need;
`thin` covers it with less than 3 times the need left; `ok`; `unknown` has no data. For `jlc-library`
lines the inventory (`parts/inventory.csv`) is counted first, then JLC stock; for `jlc-sourcing` and
`hand-solder` lines the stock is DigiKey's. Every line of the snapshot is in its `lines.csv`.

## 1.1 Status counts per board

{{fact:t_counts}}

# 2. Short lines

Each goes back to the user with its fallback; no part choice was changed.

{{fact:t_short}}

# 3. Thin lines

{{fact:t_thin}}

# 4. Unknown lines

{{fact:t_unknown}}

# 5. Changes since the previous snapshot

Previous snapshot: {{fact:previous}}. Lines changed: {{fact:n_changes}}.

{{fact:t_changes}}

# 6. Sourced and hand-solder lines

{{fact:n_dk}} lines are bought by JLC sourcing or by the user from DigiKey, so their stock is DigiKey's.

{{fact:t_sourced}}

# 7. Rerun

`./run parts/availability_report.py --refresh` writes a new dated snapshot (never over an earlier one);
`./run tools/build_report.py analysis/14_parts_availability` rebuilds this report from the latest one.
