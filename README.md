# Repository layout and branches (davidmhunt fork)

Fork of [`ckflight/FMCW3-Kicad`](https://github.com/ckflight/FMCW3-Kicad), a
custom 6-layer, Artix-7-based 5.8 GHz FMCW radar board (KiCad 9). This is
Falcon's second fmcw3-derived reference design, evaluated alongside
[`hardware/fmcw3/`](../fmcw3/README.md) (Forstén's original) under
directives hw-17..19 — see `hardware/README.md`'s Boards table.

| Path | What |
|------|------|
| `fmcw3.kicad_pro`, `fmcw3.kicad_sch` + sheets (`adc`, `clock`, `fpga`, `fpga_config`, `mixer`, `opamp_amp`, `power`, `rx`, `tx`, `usb`) | The KiCad 9 schematic. |
| `fmcw3.kicad_pcb` | The 6-layer PCB layout. |
| `libs/`, `fmcw3.pretty/`, `fmcw3-rescue.lib`, `fmcw3-cache.lib`, `sym-lib-table`, `fp-lib-table` | Symbol/footprint libraries and lib tables. |
| `production/` | JLCPCB manufacturing outputs (BOM, positions, designators, netlist, a fab zip) — upstream's as-shipped fab package. |
| `fmcw3.pdf` | Upstream's schematic export (not a datasheet). |
| `fmcw3-backups/`, `rescue-backup/` | Upstream KiCad autosave/rescue backups. |

## Branch pinned

**`main`**, pinned at upstream/fork commit
[`5fba6a3`](https://github.com/davidmhunt/fmcw3-ckflight/commit/5fba6a33842a1cbaa5bbb830c68bed0dde02df7d)
("readme update") plus this README commit. `main` was David's call for the
baseline (hw-17 Decisions): it is upstream's default/most-current branch.
The other upstream branches present
(`jlcpcb_v2`, `jlcpcb_version`, `lt6232_implement`, `lt6232_ld3920_33`,
`oshpark_version`) are stackup/part-substitution variants — noted here in
case a later directive needs one of them, not evaluated in hw-17.

## Upstream

`ckflight/FMCW3-Kicad` (author: Cenk KESKİN). Related upstream repos named
in its README: firmware [`ckflight/FMCW3`](https://github.com/ckflight/FMCW3)
(forked here as [`davidmhunt/fmcw3-ckflight-fw`](https://github.com/davidmhunt/fmcw3-ckflight-fw),
submodule at `fpga/fmcw3-ckflight/`), and host radar software
(`FMCW_RADAR`, `FMCW_RADAR_2v2`) not forked by this directive (hw-17
Decisions #4: pending David).

## Known upstream artifact: stray lock file

Upstream's `main` branch has a committed
`~_autosave-fmcw3.kicad_pcb.lck` at the repo root. This is a KiCad
autosave lock file that should never have been committed; KiCad will
refuse to open `fmcw3.kicad_pcb` in the GUI while it sits next to the
project (it reads as "already open"). It is left as-is here — not ours to
fix, and the board has not been opened in the GUI by this directive (that
is hw-18).

## Licence

Upstream's README states GPLv3 (no separate `LICENSE` file in the repo).
Noted here; a full licence comparison against `hardware/fmcw3/`'s
Apache-2.0 is deferred to hw-19.

## No datasheet PDFs

Only one PDF ships in this repo (`fmcw3.pdf`, a KiCad schematic export);
no part datasheets are present or added here.
