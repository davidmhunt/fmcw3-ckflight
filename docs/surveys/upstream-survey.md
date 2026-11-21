# Upstream survey: legacy files, branches, firmware (fnd-01)

Compared against the working tree at 76be142 (schematics KiCad 9 format, board re-saved KiCad 10) and
`origin/main`. Current exports: `runs/fnd-01/cur.net`, `cur.xml`, `cur_bom.csv` (kicad-cli 10.0.5; 382
netlist components, 397 nets, 370 real refdes). Raw findings: `runs/fnd-01/notes.md` (untracked). Firmware
clone: `runs/fnd-01/fw` at cb7f097.

## Legacy files

Dates are git first/last-change dates (working-tree mtimes are all checkout time).

| path | origin | content | superseded by current? |
|---|---|---|---|
| `fmcw3.net` | 26e19f2, 2026-08-04, Eeschema 9.0.7 | Identical to the fresh export `cur.net`: 382 components, 397 nets, no refdes, value, footprint or connectivity difference | Yes, identical and regenerable |
| `fmcw3.xml` | 00dd3f2, 2025-05-01; design date 2024-01-13, Eeschema 7.0.1 | Older iteration: 400 components, 395 nets. 68 refdes only here (IF stage C124-C151, L8-L11, P3/P4/P6/P9-P16, Q2, DNP parts), 63 only in current (J1 USB-C, JP1-JP12, LT6232 U45, U38, U41-U49). U30 XC7A15T (current 100T), U40 W25Q32JV (W25Q128JV), U6 NB3N551 (PL133-37), U25 BU33SD5WG (LD3920_33), U31 USB-MICRO (J1). Nets renamed (3V6 to 3V8, ADC_REF to ADC_CLK, ADF_REF to ADF_CLK_REF, FPGA_REF to FPGA_CLK) | Yes |
| `fmcw3.csv` | 880901e, 2026-05-24 | Grouped BOM, 83 rows, 387 parts incl. 44 DNP, pre-dating 546dfd1 (DNP deletion). Lacks the LT6232, XC7A100T, PL133-37, LD3920_33 and SMA parts of current | Yes (current BOM: `runs/fnd-01/cur_bom.csv`, `parts/parts.csv`) |
| `fmcw3.sch` | 00dd3f2, 2025-05-01; KiCad 4/5 format v2 | Root sheet only (32 components), byte-identical to `rescue-backup/fmcw3-2023-03-24-11-11-22.sch`. Its sub-sheets exist only in `rescue-backup/`, so it cannot open standalone | Yes |
| `rescue-backup/*.sch` (adc, fmcw3, fpga, if, imu, mixer, power, rx, tx, usb) | 00dd3f2; 2023-03-24 KiCad 5 rescue/migrate backup | 398 real refdes (incl. unannotated `C? R? U?`) vs 370 current; 304 in common, values differ on 95. Legacy-only blocks: IF filter/amp stage (replaced by LT6232 in `opamp_amp.kicad_sch`, commit range lt6232_implement) and the LSM6DS3H IMU sheet (never in current) | Yes; IMU and IF stage are retired content |
| `rescue-backup/fmcw3-cache-2023-03-24-11-11-22.lib`, `sym-lib-table-2023-03-24-11-12-48` | 00dd3f2 | Byte-identical to `fmcw3-cache.lib`; old sym-lib-table | Yes |
| `fmcw3-cache.lib` | 00dd3f2; EESchema-LIBRARY 2.3 | 42 symbols. Not embedded by name in current: 74AHC1G04, ADA4940-2, CONN_02X04, D_Schottky, KT2520K, L7981, MGA-25203, MIC5301, MOS_N_GSD, NB3N551, TPS7A91, USB-MICRO (all retired parts) | Yes. Current schematics embed their own symbols in `lib_symbols` and export cleanly without it |
| `fmcw3-rescue.lib` | 00dd3f2; EESchema-LIBRARY 2.4 | 13 symbols; 74AHC1G04, CONN_02X04, D_Schottky not embedded in current | Yes |
| `libs/fmcw3.lib`, `.bak`, `.bck`, `.dcm` | 00dd3f2 | Personal symbol library, 96 symbols (`.bak` 95; `.bck`, `.dcm` are 171-byte stubs). 75 symbols are unused by current: candidate parts never placed (AD7266, AD9269, ADA4932-2, ADL5380, HMC313, MAX2870, LPC4370, LT6230, LTC6362, PE42420/23/41, LSM6DS3H, ...) | Yes for the design; a part-ideas list only |
| `fmcw3-backups/*.zip` (25) | 26e19f2 and earlier, 2026-07-02 to 2026-08-04 | KiCad 9 project snapshots. Last (2026-08-04_152211): all 11 `.kicad_sch` byte-identical to the tree, netlist identical, only `.kicad_pcb` differs (KiCad 10 re-save). 2026-08-04_135212 differs only in U30 = XC7A35T. 2026-07-03..08-03 differ only in U30 and R26/R28/R31/R38 = 500 ohm (current 1k). First five (2026-07-02) also differ in 2-8 connectivity groups (IF1/IF2 jumpers JP9-JP12, R97/R99, L14/L15, R55/R56), early rework that was settled | Yes. Every revision of the tracked sch/pcb is also in git history |
| `production/backups/fmcw3_2026-07-07_20-50-10.zip` | 22b23f1, 2026-07-07 | Five members, byte-identical (cmp) to `production/{fmcw3.zip,bom.csv,positions.csv,designators.csv,netlist.ipc}` | Redundant copy |
| `production/` (other files) | 1aa35ac/22b23f1, 2026-07-04/07 | As-ordered JLCPCB package, the XC7A35T build (U30 35T, R26/R28/R31/R38 = 500 ohm). Current schematic is the 100T build (26e19f2) | Not legacy; the only record of what was ordered |

Other observations (for fnd-02, not deletions):
- `sym-lib-table` lists 172 Legacy entries with absolute `/home/ck/...` paths that do not exist here and no
  entry for `fmcw3`, `fmcw3-cache`, `fmcw3-rescue` or `libs/fmcw3`. `fp-lib-table` has `fmcw3` ($KIPRJMOD) plus
  `Footprints` at a missing `/home/ck` path. Boards still resolve because footprints are embedded in the
  `.kicad_pcb`.
- `fmcw3.pretty` is current, not legacy (75 footprints, identical to the last backup zip), but only 16 are
  referenced as `fmcw3:*` by the board; C_0402b, R_0402b, EJ508A, coupler, DFN-8, SOT-23-5L, USB_MICRO,
  MGA-25203, TFBGA-100 and others are leftovers.

## Branches

Topology (`git branch -r --merged origin/main`, merge-base/rev-list, `git cherry`): a linear chain, all merged
except `oshpark_version`. a06aa38 "OSH Park version is ready" (2025-08-21, on main) then `jlcpcb_version`
3af22f7 (2026-05-23), `jlcpcb_v2` 100aed1 (2026-05-26), `lt6232_implement` 256c33f (2026-06-04),
`lt6232_ld3920_33` 546dfd1 (2026-06-26, merged in a40af5c), then main (22b23f1, 26e19f2, 5fba6a3). No LCSC
numbers exist in any branch's schematic, `fmcw3.net` or `fmcw3.csv`; the only LCSC column is the empty
`LCSC Part #` in `production/bom.csv`. Read only via `git show`/`git diff`, no checkout.

### origin/jlcpcb_version (merged; tip 3af22f7)
35 commits past a06aa38. 50 ohm RF rework: R55-58 550 to 1k, coupler 0.23 mm to 0.169 mm from CST sim (5bd5c1a,
c366e69); ADL5802 IF pull-up fix (0f63396); 0.1016 min track/clearance; U30 XC7A15T to XC7A35T; FB11 CIC21P101NE
to MPZ2012S101AT000; about 29 R/C retunes (R59-62 8.2k to 20.5k, R45 2.61k to 49.9k, R84/85/88 33 to 22);
+R19,U2,U31,U37,U5, -C13,D4,R26. Fab outputs: `production/` dated 2026-05-23 (empty LCSC column) and
`fabrication-toolkit-options.json`. Includes the FPGA CLKOUT/RD# pin change (586876e). Everything is in main.

### origin/jlcpcb_v2 (merged; tip 100aed1)
+5 commits. Removed `production/` from the tree (main later got the 2026-07-07 package). Added `readme.md`
(181 lines, by Cenk Keskin) and `sym-lib-table`. U6 NB3N551 to PL133-37, +Y2 TCXO, +C1, -U4 (880901e); SW1/SW2 to
B3U-1000P; U26-28 baluns to 5400BL15B0050001E; R9/11/12 16.7 to 16.9; R21/84/85/88 22 to 33; R109 240 to 1k.

### origin/lt6232_implement (merged; tip 256c33f)
+10 commits. LT6232 op-amp stage: new `opamp_amp`, `clock`, `fpga_config` sheets, `if.kicad_sch` removed, `fpga`
restructured; 413 to 397 components (+48/-64: removed C124-151, L8-L11, P10-P15; added JP1-JP8, J2, L12-L15,
U38, U41). U34/U35 ADA4940-2 to solder pads; U40 W25Q32JV to W25Q128JV; R55-58 1k to 0; R104 68k to 10k.
README: +7 images only. Adds `~fmcw3.kicad_*.lck` files (the stray lock-file origin).

### origin/lt6232_ld3920_33 (merged via a40af5c; tip 546dfd1)
+3 commits. U25 BU33SD5WG to LD3920_33; Y2 to ECS-TXO-32CSMV-400; C71 DNP to 10u; 14 DNP refs deleted; copper
pours/vias checked. 397 to 383 components. README: author block only.

### origin/oshpark_version (NOT merged; tip e39d97a, 2025-11-02)
Merge base a06aa38. 3 commits not in main (10c91b4, 3b788b0, e39d97a; `git cherry` all "+"); main has 64 not in
it. Changes: FPGA CLKOUT A15 to D13 and RD# B14 to A15 (B14 NC); `fmcw3.kicad_pro` zone min_clearance 0.16 to 0,
undefined_netclass=error; PCB 3h RF-path ground spacing for 50 ohm microstrip; PDF re-export. No
refdes/value/footprint change (410 components, same as a06aa38). The pin change is in main's `fmcw3.net`
(arrived via jlcpcb_version 586876e/720ff8b), and main's board was fully re-routed since (40a98db, 05ad72c), so
the RF clearance edits are superseded in practice (the PCB differs by about 40k lines, not diffable). No fab
output on the branch (only `fmcw3.pdf`, `fmcw3.csv`). It holds nothing the current project lacks except the
OSH Park fab target. Main's PCB `gr_text` still mentions "jlcpcb and oshpark branches".

## Firmware

Repo `davidmhunt/fmcw3-ckflight-fw` (HEAD cb7f097, 248 commits, remote `upstream` ckflight/FMCW3). A Vivado
2025.2 project dump (`FMCW3.xpr`, `.cache`, `.gen`, Vitis workspace `FMCW3_Microblaze`). Sources:
`FMCW3.srcs/sources_1/new/{top_module,adc,control,config,usb_sync}.vhd`; MicroBlaze app
`FMCW3_Microblaze/FMCW3_App/src/{helloworld,spi,gpio,definitions}.c/.h`; one constraint file
`FMCW3.srcs/constrs_1/new/pinout.xdc`.

FPGA variants:
- Two prebuilt outputs committed in 1b354b5 (2026-08-04): `top_module_xc7a35t.{bit,bin,ltx}` (built 2026/08/04
  15:29) and `top_module_xc7a100t.{bit,bin,ltx}` (15:36), plus `top_module.xsa`.
- `FMCW3.xpr` line 11 targets xc7a100tftg256-1 only; there is one xdc and no separate 35T project, so the
  35T build was made by retargeting (same FTG256 package; per-bank validity for 35T not verified).
- README: `jlcpcb_version` branch = XC7A35T, main = XC7A100T, which matches the schematic (U30 XC7A100T-1FTG256C).

Clocks and ADC:
- `sysclk` 40 MHz: `pinout.xdc` create_clock period 25.00 on N11; `top_module.vhd` comment ECS-TXO 40 MHz; BOM Y2
  ECS-TXO-32CSMV-400. The same source feeds `/FPGA_CLK` (R13) and `/ADC_CLK` (R15, R21 to U8 CLKA/CLKB).
- `usb_clk` 60 MHz from FT2232H (xdc period 16.667 on D13), synchronous 245 FIFO.
- `clk_wiz_0.xci`: 40 MHz in, VCO 1000 MHz, CLKOUT1 40 MHz, CLKOUT2 100 MHz (MicroBlaze/AXI).
- ADC LTC2292 sampled at 40 MHz (`adc.vhd`: ch1 on rising, ch2 on falling edge; 12 bit padded to 16). README: 40
  MSPS. `fir_compiler_0.xci`: decimation 20, so 2 MSPS per channel; default coefficients
  `fir_hpf_400khz_gain16.coe`. 500 samples per 250 us chirp.

ADF4158 (`FMCW3_App/src/helloworld.c`, `ADF4158_Configure_Sweep`; runtime from a 24-byte host packet, no hardcoded
chirp): FREQ_REF = 40 MHz, PFD = 40 MHz (R counter 1); start freq = word x 10 MHz, bandwidth = word x 1 MHz,
sweep time in us. Registers written R7 to R0; R4 READ BACK TO MUX = 3, CLK DIV MODE = 3; R3 sawtooth (triangular
if sweep_type != 0); R2 CSR on, CP current index 14, prescaler 8/9; R0 ramp on. MUXOUT is the ramp-status flag
used by `control.vhd`. The code comment says "max pfd is 32mhz" while 40 MHz is used: flag for rf-review
(datasheet limit not checked here).

Pin-constraint comparison (`pinout.xdc` against U30 in `runs/fnd-01/cur.net`): all 56 constrained ports checked,
no mismatches. Examples: sysclk N11 = /FPGA_CLK; usb_clk D13 = /fpga/CLKOUT; reset_n B4 = /fpga/RESET; adc_data
L2,K2,K1,J3,H1,H2,H3,G2,G1,F2,E1,E2 = /fpga/D0..D11; usb_rd A15 = RD#; adf_data M2 = /ADF_DATA; pa_en T2, mix_en J4.
The firmware uses the post-swap pins (CLKOUT D13, RD# A15; commits 47dc621, 3306991), so it matches main, not
pre-Nov-2025 boards. Naming differences only: `adf_clk` R1 is an unnamed net via R130; xdc `usb_rxf/txe/rd/oe`
vs schematic `RXF#/TXE#/RD#/OE#`. Schematic FPGA nets absent from the xdc: `/DET_OUT` (C7), `/fpga/PIN1..PIN12`
(commented out in xdc), `/fpga/SPI_CS/MISO/MOSI` (dedicated config pins), PUDC_B net on L15.
Hardware history in the xdc log: adf_data was moved off M2 (burned pin) to B10 then B7 in 5/2026, back to M2 in
82e9b33 (2026-08-02); 0498d51 "mixer might be burned". Relevant to rf-review of ADF4158 DATA and the mixer enable.

## Worth carrying over

1. Firmware ADF4158 PFD of 40 MHz versus the code comment's 32 MHz limit: check against the ADF4158 datasheet
   (goal rf-review).
2. adf_data M2 / mixer "burned" history (82e9b33, 0498d51): look at ESD/protection and enable nets on those
   pins (goal rf-review, layout-review).
3. Pin map, 40 MHz clock and 40 MSPS/decimate-20 numbers from the firmware as the stated design intent for the
   spur study (goal sim-spurs) and clock/ADC checks (rf-review).
4. Retired part ideas in `libs/fmcw3.lib` (e.g. ADL5380, MAX2870, PE42420): only if a later goal reopens part
   choices (goal parts). Nothing needs to be copied now.
5. `oshpark_version`: the OSH Park fab target (6-layer, FR4 er 4.5, same stackup as main). Only relevant if a
   US-fab variant is wanted; no action now.
6. `production/` stays as the record of the 35T order; the current 100T build has no fab package yet (new
   output goes to a new path, per CLAUDE.md).
7. IMU (LSM6DS3H, rescue-backup `imu` sheet): never reached current; carry over only if a later goal wants it.

No legacy file holds a refdes, net or part needed by the current project.

## Safe to delete

"Yes" means fnd-02 may delete or archive it; the content is superseded and, for tracked files, stays in git history.

| path | delete? | reason |
|---|---|---|
| `fmcw3.sch` | yes | 2023 KiCad 5 root sheet, duplicate of `rescue-backup/fmcw3-2023-...sch`, superseded (Legacy files) |
| `fmcw3.net` | yes | identical to a fresh export; regenerable |
| `fmcw3.xml` | yes | 2024 netlist of an older iteration |
| `fmcw3.csv` | yes | 2026-05-24 BOM with DNP lines; superseded by `parts/parts.csv` |
| `fmcw3-cache.lib` | yes | 42 retired symbols; current schematics embed their symbols |
| `fmcw3-rescue.lib` | yes | 13 retired symbols |
| `libs/` (`fmcw3.lib`, `.bak`, `.bck`, `.dcm`) | no | user decision 2026-11-19: keep as the part-ideas reference (item 4) until goal `parts` is done; moves to `kicad/libs/` with the project |
| `rescue-backup/` | yes | 2023 KiCad 5 migration backup, all superseded; in git history |
| `fmcw3-backups/` (25 zips) | yes | the last equals the tree; earlier revisions are in git history. Caveat: only snapshots in git history, so delete only after the user is content with that |
| `production/backups/` | yes | byte-identical copy of `production/` members |
| `production/` (rest) | no | as-ordered 35T fab package; CLAUDE.md forbids regenerating in place |
| `fmcw3.pretty/` | no | current footprint library (16 of 75 used; pruning is a separate decision) |
| `sym-lib-table`, `fp-lib-table` | no | current project config (they hold stale absolute paths; fix separately, not delete) |
| `~_autosave-fmcw3.kicad_pcb.lck` | yes | stray lock file from `lt6232_implement` (see Branches); no content, makes the GUI think the board is open. User decision 2026-11-19: delete |
| `fmcw3.pdf`, `*.plt` | yes | upstream plot exports of an older board state, regenerable from `kicad/`. User decision 2026-11-19: archive to `legacy/` |

### Decisions (user review, 2026-11-19)
- Every kept path needs a stated reason; an old CLAUDE.md rule is not one. The lock file, `fmcw3.pdf` and `*.plt`
  are therefore yes (above).
- `fmcw3-backups/`: deleting is accepted; git history is the record.
- `libs/`: kept until goal `parts` is done, then reconsidered.
- Branches: keep a branch only if it holds work not in `main`. The four merged branches are 0 commits ahead of
  `origin/main`; `oshpark_version` holds 3 commits whose content is in or superseded by `main`.
  The project carries one design, built on the JLCPCB stackup.
