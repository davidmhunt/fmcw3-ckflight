# fnd-01: Survey legacy files, upstream branches and the firmware repo before cleanup
Status: awaiting review
Goal: foundation
Node: any
Deliverable: doc
Accept: user
Verify: test -s docs/surveys/upstream-survey.md && grep -q '^## Legacy files' docs/surveys/upstream-survey.md && grep -q '^## Branches' docs/surveys/upstream-survey.md && grep -q '^## Firmware' docs/surveys/upstream-survey.md && grep -q '^## Safe to delete' docs/surveys/upstream-survey.md
Hardware: none

## Goal
A written survey, `docs/surveys/upstream-survey.md`, that says whether the legacy files and the
other upstream branches hold anything the current KiCad 10 project lacks, and what the firmware
repo tells us about the hardware. It holds when the user can read it and decide that fnd-02 may
delete the legacy files.

## Steps
1. Legacy versus current. Export the component list and netlist of the current project
   (`kicad-cli sch export netlist` and `sch export bom` on `fmcw3.kicad_sch`, output under
   `runs/fnd-01/`). Parse the legacy files (`fmcw3.sch` and its sheets if present, `fmcw3.net`,
   `fmcw3.xml`, `fmcw3.csv`, `fmcw3-cache.lib`, `fmcw3-rescue.lib`, `libs/`, `rescue-backup/`,
   `fmcw3-backups/`, `production/backups/`) and compare refdes, values, footprints and nets.
   Record file dates and KiCad versions. List every difference; say for each whether the current
   project supersedes it.
2. Branches. For each of `origin/jlcpcb_v2`, `origin/jlcpcb_version`, `origin/lt6232_implement`,
   `origin/lt6232_ld3920_33`, `origin/oshpark_version`: `git log`/`git diff` against `origin/main`,
   confirm whether it is merged, and extract what differs: part substitutions, stackup, LCSC
   numbers in BOM files, fab outputs, README text. Read-only: use `git show`/`git worktree` under
   `runs/fnd-01/`, never check a branch out in the main tree.
3. Firmware. Clone `davidmhunt/fmcw3-ckflight-fw` into `runs/fnd-01/fw` (read-only). Record: FPGA
   variants built (35T, 100T), pin constraints (`.xdc`) versus the schematic's FPGA net names with
   any mismatch listed, clock frequencies, ADC sample rate, ADF4158 register/chirp settings.
4. Write `docs/surveys/upstream-survey.md` with sections `## Legacy files`, `## Branches`,
   `## Firmware`, `## Worth carrying over` and `## Safe to delete` (an explicit list of paths with a
   yes/no and reason for each). Each claim names the file, branch or commit it comes from.

## Acceptance
- Every legacy path named in step 1 appears in `## Safe to delete` with yes or no and a reason.
- All five branches have a subsection saying merged or not, and what differs from `main`.
- `## Firmware` states the FPGA variants, the clock and sample-rate numbers with file references,
  and the result of the pin-constraint comparison.
- `## Worth carrying over` lists concrete items (or says none) with where each should go later.
- No file outside `docs/surveys/` is changed.

## Review
- Open `docs/surveys/upstream-survey.md`. Check `## Safe to delete`: fnd-02 deletes or archives
  exactly what is marked yes.
- Read `## Worth carrying over` and say if any item should change the later goals.

## Out of scope
- Deleting, moving or editing any existing file.
- Evaluating upstream's host software repos.

## Allowed commands
- `gh repo clone davidmhunt/fmcw3-ckflight-fw runs/fnd-01/fw*`
- `git worktree add runs/fnd-01/*`

## Log

### 2026-11-19
Commits:
- 718eede Survey: upstream legacy files, branches and firmware (fnd-01 step 4)
Notes:
# fnd-01 step 1: legacy versus current (findings)

Method. Current project exported with kicad-cli 10.0.5 into runs/fnd-01/: cur.net (kicadsexpr netlist),
cur.xml (kicadxml netlist), cur_bom.csv (Reference,Value,Footprint, ungrouped). Current = 382 netlist
components (370 real refs + power flags/symbols), 397 nets. Legacy files parsed with ad-hoc Python (s-expr /
XML / `$Comp` blocks of the v2 .sch files); comparison keyed on refdes, value, footprint, and net
connectivity (set of (ref,pin) per net, name-independent). Scripts were in the session scratchpad.
"Current" below means the working tree at 76be142 (schematics are KiCad 9 format v20250114,
generator_version 9.0; fmcw3.kicad_pcb re-saved KiCad 10, v20260206).

## Dates and KiCad versions (git add/last-change dates; working-tree mtimes are all the checkout time)
| path | first commit | last change | format / tool |
|---|---|---|---|
| fmcw3.sch | 2025-05-01 | 2025-05-01 (00dd3f2) | EESchema Schematic File Version 2 (KiCad 4/5 era); byte-identical to rescue-backup/fmcw3-2023-03-24-11-11-22.sch |
| rescue-backup/*.sch, *.lib | 2025-05-01 | same | timestamps in names 2023-03-24 11:11-11:12 (KiCad 5 rescue/migrate backup); schematic Date fields empty |
| fmcw3-cache.lib | 2025-05-01 | same | EESchema-LIBRARY 2.3; byte-identical to rescue-backup/fmcw3-cache-2023-03-24-11-11-22.lib |
| fmcw3-rescue.lib | 2025-05-01 | same | EESchema-LIBRARY 2.4 |
| libs/fmcw3.lib, .bak, .bck, .dcm | 2025-05-01 | same | LIBRARY 2.3 (.dcm/.bck are 171-byte stubs) |
| fmcw3.xml | 2025-05-01 | same | `<tool>Eeschema 7.0.1-0`, design date 2024-01-13, source /Users/ck/... (macOS) |
| fmcw3.net | 2025-05-01 | 26e19f2 2026-08-04 | `Eeschema 9.0.7`, date 2026-08-04T15:22:22+0300, source /home/ck/... |
| fmcw3.csv | 2025-05-01 | 880901e 2026-05-24 | grouped BOM (Qty,Value,Footprint), 83 rows, 387 parts incl. 44 DNP |
| fmcw3-backups/*.zip (25) | 2026-07-02.. | 26e19f2 2026-08-04 | KiCad 9 projects (sch+pcb+pro+fmcw3.pretty), names 2026-07-02_230843 .. 2026-08-04_152211 |
| production/backups/fmcw3_2026-07-07_20-50-10.zip | 2026-07-04 | 22b23f1 2026-07-07 | fab package: fmcw3.zip, bom.csv, positions.csv, designators.csv, netlist.ipc |
| production/{bom.csv,fmcw3.zip,...} | 2026-07-04 | 22b23f1 2026-07-07 | byte-identical to the 07-07 backup zip (cmp on all 5 members) |

## 1. fmcw3.net (KiCad 9.0.7, 2026-08-04)
Identical to the current export: 382 comps / 397 nets both sides, no refdes, value, footprint, net-name or
connectivity difference. It is just a stale generated file. Superseded: yes (regenerable; cur.net).

## 2. fmcw3-backups/*.zip (25 zips)
Netlist of each zip exported (kicad-cli) and compared with current:
- 2026-08-04_152211 (last): all 11 .kicad_sch byte-identical to the working tree; netlist identical;
  fmcw3.pretty identical; only fmcw3.kicad_pcb differs (KiCad 10 re-save, expected).
- 2026-08-04_135212: differs only in U30 = XC7A35T-1FTG256C (current XC7A100T-1FTG256C).
- 2026-07-03_102910 .. 2026-08-03_152046 (all zips between): refdes set identical to current; differences
  are only U30 (35T vs 100T) and R26/R28/R31/R38 = 500 ohm (current 1k). Connectivity identical.
- 2026-07-02_230843 .. 2026-07-02_233152 (first 5): same refdes; additionally 2..8 net-connectivity groups
  differ (IF1/IF2 jumper wiring JP9-JP12, ADC2+/- R97/R99 swap, L14/L15, Net-(R55-Pad2)/(R56-Pad2)),
  early rework later settled to the current wiring.
- Net: no zip holds a refdes, part or net absent from current except the 35T/500-ohm state, which the
  commit 26e19f2 ("100t changes design is working tested on a real hardware") superseded. Git history also
  holds every one of these revisions of the sch/pcb files (the zips are redundant with git for the
  tracked files). Superseded: yes.

## 3. production/ (bom.csv, designators.csv, positions.csv, netlist.ipc, fmcw3.zip, backups/)
Not legacy KiCad data; it is the as-ordered JLCPCB package (2026-07-07). Its bom.csv has 370 refs, the same
370 as current, with value differences: U30 XC7A35T-1FTG256C (current 100T), R26/R28/R31/R38 500 (current
1k), and case-only differences (4->1K, 18.7K, 3.3K). So the shipped fab package is the 35T build; the current
schematic is the 100T build. Not superseded as a record of what was ordered (CLAUDE.md says do not
regenerate in place). production/backups/ holds one zip that is byte-identical to production/'s members
(redundant copy). Superseded: n/a; backups/ copy redundant: yes.

## 4. fmcw3.xml (Eeschema 7.0.1, 2024-01-13)
400 comps / 395 nets versus 382 / 397. Refs only in the xml (68): C35 C45 C47 C50 C51 C54 C56 C59 C72 C105
C107 C124-C151 C169 C172-C174 C177 C178 C214 C215, L8-L11, P3 P4 P6 P9-P16, Q2, R59-R62 R65-R68 R74-R78
R86 R87 R89 R90 R94 R101 R103 (DNP caps/resistors, the IF-stage network, 2x4 headers and test points,
Q2). Refs only in current (63): C1 C9 C15 C16 C32-C34 C36-C41 C63, D3 D7, J1 J2, JP1-JP12, L12-L15, R3 R8 R14
R18 R19 R25-R31 R38-R42, SW1, U2 U5 U38 U41-U49, Y2 (USB-C J1, jumpers, LT6232 U45 op-amp stage, new
regulator/clock parts).
Value/footprint differences on 41 common refs, notable: U30 XC7A15T (cur 100T); U40 W25Q32JV (cur
W25Q128JV); U34/U35 ADA4940-2 (cur SolderPad placeholders, op-amps moved to LT6232 U45); U4
ECS-TXO-3225MV (cur placeholder/ECS-TXO-32CSMV); U6 NB3N551 (cur PL133-37); U25 BU33SD5WG (cur
LD3920_33); U31 USB-MICRO (cur J1 USB-C); U26-28 5400BL15B050E (cur 5400BL15B0050001E); CON2 fp
fmcw3:EJ508A -> Footprints:BarrelJack; FB11 CIC21P101NE -> MPZ2012S101AT000; SW2 SW_PUSH -> B3U-1000P;
many R/C value retunes (R7 R9 R11 R12 R21 R24 R35 R45-R48 R55-R58 R104 R109, C10 C13 C14 C29).
Net names renamed (3V6->3V8, ADC_CE->ADF_CE, ADC_REF->ADC_CLK, ADF_REF->ADF_CLK_REF, ADC_VCM1/2->ADC_VCMA/B,
FPGA_REF->FPGA_CLK). Current project supersedes all of it (it is an older iteration); nothing in the xml
is absent from the design history except as a record of rejected parts. Superseded: yes.

## 5. fmcw3.sch and rescue-backup/*.sch (2023, KiCad 5 legacy format)
fmcw3.sch = root sheet only (32 comps incl. 12 power symbols; sheets fpga, tx, rx1, rx2 (both rx.sch), power,
mixer, if); sub-sheets exist only in rescue-backup (adc, fpga, if, imu, mixer, power, rx, tx, usb) so
fmcw3.sch cannot be opened standalone with its sheets in place, and is byte-identical to the rescue copy.
Legacy real refs 398 (incl. unannotated C? R? U?) vs current 370. 304 refs in common; values differ on 95 and
footprint package differs on 32 (see below); library prefixes differ (fmcw3:C_0402b vs Footprints:SMD_0402),
so only package size was compared.
Legacy-only refs (not in current): C35 C47 C50 C54 C65-C69 C72 C90-C92 C105 C107 C124-C151 C169 C172-C178 C214
C215 D4 L8-L11 P3 P4 P6 P9-P16 Q1 Q2 R59-R62 R65-R68 R74-R78 R86 R87 R89 R90 R94 R101 R103 and unannotated
C? R? U?. In these, 40 are DNP (value exactly "DNP"); the rest are the legacy IF filter/amp stage (sheet "if": C124-C151,
R59-R94, L8-L11 inductors), D4 (SS13FL), Q1/Q2 (RE1C002UN MOSFET), P3/P4 headers + P6/P9-P16 test points,
imu sheet (LSM6DS3H U? + C?; an IMU that never reached the current design).
Value changes common refs (examples): U30 XC7A15T->XC7A100T, U40 W25Q32JV->W25Q128JV, U17-19 L7980->LMR51420,
U22-24 TPS7A91->LD3920, U25 MIC5301-3.3->LD3920_33, U14 MGA-25203->TQP5525, U12 PAT1220-6dB->3dB,
U6 NB3N551->PL133-37, U4 KT2520K->placeholder, U34/U35 ADA4940-2->placeholder, U2 LP5907-1.8, U5 NC7S04P5X,
U31 USB-MICRO (replaced by J1 USB-C), D2/D3 SS13FL->LED, FB4/FB11, SW2, plus R/C retunes.
Footprint-package changes: pins/placeholders (U2 U4 U5 U6 U14 U17-U19 U22-U25 U31 U34 U35 changed package),
C181 1210, C183.. 0805->0603 caps, D2/D3 SOD-123F->Diode_0603, CON2 EJ508A->BarrelJack, Z1 coupler.
All superseded by the current design (the current project is a later redesign of the same refdes space).
The legacy-only items are retired design content, not missing parts; the IMU and IF-amp sub-circuits
are the only functional blocks present in legacy and absent in current (IF amp replaced by LT6232 opamp_amp).

## 6. Symbol libraries
- sym-lib-table (current) lists 172 Legacy lib entries with absolute paths /home/ck/... (do not exist on this
  machine) and no entry for fmcw3, fmcw3-cache, fmcw3-rescue or libs/fmcw3. The current schematics embed
  all their symbols in lib_symbols (464 of them under prefix `fmcw3-rescue:` inside .kicad_sch; that is the
  embedded rescue namespace, not the file fmcw3-rescue.lib, which has only 13 symbols), so the
  schematics export cleanly without any legacy .lib file.
- fmcw3-cache.lib (42 symbols): not-embedded-by-name in current: 74AHC1G04, ADA4940-2, CONN_02X04,
  D_Schottky, KT2520K, L7981, MGA-25203, MIC5301, MOS_N_GSD, NB3N551, TPS7A91, USB-MICRO (all parts of the
  retired design; same content as rescue-backup cache copy).
- fmcw3-rescue.lib (13): 74AHC1G04, CONN_02X04, D_Schottky not embedded in current.
- libs/fmcw3.lib (96 symbols) / .bak (95): 75 symbols not used by current, including candidate parts never
  placed in the final design: AD7266 AD9269 ADA4932-2 ADA4940-1/-2 ADL5380 ADL5801 HMC313 HMC713LP3E MAX2870
  MAX1426 LPC4320 LPC4370 LT1817 LT6230 LTC6362 LMZ30602 PE42420/23/41 PE43711 FT2232D N25Q032A MCP1700
  MCP1824T MIC5366 AOZ1280/81 AP65201 LSM6DS3H ... A personal symbol library of unused parts; not referenced by
  any current file.
- fmcw3.pretty (75 footprints; identical to the one in the last backup zip) is current and not legacy.
  Only 16 of the 75 footprints are referenced as fmcw3:* by the current board (the rest incl. C_0402b,
  R_0402b, EJ508A, coupler, DFN-8, SOT-23-5L, USB_MICRO, MGA-25203, TFBGA-100 ... are legacy leftovers),
  mentioned only for fnd-02; out of scope to delete here.
- fp-lib-table: fmcw3 ($KIPRJMOD/fmcw3.pretty) plus Footprints at an absolute /home/ck path (missing here).
  Current boards still resolve because footprints are embedded in the .kicad_pcb.

## 7. fmcw3.csv versus current BOM
387 parts vs 370. Present only in the csv: 44 DNP lines (26 x 0402, 8 x 0603, 10 x 0805), ADA4940-2 x2,
XC7A35T, W25Q32JV, NB3N551, BU33SD5WG, ECS-TXO-3225MV, 5400BL15B050E x3, SW_PUSH x2, and RC values since
retuned (16.7, 22, 20.5k, 240, 68k). Only in current: 15x SolderPad_1_Circle placeholders, XC7A100T,
W25Q128JV, PL133-37, LD3920_33, LT6232, ECS-TXO-32CSMV-400, Z1 coupler 15dB, 0 ohm / 5p / 33 / 10k parts,
SMA x3, RF_via x2, M3 mounting x3, Connector_02x08. csv last touched 2026-05-24 (880901e), a pre-DNP-removal
snapshot (546dfd1 2026-06-26 "DNP components are deleted"). Superseded: yes (current BOM: runs/fnd-01/cur_bom.csv
and parts/parts.csv).

## Summary table: does current supersede?
| path | content | superseded by current? |
|---|---|---|
| fmcw3.net | identical to current netlist (2026-08-04) | yes, identical |
| fmcw3.xml | 2024 netlist, 400 comps, 15T FPGA, ADA4940 stage | yes |
| fmcw3.csv | grouped BOM, 2026-05-24, includes DNP | yes |
| fmcw3.sch | KiCad 5 root sheet 2023, 32 comps | yes (root only; same as rescue copy) |
| rescue-backup/*.sch (10) | 2023 sheets incl. IF stage, IMU | yes (IMU, IF-stage retired) |
| fmcw3-cache.lib, rescue-backup cache copy | 42 symbols, byte-identical pair | yes; current embeds symbols |
| fmcw3-rescue.lib | 13 symbols | yes |
| libs/fmcw3.lib/.bak/.bck/.dcm | 96 symbols personal lib, 75 unused | yes for the design; part ideas only |
| fmcw3-backups/*.zip (25) | 07-02..08-04 revisions, last = current sch | yes; content in git history |
| production/backups/*.zip | copy of production/ | redundant copy |
| production/ | as-ordered 35T build | n/a: not legacy; differs from current by 35T->100T and R26/28/31/38 |

# fnd-01 step 2: upstream branches (findings)

Method: `git fetch`, then git log / merge-base / cherry / diff and `git show <ref>:path` only (no checkout, no
worktree needed). "main" = origin/main = a73fbc1 (this fork's history: includes upstream main up to 5fba6a3 plus
our commits cf34c04, b0dbb27, dc25294, a73fbc1). Component comparison parsed from `fmcw3.net` at each tip
(410/410/412/413/397/383/382 comps). No LCSC numbers exist in any branch's schematics, fmcw3.net or fmcw3.csv;
the only LCSC column is the empty `LCSC Part #` in production/bom.csv (jlcpcb_version, and main). Stackup
(copper/dielectric thicknesses, FR4 er 4.5, finish None) is identical in oshpark_version and main.

## Topology
Linear chain, all merged into main (git branch -r --merged origin/main; `rev-list` behind count 0):
a06aa38 "OSH Park version is ready" (2025-08-21, on main history) -> jlcpcb_version 3af22f7 (2026-05-23)
-> jlcpcb_v2 100aed1 (2026-05-26) -> lt6232_implement 256c33f (2026-06-04) -> lt6232_ld3920_33 546dfd1
(2026-06-26, merged in a40af5c) -> main (22b23f1 final order, 26e19f2 100T tested, 5fba6a3 readme).
oshpark_version e39d97a (2025-11-02) is the only unmerged one: 3 commits not in main, main has 64 not in it.

## jlcpcb_version (merged; 35 commits past a06aa38, tip 3af22f7)
Changes vs a06aa38: 50 ohm RF rework (R55-58 550->1k, coupler 0.23mm -> 0.169mm Z1 from CST sim 5bd5c1a,
c366e69), ADL5802 IF pull-ups fix (0f63396), 0.1016 min track/clearance rules, U30 XC7A15T -> XC7A35T,
FB11 CIC21P101NE -> MPZ2012S101AT000, ~29 resistor/cap value changes (R59-62 8.2k->20.5k, R45 2.61k->49.9k,
R84/85/88 33->22, ...), +5 refs (R19,U2,U31,U37,U5), -3 (C13,D4,R26). Fab outputs: production/ (bom.csv with
empty LCSC col, designators, positions, netlist.ipc, fmcw3.zip, backups zip 2026-05-23), fabrication-toolkit-options.json.
Also pulled in the FPGA CLKOUT/RD# pin change (586876e = oshpark 10c91b4 equivalent).

## jlcpcb_v2 (merged; +5 commits, tip 100aed1)
Deleted production/ from tree (removed again later; main has the 2026-07-07 package instead). Added readme.md
(181 lines, XC7A35T, HMC431LP4 VCO, ADL5802, ADA4940, LTC2292, FT2232H; author Cenk Keskin), sym-lib-table.
Parts: U6 NB3N551 (DFN-8) -> PL133-37 (SOT23-6) clock buffer, +Y2 TCXO, +C1, -U4 (880901e "clock buffer and
txco source is changed"); SW1/SW2 SW_PUSH -> B3U-1000P; U26-28 5400BL15B050E -> 5400BL15B0050001E (baluns);
R9/11/12 16.7->16.9; R21/84/85/88 22->33; R109 240->1k.

## lt6232_implement (merged; +10 commits, tip 256c33f)
LT6232 opamp stage (new sheets opamp_amp.kicad_sch, clock.kicad_sch, fpga_config.kicad_sch; if.kicad_sch removed,
fpga.kicad_sch restructured). Comps 413->397: +48/-64 (removed C124-151, L8-L11, P10-P15; added JP1-JP8, J2,
L12-L15, R26/28/29/30/31/38-42, U38, U41, C9/15/16/32-34/36-41/63). U34/U35 ADA4940-2 -> placeholder solder pads
(SolderPad_1_Circle); U40 W25Q32JV -> W25Q128JV; R55-58 1k->0, R63/R64 DNP->0, R104 68k->10k. README +7 images
(unchanged text). Adds ~fmcw3.kicad_*.lck files.

## lt6232_ld3920_33 (merged via a40af5c; +3 commits, tip 546dfd1)
3.3 V regulator upgraded: U25 BU33SD5WG (SOT-23-5) -> LD3920_33 (DFN-6 3x3); Y2 value -> ECS ECS-TXO-32CSMV-400;
C71 DNP -> 10u; 14 DNP refs deleted (C107,C169,C177,C178,C215,C35,C47,C50,C51,C56,C59,C72,R101,R103); copper
pours/vias checked. Comps 397 -> 383. README: only author block changed (Cenk KESKIN, EW title dropped).

## After the branches, on main
R26/28/31/38 500->1k; U30 XC7A35T -> XC7A100T (26e19f2, "tested on real hardware"); +JP9-12; -C45,C54,C105,C172,
C214 (5 DNP caps). main's readme.md differs from the branch only in 7 image URLs.

## oshpark_version (NOT merged; tip e39d97a 2025-11-02)
Merge base a06aa38 ("OSH Park version is ready", 2025-08-21; this commit is on main). 3 commits ahead of
a06aa38 (10c91b4, 3b788b0, e39d97a); git cherry marks all three "+" (no patch-equivalent in main), main has
moved 64 commits. Changes: fpga.kicad_sch + fmcw3.net: CLKOUT U30 A15 -> D13 (IO_L12P_T1_MRCC_15), RD# U30 B14 ->
A15 (B14 becomes NC; "usb clkout pin and one more pin is changed"); fmcw3.kicad_pro zone min_clearance 0.16 -> 0,
adds undefined_netclass=error, drops 1 DRC exclusion; fmcw3.kicad_pcb 3h RF clearance (rf path ground
spacing for 50 ohm microstrip), PDF re-export. No refdes/value/footprint change (410 comps identical to a06aa38).
Stackup unchanged (FR4, 6-layer, 0.0432/0.0175 Cu). Is its content in main? Schematic pin change: YES, main's
fmcw3.net has CLKOUT=U30 D13 and RD#=U30 A15, zone min_clearance 0.0 and undefined_netclass present (arrived via
jlcpcb_version 586876e/720ff8b). The oshpark-specific RF clearance PCB edits: main's pcb has been fully re-routed
(2026-01 onward, 2h spacing 40a98db, vias, 05ad72c), so those are superseded in practice; not diffable
line-by-line (pcb differs by ~40k lines). The oshpark branch is the 2025 OSH Park (US fab, 6-layer) variant with
the 0.23mm coupler / 15T-35T era design; it holds nothing the current project lacks except the OSH Park fab target.
The pcb gr_text on main still says "jlcpcb and oshpark branches are created / Oshpark is ready".
Fab outputs on oshpark_version: none (no production/ dir; only fmcw3.pdf, fmcw3.csv).

## Fab/BOM/README summary
- LCSC numbers: none in any branch (empty column). Part numbers only in the Value field.
- Fab outputs: only jlcpcb_version has production/ (2026-05-23); main has the 2026-07-07 one.
- README: readme.md only in jlcpcb_v2 and later; only image/author changes after jlcpcb_v2.

## Firmware relevance (for step 3)
oshpark/jlcpcb pin swap: CLKOUT=D13 (IO_L12P_T1_MRCC_15), RD#=A15 (IO_L9N_T1_DQS_AD3N_15), B14 now NC. Check the
firmware .xdc uses these, not the pre-Nov-2025 A15/B14.

## Step 3: Firmware (davidmhunt/fmcw3-ckflight-fw, cloned to runs/fnd-01/fw, HEAD cb7f097 "readme update"; 248 commits; remote "upstream" = ckflight/FMCW3)
Repo is a full Vivado 2025.2 project dump (FMCW3.xpr, .cache, .gen, .runs, Vitis workspace FMCW3_Microblaze). Not a clean source tree.
Sources: FMCW3.srcs/sources_1/new/{top_module,adc,control,config,usb_sync}.vhd; MicroBlaze BD FMCW3.srcs/sources_1/bd/microblaze;
app C: FMCW3_Microblaze/FMCW3_App/src/{helloworld,spi,gpio,definitions}.c/.h; one constraint file FMCW3.srcs/constrs_1/new/pinout.xdc.

### FPGA variants
- Two prebuilt outputs at repo root, both committed in 1b354b5 (2026-08-04 "xc7a100t commit"): top_module_xc7a35t.{bit,bin,ltx} and
  top_module_xc7a100t.{bit,bin,ltx} (+ top_module.xsa). Bit headers (strings): 7a35tftg256 built 2026/08/04 15:29:09; 7a100tftg256 built 2026/08/04 15:36:50;
  both Vivado 2025.2.
- The .xpr itself targets xc7a100tftg256-1 only (Part in FMCW3.xpr line 11). There is ONE xdc and NO separate 35T project/constraint set in the repo;
  the 35T bitstream was presumably built by retargeting the part. Package FTG256 is shared, so the same pinout.xdc applies (not verified per-bank for 35T).
- README: jlcpcb_version branch = XC7A35T, main branch = XC7A100T (matches hardware survey: U30 value XC7A100T-1FTG256C on current main schematic).
- README flash command uses --fpga-part xc7a35tftg256; JTAG via FT2232H channel B, M[2:0]=101 JTAG, 001 SPI flash.

### Pin constraints vs current schematic (fmcw3.kicad_sch netlist, runs/fnd-01/cur.net, U30)
All 56 constrained ports checked (script: pin -> net on U30). RESULT: no mismatches; every XDC pin lands on the net whose name matches the port:
 sysclk N11=/FPGA_CLK; usb_clk D13=/fpga/CLKOUT (FT2232H ACBUS5 pin 32); reset_n B4=/fpga/RESET; adf_ce R3=/ADF_CE; adf_txdata P3=/ADF_TXDATA;
 adf_data M2=/ADF_DATA; adf_le N1=/ADF_LE; adf_muxout K3=/ADF_MUXOUT; adc_data[0..11] L2,K2,K1,J3,H1,H2,H3,G2,G1,F2,E1,E2 = /fpga/D0..D11;
 adc_of C2,M1 = OFA,OFB; adc_oe B2,P1 = ADC_OE1/2; adc_shdn B1,N2 = ADC_SHDN1/2; usb_data F15,G16,G15,F14,E16,E15,D16,D15 = FT_D0..D7;
 usb_rxf B16=RXF#; usb_txe B15=TXE#; usb_rd A15=RD#; usb_wr A14=WR; usb_siwua A13=SIWUA; usb_oe A12=OE#; usb_suspend C16=FT_SUSPEND;
 led1 B12=USER_LED; pa_en T2=/PA_EN; mix_en J4=/MIX_ENBL; SD_DATA0-3 N16,M16,R16,R15 / SD_CMD P16 / SD_CLK N14 / SD_CARD_DETECT H16 = /fpga/SD_*.
- The post-Nov-2025 pin swap is in the xdc: usb_clk=D13, usb_rd=A15 (commits 47dc621 2025-10-24 and 3306991 2025-12-17 moved A15->D13 clock and B14->A15 rd).
  Matches schematic CLKOUT=D13, RD#=A15, B14 unconnected. Firmware agrees with current main, not with pre-swap boards.
- Naming differences only (not errors): adf_clk R1 net is the unnamed Net-(U30D-IO_L7N_T1_34) via series R130 to ADF4158 (no /ADF_CLK label);
  schematic names RXF#/TXE#/RD#/OE# vs xdc usb_rxf/usb_txe/usb_rd/usb_oe.
- Schematic FPGA nets NOT in the xdc / top_module ports: /DET_OUT (C7, power detector output, unused by firmware); /fpga/PIN1..PIN12 (ext connector, xdc has them
  commented out); /fpga/SPI_CS,SPI_MISO,SPI_MOSI (L12,J14,J13, config flash, dedicated config pins); one unnamed net on L15 (PUDC_B). The ADC clock
  (/ADC_CLK to U8 CLKA/CLKB) and ADF4158 ref are not FPGA ports (shared 40 MHz source, per xdc comment "Clock is same for fpga, adc and adf ref in").
- Port names in top_module.vhd all have an xdc entry; no xdc entry refers to a non-existent port that I found.
- Hardware history in xdc log: adf_data was moved off M2 (burned pin) to ext pin B10 then B7 (5/2026), then back to M2 in 82e9b33 (2026-08-02), i.e. the
  current xdc assumes a good M2 pin. 0498d51 "mixer might be burned". Worth knowing for review of ADF4158 DATA and ADL5802 enable nets.

### Clocks
- sysclk 40 MHz (xdc create_clock period 25.00 on N11; top_module.vhd comment ECS-TXO 40 MHz; BOM Y2 ECS-TXO-32CSMV-400).
- usb_clk 60 MHz from FT2232H (xdc period 16.667 on D13), sync FIFO 245 mode, ~11 MB/s claimed (README).
- clk_wiz_0 (MMCM, clk_wiz_0.xci): in 40 MHz; VCO = 40*25 = 1000 MHz; CLKOUT1 40 MHz (div 25, logic/ADC capture); CLKOUT2 100 MHz (div 10, MicroBlaze/AXI).
- sysclk path is 40 MHz on both /FPGA_CLK (via R13 33R) and /ADC_CLK (R15, R21 33R to U8 CLKA/CLKB).

### ADC sample rate
- LTC2292 clocked at 40 MHz (adc.vhd: ch1 captured on rising edge, ch2 on falling edge of clk_40mhz; 12-bit two's complement, sign-extended/padded to 16 bit).
  README: 40 MSPS, ~71.3 dB SNR.
- fir_compiler_0 (fir_compiler_0.xci): Decimation, rate 20, sample freq 40.0, clock 40, 1 channel, 16-bit coeffs; coefficient file configured as
  fir_hpf_400khz_gain16.coe (HPF 400 kHz; other coe files in repo: 200/250/350/600 kHz). Output rate 40/20 = 2 MSPS per channel (adc.vhd comment:
  "ADC is still sampled with 40msps but 2msps valid is generated" when FIR disabled). Samples/chirp 500 for a 250 us ramp.
- Config packet has a "sampling_frequency (kHz)" field but ADC rate is fixed in hardware (40 MHz, /20).

### ADF4158 settings (helloworld.c ADF4158_Configure_Sweep; set at runtime from a 24-byte host config packet, not hardcoded)
- FREQ_REF = 40 MHz, FREQ_PFD = FREQ_REF/1 = 40 MHz (R counter = 1, field "1<<15" in R2). Code comment says "max pfd is 32mhz": NOTE the PFD used (40 MHz)
  exceeds the 32 MHz the comment cites; ADF4158 datasheet limit not checked here. Flag for rf-review.
- Config-packet units: start freq = word * 10 MHz; bandwidth = word * 1 MHz; sweep time and delay in us (16-bit BE). Default example in comments: 250 us ramp (also 1 ms in README).
- fres = PFD/2^25; RFout = (N + FRAC/2^25)*PFD; ramp delay word 12-bit with CLK1 divider; steps = rampTime/(CLK1/PFD) (20-bit);
  deviation word 16-bit + offset 0..15.
- Registers written in order R7,R6,R5,R4,R3,R2,R1,R0 (32-bit MSB-first over AXI quad SPI, LE via GPIO[1], CE via GPIO[0]):
  R7: ramp-delay flags 18,17,16,15 set (RAMP DEL FL, RAMP DEL, DEL CLK SEL=PFD*CLK1, DEL enable) | delay word<<3.
  R6: step word<<3.   R5: dev offset<<19 | dev word<<3.
  R4: modulator mode 0; neg bleed 0; READ BACK TO MUX = 3 (bits 22:21); CLK DIV MODE = 3 (bits 20:19, ramp divider); CLK2 = 1.
  R3: ramp mode 0 sawtooth (1<<10 triangular if sweep_type!=0); phase detector polarity bit 6 = 1.
  R2: CSR enable (bit 28); CP current index 14 (bits 27:24); prescaler 8/9 (bit 22); R counter 1; CLK1 divider.
  R1: FRAC LSB.   R0: ramp on (bit 31); MUXOUT/readback control 15 (bits 30:27); INT; FRAC MSB.
- MUXOUT used as ramp-status flag: control.vhd samples ADC while MUXOUT=0 and uploads over USB in the gap (README). adf_txdata unused (driven 0).
- GPIO map (definitions.h): 0 ADF_CE, 1 ADF_LE, 2 sampling done, 3 ramp configured, 4 soft reset, 5 LED, 6 FIR enable, 7 send data type, 8 PA mode, 9 test mux.
- No separate adf4158.h in repo (include commented out); no fixed numeric default chirp (start/BW/time come from the host config).
Verify: Verify passed: test -s docs/surveys/upstream-survey.md && grep -q '^## Legacy files' docs/surveys/upstream-survey.md && grep -q '^## Branches' docs/surveys/upstream-survey.md && grep -q '^## Firmware' docs/surveys/upstream-survey.md && grep -q '^## Safe to delete' docs/surveys/upstream-survey.md
Independent review: no gaps
