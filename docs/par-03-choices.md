# par-03 choices, as made in review (2026-11-23)

The user's choices for the par-03 keys of `parts/choices.json`, recorded as they are made so they
survive until `friday accept par-03 --note ...`. The accept note is the authority; this file is the
working record. "Both" means the 2-RX board (`kicad/`) and the 1-RX board (`kicad-1rx/`).

| Key | Choice | Boards | Applied by | Notes |
|---|---|---|---|---|
| fpga | B: XC7A100T-1FTG256I (JLC C1521781) | both | par-04 (fields) | Same as rx1-fpga A |
| adc | B: LTC2292IUP#PBF | 2-RX | par-04 (fields) | Bought through JLC global sourcing (consigned); ideally one of the only consigned parts. 1-RX uses the AD9237 (rx1-02) |
| usbc | A: USB4105-GF-A (JLC C3020560) | both | par-04 (fields) | The -060/-120 suffixes are only the shell stake length (gct-usb4105-drawing p.1) |
| inductor | APS0650M330A (Coilank, JLC C47327223), a new option | both | par-12 (2-RX), rx1-03 (1-RX) | Footprint change; par-11 load check passed (peak 1.282 A, DC 1.184 A worst case) |
| y2 | B: Epson X1G0054210307 (TG2520SMN 40 MHz clipped sine, JLC C3007519) | both | par-12, rx1-03 | Keeps the 2.5 x 2.0 mm footprint (the ECS part was 3.2 x 2.5 mm). R19 changes from 0 ohm to a 10 nF 0402 DC-cut capacitor (epson-tg2520smn-datasheet p.1) |
| lmr | A: LMR51420YFDDCR (JLC C7296200), 1.1 MHz, fixed frequency (FPWM) | both | par-04 (fields) | As on the schematic. Fixed frequency keeps light-load burst tones out of the IF band; the 1.1 MHz tone sits above the 1 MHz decimated band but inside the 1.26 MHz analog IF response (sim-01 measures its level) |
| tgrade | Per board: 1-RX A PL133-37TC-R (JLC C626278, 0 to 70 C); 2-RX B PL133-37TI-R (-40 to 85 C) | per board | par-04 (fields, per board) | The 2-RX TI-R is consigned in the same JLC sourcing order as the LTC2292 (DigiKey stock 2,245) |

Still open: balun, opamp, ldo, sma, atten, fb4, assembly, library.
