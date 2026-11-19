# fmcw3-ckflight

Fork of [`ckflight/FMCW3-Kicad`](https://github.com/ckflight/FMCW3-Kicad): a 6-layer,
Artix-7 (XC7A100T, U30), 5.8 GHz FMCW radar board. FPGA, HMC431LP4 VCO, dual RX with
ADL5802 mixer and ADA4940 IF amplifiers, LTC2292 ADC, FT2232H USB FIFO. KiCad 10 project in
`kicad/`. This fork is a review of the design (parts, RF chain, impedance, testability,
ERC/DRC, spurs), used as a submodule of the Falcon parent repo under `hardware/`.

## Folder map

| Path | What |
|------|------|
| `kicad/` | The KiCad 10 project: `fmcw3.kicad_pro`, `fmcw3.kicad_sch` + ten sheets, `fmcw3.kicad_pcb`, `fmcw3.pretty/`, `libs/`, lib tables. |
| `production/` | Upstream's as-ordered JLCPCB fab package, the XC7A35T build. Not regenerated. |
| `checks/` | ERC/DRC gate (`run_checks.sh`), `baseline.json`, recorded reports. |
| `parts/` | BOM groups, DigiKey availability check. |
| `docs/` | `goals/`, `directives/` (friday plan), `surveys/`, `references/` (review plan), `upstream-readme.md`. |
| `analysis/`, `reports/`, `datasheets/`, `docker/` | Placeholders, each with its own README. |
| `legacy/` | Upstream's old exports, unused; see `legacy/README.md`. |

## Running the checks

```
checks/run_checks.sh            # ERC + DRC against checks/baseline.json
checks/run_checks.sh --record   # re-record baseline and reports
```

Needs `kicad-cli` 10.0.5. It exits 0 only when error counts are not above the baseline and
DRC has 0 unconnected items and 0 schematic-parity issues. The upstream design is not
ERC/DRC clean; see `checks/README.md`.

## Roadmap

Goals live in `docs/goals/`:

- `foundation`: clean layout, repeatable environment, report pipeline.
- `parts`: BOM with DigiKey and JLCPCB availability, and datasheets.
- `rf-review`: RF level plan and 50 ohm impedance review.
- `layout-review`: ERC/DRC triage, layout checks, testability and bring-up plan.
- `sim-spurs`: supply-noise, IF and PLL simulation and the spur frequency plan.

## Upstream and licence

Upstream is `ckflight/FMCW3-Kicad` (author Cenk Keskin); its README is kept as
`docs/upstream-readme.md`. Related repos: firmware
[`ckflight/FMCW3`](https://github.com/ckflight/FMCW3) (forked as
[`davidmhunt/fmcw3-ckflight-fw`](https://github.com/davidmhunt/fmcw3-ckflight-fw)) and the
host software `FMCW_RADAR`, `FMCW_RADAR_2v2`.

Licensed under GPLv3, as upstream states; full text in `LICENSE`.

## Archived upstream branches

The upstream branches below were tagged (annotated) and then deleted from `origin`; each
tag points at the former branch tip.

| Branch | Tagged commit | Tag | Merged into main |
|---|---|---|---|
| `jlcpcb_v2` | `100aed1743` | `archive/jlcpcb_v2` | yes |
| `jlcpcb_version` | `3af22f786f` | `archive/jlcpcb_version` | yes |
| `lt6232_implement` | `256c33f6f3` | `archive/lt6232_implement` | yes |
| `lt6232_ld3920_33` | `546dfd13b2` | `archive/lt6232_ld3920_33` | yes |
| `oshpark_version` | `e39d97a5c4` | `archive/oshpark_version` | no |
