# reports/

Baseline ERC/DRC on `fmcw3-ckflight` as forked (`main` @ cf34c04), KiCad
10.0.5 `kicad-cli`, no fixes applied. See directive hw-18's Log for violation
counts and types.

| File | Command |
|------|---------|
| `erc.json` | `kicad-cli sch erc --format json fmcw3.kicad_sch` |
| `drc.json` | `kicad-cli pcb drc --format json fmcw3.kicad_pcb` |

DRC is nondeterministic run-to-run on identical input (`solder_mask_bridge`
count jitters +/-1), same as observed on `fmcw3` in hw-01; `drc.json` is one
representative run (410 violations, reproduced twice).
