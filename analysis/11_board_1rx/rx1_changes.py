"""rx1-02 step 7: the 1-RX change list and the 1-RX choices, written from the step 2-6 results.

Writes (run: ./run python3 analysis/11_board_1rx/rx1_changes.py):
  parts/rx1_changes.csv  one row per ref or net change; rx1-03 applies it and tests the netlist
                         difference of kicad/ against kicad-1rx/ row by row;
  parts/choices.json     the keys prefixed `rx1-` (the file's other keys are left as they are).

Stock, class and price are read from sim/stock_lines.json (JLC database date inside it), the
DNP list from sim/rx2_dnp.json; nothing about stock is typed here. The datasheet facts are the
ones of runs/rx1-02/notes.md, each with its manifest id and page. Nothing under kicad/ or
kicad-1rx/ is read or written.

Columns of rx1_changes.csv:
  id, kind, refs, group, from, to, status, choice, option, applies_when, cls, evidence, check,
  board_row
  kind          swap | value | dnp | new | net | fields
  status        decided (stated by the directive), proposed (agent; the user accepts at review),
                option (applies only when the user accepts the option named in `option` of the
                choice `choice`; `option` holds the recommended one)
  applies_when  empty, or a condition on another choice (the row is dropped when it is false)
  cls           drop-in | footprint change | design change | netlist only
  board_row     the Ref cell of the docs/board-changes.md row (Board 1-RX) that names the check
"""
from __future__ import annotations

import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STOCK = HERE / "sim" / "stock_lines.json"
RX2 = HERE / "sim" / "rx2_dnp.json"
CSV_OUT = ROOT / "parts" / "rx1_changes.csv"
CHOICES = ROOT / "parts" / "choices.json"

COLS = ["id", "kind", "refs", "group", "from", "to", "status", "choice", "option", "applies_when",
        "cls", "evidence", "check", "board_row"]

# Ref cells of the docs/board-changes.md rows (Board 1-RX) the changes belong to.
R_U8 = "U8 (ADC), 1-RX"
R_STRAP = "U8 straps and the VCMB bias divider, 1-RX (R91, R92, R93, R990, R991, R992)"
R_REF = "U8 reference, VREF and supply caps, 1-RX (C217, C218, C220, C992, C993, C994, C995)"
R_DNP = "Receive chain 2 not fitted, 1-RX"
R_VCM = "U45 unused pair and /ADC_VCMA, 1-RX"
R_FPGA = "U30 (FPGA), 1-RX"
R_BALUN = "U26, U27 (baluns), 1-RX"
R_OPAMP = "U45 (op-amp), 1-RX"
R_LDO = "U21 (LDO), 1-RX"
R_SMA = "P1, U15 (SMA), 1-RX"
R_IND = "L5-L7 (inductor), 1-RX"
R_ATT = "U3, U12 (attenuators), 1-RX"
R_LED = "D1-D3, D5-D7 (LEDs), 1-RX"
R_CON = "CON2, J2 (barrel jack, header), 1-RX"
R_USB = "U33 (USB bridge), 1-RX"
R_SEQ = "U24, U23 enables from 3V0 (rail order), 1-RX"
BOARD_ROWS = [R_U8, R_STRAP, R_REF, R_DNP, R_VCM, R_FPGA, R_BALUN, R_OPAMP, R_LDO, R_SMA, R_IND,
              R_ATT, R_LED, R_CON, R_USB]

AD = "adi-ad9237-datasheet"
SIM = "adc_input_sim.py (sim/adc_input.json)"

# The receive-chain-2 groups (runs/rx1-02/notes.md step 4), by ref.
DNP_GROUPS = {
    "RF front end (rx sheet)": ["P2", "U16", "U13", "C57", "C55", "C52", "C53", "C206", "C213", "C58",
                                "L3", "L4", "FB7", "FB8", "R23"],
    "Mixer RF input (balun on /RF2)": ["U28", "C113", "C114"],
    "IF filter and op-amp, channel 1 (opamp_amp)": ["R55", "R56", "L14", "L15", "C36", "C37", "C38",
                                                    "R31", "R38", "R63", "R64", "U31", "U34", "U48",
                                                    "U49"],
    "ADC input network, channel B (adc)": ["R98", "R100", "C166", "C167", "C168"],
    "U8 channel-B reference and sense parts (go with the U8 swap)": ["R20", "C19", "C20", "C22", "C23"],
}

# One entry per line with a stock failure (key of sim/stock_lines.json "options"): the recommended
# option (JLC-stocked, least layout work, a datasheet on file), the choice key, the board row, and
# the per-ref rows.
LINES = {
    "U30": dict(choice="rx1-fpga", rec="A", row=R_FPGA, refs=["U30"], title="FPGA U30",
                frm="XC7A100T-1FTG256C",
                note="drop-in: value C to I; par-03 choice 1 pin check (same 256 balls)"),
    "U26": dict(choice="rx1-balun", rec="A", row=R_BALUN, refs=["U26", "U27"], title="Baluns U26, U27",
                frm="5400BL15B0050001E", note="U28 is receive chain 2 and is not fitted"),
    "U45": dict(choice="rx1-opamp", rec="B", row=R_OPAMP, refs=["U45"], title="Op-amp U45",
                frm="LT6232IGN#PBF",
                note="only amps A and B are used in 1-RX; SSOP-16 becomes SO-8"),
    "U21": dict(choice="rx1-ldo", rec="B", row=R_LDO, refs=["U21"], title="LDO U21 (10 V)",
                frm="LP2985A-10DBVR", note="pin 4 BYPASS becomes FB; two divider resistors added"),
    "P1": dict(choice="rx1-sma", rec="", row=R_SMA, refs=["P1", "U15"], title="SMA P1, U15",
               frm="CONSMA003.062", note="no option recommended: see the choice"),
    "L5": dict(choice="rx1-inductor", rec="A", row=R_IND, refs=["L5", "L6", "L7"],
               title="Inductors L5-L7", frm="SRR6040A-330M", note="33 uH, the LMR51420 current limit"),
    "U3": dict(choice="rx1-atten", rec="A", row=R_ATT, refs=["U3"], title="Attenuator U3",
               frm="PAT1220-6dB (no MPN)", note="fields only: the match is the user's to accept"),
    "U12": dict(choice="rx1-atten", rec="A", row=R_ATT, refs=["U12"], title="Attenuator U12",
                frm="PAT1220-3dB (no MPN)", note="fields only; JLC stock is 5 for a need of 3"),
    "D1": dict(choice="rx1-led", rec="A", row=R_LED, refs=["D1", "D2", "D3", "D5", "D6", "D7"],
               title="LEDs D1-D3, D5-D7", frm="LED (no MPN)", note="red; the colour is the user's"),
    "CON2": dict(choice="rx1-conn", rec="A", row=R_CON, refs=["CON2"], title="Barrel jack CON2",
                 frm="BARREL_JACK (no MPN)", note="through-hole"),
    "J2": dict(choice="rx1-conn", rec="A", row=R_CON, refs=["J2"], title="Header J2",
               frm="Connector_02x08 (no MPN)", note="2.54 mm part on 2.5 mm pads"),
    "U29": dict(choice="rx1-mixer", rec="A", row="", refs=["U29"], title="Mixer U29",
                frm="ADL5802ACPZ-R7", note="no change; JLC stock equals the need"),
}


def cite(cites) -> str:
    return "; ".join(f"{i} p.{p}" if p else i for i, p in cites)


def stock() -> dict:
    return json.loads(STOCK.read_text())


def rx2() -> dict:
    return json.loads(RX2.read_text())


def changes() -> list[dict]:
    st, rx = stock(), rx2()
    rows: list[dict] = []

    def add(**kw):
        r = {c: "" for c in COLS}
        r.update(kw)
        rows.append(r)

    # --- the ADC ---------------------------------------------------------------------------------
    add(kind="swap", refs="U8", group="adc", **{"from": "LTC2292 (QFN-64)"},
        to="AD9237BCPZ-40 C514275 (LFCSP-32, 5x5 mm)", status="decided", cls="footprint change",
        evidence=f"{AD} p.8 (Table 6 pin map); p.3 (Table 1)",
        check=f"{SIM}: swing, common mode, settling, IF response; adc_numbers.py: 3V0 load, SNR",
        board_row=R_U8)
    add(kind="net", refs="R93", group="adc", **{"from": "SENSEA strap to 3V0 (2 V span)"},
        to="SENSE (pin 23) strapped to GND: VREF 1.0 V, 2 V p-p, the same span as today",
        status="proposed", cls="netlist only", evidence=f"{AD} p.18 (Table 7); p.3 (Table 1)",
        check="pin map and span arithmetic (pin_map.csv); the span is the one the simulation uses",
        board_row=R_STRAP)
    add(kind="net", refs="U8", group="adc", **{"from": "no MODE2 pin (LTC2292)"},
        to="MODE2 (pin 1) to GND: span factor 2, power scaling off; GC (pin 5) to GND: no gray code",
        status="proposed", cls="netlist only", evidence=f"{AD} p.20 (Table 8); p.21 (GC); p.8 (Table 6)",
        check="pin map table (pin_map.csv); static strap, no simulation needed", board_row=R_STRAP)
    add(kind="value", refs="R91;R92", group="adc", **{"from": "MODE divider 4.7k / 10k on 3V0"},
        to="R91 5.1k (C25905, Basic) / R92 12k (C25752, Basic): MODE (pin 22) at 0.668 AVDD, on the 2/3 AVDD "
           "row (twos complement, DCS on); both values already on the 1-RX BOM (R3, R8; R37, R71)",
        status="decided", choice="rx1-mode", option="C", cls="value only",
        evidence=f"{AD} p.21 (Table 10); p.10 (Figure 5, 70 kohm pull-down)",
        check="hand calculation with the 70 kohm pull-down: 4.7k/10k 0.651 AVDD (A), 4.7k/11k 0.669 (B, 11k is "
              "Extended C25749), 5.1k/12k 0.668 (C, chosen by the user 2026-11-25)",
        board_row=R_STRAP)
    add(kind="new", refs="R990", group="adc", **{"from": ""},
        to="1.0 kohm 0402, 3V0 to /ADC_VCMB (1.5 V bias divider, top)", status="proposed",
        cls="netlist only", evidence="adi-lt6232-datasheet p.3 (IB 5 uA typ, 10 uA max); "
                                     f"{AD} p.17 (VCM range 0.5 to 2.0 V)",
        check=f"{SIM}: bias node 1.495 V, pin CM 1.545 V", board_row=R_STRAP)
    add(kind="new", refs="R991", group="adc", **{"from": ""},
        to="1.0 kohm 0402, /ADC_VCMB to GND (1.5 V bias divider, bottom)", status="proposed",
        cls="netlist only", evidence="adi-lt6232-datasheet p.3; adi-lt6232-datasheet p.5 (11 uA max over temperature)",
        check=f"{SIM}", board_row=R_STRAP)
    add(kind="net", refs="C30;C31;C41", group="adc", **{"from": "decoupling of the LTC2292 VCMB output"},
        to="kept on /ADC_VCMB as the divider's decoupling (100n, 2.2u, 100n)", status="proposed",
        cls="netlist only", evidence="adi-lt6232-datasheet p.3", check=f"{SIM}: 130 Hz corner with 500 ohm",
        board_row=R_STRAP)
    for ref, frm, to, why in (
            ("C217", "1u (REFHA)", "100n REFT (pin 26) to AGND", "p.18 Figure 39"),
            ("C218", "1u (REFLA)", "100n REFB (pin 25) to AGND", "p.18 Figure 39"),
            ("C220", "2.2u REFHA-REFLA", "10u REFT to REFB", "p.18 (0.1 uF and 10 uF between REFT and REFB); p.8 Table 6")):
        add(kind="value", refs=ref, group="adc", **{"from": frm}, to=to, status="proposed", cls="netlist only",
            evidence=f"{AD} {why}", check="datasheet values; no simulation needed", board_row=R_REF)
    add(kind="net", refs="C221", group="adc", **{"from": "100n REFHA-REFLA"},
        to="kept: 100n REFT to REFB", status="proposed", cls="netlist only", evidence=f"{AD} p.18",
        check="datasheet values", board_row=R_REF)
    add(kind="new", refs="C992", group="adc", **{"from": ""}, to="100n 0402, VREF (pin 24) to AGND",
        status="proposed", cls="netlist only", evidence=f"{AD} p.18 (Figure 39); p.19 (2 mA reference load)",
        check="datasheet values", board_row=R_REF)
    add(kind="new", refs="C993", group="adc", **{"from": ""}, to="10u 0805 (C15850, Basic, the board's 10u part), VREF (pin 24) to AGND",
        status="decided", cls="netlist only", evidence=f"{AD} p.18 (Figure 39)",
        check="datasheet values; 0805 chosen by the user 2026-11-25 (rx1-02 review); fits on the "
              "bottom side behind the pin, outside the exposed-pad via field (cap_space.py 2026-11-25, AD9237 pins 25-32 facing the input network)",
        board_row=R_REF)
    add(kind="net", refs="C24;C27;C223;C224;C222;C249", group="adc",
        **{"from": "LTC2292 VDD 7, 10, 18, 63 (/fpga/adc/3V0): 4 x 100n, 2 x 1u"},
        to="kept on AVDD (pins 27, 32): the 100n per supply pin group the datasheet asks for",
        status="proposed", cls="netlist only", evidence=f"{AD} p.8 (Table 6)",
        check="kicad/ netlist (analysis/11_board_1rx/supply_decoupling.py): these six are the only caps "
              "on the net; all within 10 mm of U8", board_row=R_REF)
    add(kind="new", refs="C994", group="adc", **{"from": ""},
        to="10u 0805 (C15850, Basic, the board's 10u part), 3V0 (AVDD, pins 27 and 32) to AGND; the net has no 10u today",
        status="decided", cls="netlist only", evidence=f"{AD} p.8 (Table 6: 0.1 uF with 10 uF recommended)",
        check="kicad/ netlist: 3V0 has 100n and 1u only; datasheet values, no simulation needed; 0805 chosen by "
              "the user 2026-11-25; fits on the bottom side behind the pin, outside the exposed-pad via field (cap_space.py 2026-11-25, AD9237 pins 25-32 facing the input network); placement is the user's", board_row=R_REF)
    add(kind="net", refs="C25;C225;C252", group="adc",
        **{"from": "LTC2292 OVDD 32, 49 (/3V3D, shared rail)"},
        to="kept on DRVDD (pin 16): 100n, the three nearest 3V3D caps (5.9 to 10.9 mm from U8)",
        status="proposed", cls="netlist only", evidence=f"{AD} p.8 (Table 6)",
        check="kicad/ netlist and kicad_pcb positions (supply_decoupling.py); 3V3D is shared with the FPGA",
        board_row=R_REF)
    add(kind="new", refs="C995", group="adc", **{"from": ""},
        to="10u 0805 (C15850, Basic, the board's 10u part), 3V3D (DRVDD, pin 16) to GND; the nearest 10u on 3V3D "
           "today is C106, 32 mm from U8",
        status="decided", cls="netlist only", evidence=f"{AD} p.8 (Table 6: 0.1 uF with 10 uF recommended)",
        check="kicad/ netlist and kicad_pcb positions (supply_decoupling.py); datasheet values; 0805 chosen by the "
              "user 2026-11-25; fits on the bottom side behind the pin, outside the exposed-pad via field (cap_space.py 2026-11-25, AD9237 pins 25-32 facing the input network), beside C25, clear of the data lines to the FPGA; "
              "placement is the user's", board_row=R_REF)
    for net, pin in (("/fpga/OFB", "M1"), ("/fpga/ADC_OE2", "P1"), ("/fpga/ADC_SHDN2", "N2")):
        add(kind="net", refs=net, group="fpga", **{"from": f"U8 channel B to U30.{pin}"},
            to=f"no source: U30.{pin} is freed", status="decided", cls="netlist only",
            evidence="rx2_dnp.py (kicad/ netlist); pinout.xdc of the firmware at cb7f097 (read only)",
            check="tests/test_rx1_rx2_dnp.py (three pins freed, no other U30 pin on a removed part)",
            board_row=R_DNP)
    add(kind="net", refs="R21", group="adc", **{"from": "Net-(U8-MUX), already not fitted"},
        to="stays not fitted: the AD9237 has no MUX pin", status="proposed", cls="netlist only",
        evidence=f"{AD} p.8 (Table 6)", check="pin map table (pin_map.csv)", board_row=R_U8)

    # --- receive chain 2 -----------------------------------------------------------------------
    gone = set(st["removed_refs"]) - {"U8"}
    listed = {r for g in DNP_GROUPS.values() for r in g}
    if gone != listed:
        raise SystemExit(f"rx1_changes.py: DNP groups differ from sim/stock_lines.json removed_refs: "
                         f"{sorted(gone ^ listed)}")
    for grp, refs in DNP_GROUPS.items():
        for ref in refs:
            v = rx["values"].get(ref, ["", ""])
            add(kind="dnp", refs=ref, group=grp, **{"from": f"{v[0]} {v[1]}".strip()}, to="not fitted (DNP)",
                status="decided", cls="netlist only",
                evidence="rx2_dnp.py netlist walk; adi-adl5802-datasheet p.6 (Table 3: channel pairing)",
                check="tests/test_rx1_rx2_dnp.py: no shared part removed, no U30 pin on a removed part",
                board_row=R_DNP)
    add(kind="net", refs="/ADC_VCMA", group="opamp_amp", **{"from": "LTC2292 VCMA output to U45 pins 12, 14"},
        to="merged into /ADC_VCMB so the unused U45 amps C and D are unity followers on the bias "
           "(R39, R40, C39, C40 stay fitted)",
        status="option", choice="rx1-unused-amps", option="A", applies_when="rx1-opamp != B",
        cls="netlist only", evidence="adi-lt6232-datasheet p.3 (input range 1.15 to 2.65 V at 3.3 V)",
        check="rx2_dnp.py vcm section; not simulated (a follower on a quiet node)", board_row=R_VCM)

    # --- stock-only substitutions ------------------------------------------------------------------
    for key, meta in LINES.items():
        ent = st["options"][key]
        opts = {o["id"]: o for o in ent["options"]}
        rec = opts.get(meta["rec"])
        if key == "U29":
            continue
        for ref in meta["refs"]:
            if rec is None:
                add(kind="swap", refs=ref, group=meta["title"], **{"from": meta["frm"]},
                    to="undecided: see the choice", status="option", choice=meta["choice"], option="",
                    cls="", evidence=cite([c for o in ent["options"] for c in o["cites"]]) or "none on file",
                    check="; ".join(sorted({o["check"] for o in ent["options"]}))[:300],
                    board_row=meta["row"])
                continue
            kind = "fields" if meta["frm"].endswith("(no MPN)") and rec["cls"] == "drop-in" else "swap"
            add(kind=kind, refs=ref, group=meta["title"], **{"from": meta["frm"]},
                to=f"{rec['label']} {rec['lcsc']}", status="option", choice=meta["choice"],
                option=rec["id"], cls=rec["cls"], evidence=cite(rec["cites"]) or "none on file",
                check=rec["check"], board_row=meta["row"])
    for ref, frm in (("R39", "10k feedback"), ("R40", "10k feedback"), ("C39", "5p across feedback"),
                     ("C40", "5p across feedback")):
        add(kind="dnp", refs=ref, group="U45 amps C and D (unused pair)", **{"from": frm},
            to="not fitted: the LT6231 replaces the quad, amps C and D are gone", status="option",
            choice="rx1-opamp", option="B", applies_when="rx1-opamp == B", cls="netlist only",
            evidence="adi-lt6232-datasheet p.2 (pinout)", check="stock_lines.py option B; SIM covers amps A and B",
            board_row=R_OPAMP)
    # LDO divider resistors (design change B)
    tps = st["ldo_check"]["tps7a2401"]["best"][0]
    add(kind="new", refs="R994", group="LDO U21 (10 V)", **{"from": ""},
        to=f"FB divider top, {tps['r_top'] / 1e6:g} M {tps['top_lcsc']} (10 V from VFB 1.24 V)",
        status="option", choice="rx1-ldo", option="B", cls="design change",
        evidence="ti-tps7a24-datasheet p.14 (Eq. 2, Eq. 3); ti-tps7a24-datasheet p.6 (VFB 1.24 V)",
        check="ldo_check in sim/stock_lines.json: 10.04 V nominal, 9.71 to 10.39 V worst case; "
              "noise is not simulated (sim-01 / sim-spurs)", board_row=R_LDO)
    add(kind="new", refs="R995", group="LDO U21 (10 V)", **{"from": ""},
        to=f"FB divider bottom, {tps['r_bottom'] / 1e3:g} k {tps['bottom_lcsc']}",
        status="option", choice="rx1-ldo", option="B", cls="design change",
        evidence="ti-tps7a24-datasheet p.14 (Eq. 2); ti-tps7a24-datasheet p.6", check="as R994",
        board_row=R_LDO)
    # PDWN series resistor (rx1-pdwn B, the user 2026-11-25), last so the earlier ids keep their numbers
    add(kind="new", refs="R992", group="adc", **{"from": "/fpga/ADC_SHDN1 straight from U30.B1 to the PDWN pin"},
        to="10k 0402 (C25744, Basic, already on the BOM) in series between U30.B1 and PDWN (pin 4), next to U8",
        status="decided", choice="rx1-pdwn", option="B", cls="netlist only",
        evidence=f"{AD} p.7 (PDWN abs max AVDD + 0.3 V), p.20 (Table 9); amd-ug470-7series-config p.22 "
                 "(Table 2-4: PUDC_B Low enables the SelectIO pull-ups after power-up and during configuration), "
                 "p.81; amd-ds181-artix7-datasheet p.3 (IRPU 90 to 330 uA at VCCO 3.3 V)",
        check="netlist: PUDC_B (U30.L15) to GND through R70, R69 not fitted, bank 35 VCCO = 3V3D; a push-pull 3.3 V "
              "high into an unpowered AVDD is held to 0.33 mA; chosen by the user 2026-11-25 (B over tying PDWN to "
              "AGND, to keep firmware power-down); space: cap_space.py search, 0402 fits on the bottom side behind "
              "pin 4 or on the top 1.7 mm from it; placement is the user's",
        board_row=R_STRAP)
    # /ADC_VCMA leftovers (rx1-vcma C, the user 2026-11-25), last so the earlier ids keep their numbers
    add(kind="net", refs="C63;C216;C219", group="adc",
        **{"from": "/ADC_VCMA decoupling: C63 100n, C216 2.2u, C219 100n (LTC2292 VCMA pin 61 to U45 pins 12, 14)"},
        to="removed from the 1-RX schematic and board together with the /ADC_VCMA net: no source or load is left "
           "once U8 is the AD9237 (no VCM pin) and U45 the LT6231 (no pins 12, 14)",
        status="decided", choice="rx1-vcma", option="C", applies_when="rx1-opamp == B", cls="netlist only",
        evidence=f"{AD} p.8 (Table 6, no VCM pin); adi-lt6232-datasheet p.2 (LT6231 SO-8 pinout)",
        check="kicad-1rx/ board: C63, C216, C219 are the only pads on /ADC_VCMA besides U8.61 and U45.12/14; "
              "rx1-unused-amps does not apply (rx1-opamp B); chosen by the user 2026-11-25",
        board_row=R_VCM)
    # Rail order by design (the user 2026-11-25), last so the earlier ids keep their numbers
    add(kind="net", refs="U24", group="power", **{"from": "U24 (LD39200, 3V3A) EN on /3V8"},
        to="U24 EN on /fpga/adc/3V0 (U39 out): 3V3A (U45, U1) cannot start before 3V0 passes the EN threshold",
        status="decided", choice="rx1-seq", option="A", cls="netlist only",
        evidence="ti-lp5907-datasheet p.6 (turn-on 80 typ, 150 max us); st-ld39200-datasheet p.7 (EN high 1.2 V, low 0.5 V, 10 nA); " f"{AD} p.7 (VIN abs max AVDD + 0.3 V)",
        check="rx1-05 simulates the sequenced start-up and power-down; lay-03 1-RX bring-up scopes the order; "
              "chosen by the user 2026-11-25", board_row=R_SEQ)
    add(kind="net", refs="U23", group="power", **{"from": "U23 (LD39200, 1V8) EN on /3V8"},
        to="U23 EN on /fpga/adc/3V0: 1V8 and then 3V3D (U25 EN from U23 PG, unchanged) start after 3V0, so U6 "
           "(clock to CLK), Y2 and the FPGA pins on PDWN and OE come up after the ADC supply",
        status="decided", choice="rx1-seq", option="A", cls="netlist only",
        evidence="ti-lp5907-datasheet p.6 (turn-on 80 typ, 150 max us); st-ld39200-datasheet p.7 (EN high 1.2 V, low 0.5 V, 10 nA); amd-ds181-artix7-datasheet p.8 (power-on order VCCINT, VCCBRAM, VCCAUX, VCCO; "
                 "1V0 is a buck from 12 V and still comes first)" f"; {AD} p.7 (CLK, PDWN abs max AVDD + 0.3 V), "
                 "p.10 (Figure 7: CLK clamp diodes at the pin, ahead of 375 ohm)",
        check="rx1-05 simulates it with the CLK case; the FPGA order stays as DS181 recommends; the FPGA rails now "
              "need U39 working; chosen by the user 2026-11-25", board_row=R_SEQ)
    for i, r in enumerate(rows, 1):
        r["id"] = f"rx1-{i:03d}"
    return rows


# ---------------------------------------------------------------------------------------------
# choices (parts/choices.json, keys prefixed rx1-)

CH_COLS = ["Option", "JLC (C number, stock for the need, USD each)", "Class", "Check and datasheet"]


def option_rows(key: str, st: dict) -> list[list[str]]:
    ent = st["options"][key]
    out = []
    for o in ent["options"]:
        price = f"{o['price']:g}" if o["price"] is not None else "-"
        tag = "ok" if o["jlc_ok"] else "short"
        out.append([f"{o['id']}. {o['label']}", f"{o['lcsc']}, stock {o['stock']} for {o['need']} ({tag}), {price}",
                    o["cls"], f"{o['check']} [{cite(o['cites']) or 'no datasheet on file'}]"])
    return out


def choices() -> dict:
    st = stock()
    date = st["jlc_database_date"]
    lay = st["layout"]
    c: dict[str, dict] = {}

    def stock_choice(key, title, refs, lines, consequence, recommendation):
        rows = []
        for ln in lines:
            rows += option_rows(ln, st)
        c[key] = dict(title=title, refs=refs, cols=CH_COLS, rows=rows, consequence=consequence,
                      recommendation=recommendation)

    stock_choice("rx1-fpga", "1-RX choice: FPGA U30 (JLC has the I grade only)", "U30", ["U30"],
                 f"JLC database {date}. The C grade has no JLC row; the I grade is the same die and 256 balls "
                 "(par-03 choice 1 pin check), value C to I, so it is a drop-in.",
                 "A, XC7A100T-1FTG256I: JLC stock 59 for 3; B costs more and has less stock.")
    stock_choice("rx1-balun", "1-RX choice: baluns U26, U27 (U28 is receive chain 2)", "U26,U27", ["U26"],
                 "The only JLC-stocked balun on file is the TDK HHM1907B1: 0402 four-terminal against the 0805 "
                 "five-terminal part, so a footprint change. Amplitude balance 2.5 dB against 2 dB; no TDK "
                 "S-parameter file is on file, so no simulation covers it (rf-01 uses the Johanson file).",
                 "A is the only JLC-stocked option; the RF effect is not simulated.")
    stock_choice("rx1-opamp", "1-RX choice: op-amp U45 (JLC lists the C grade only)", "U45", ["U45"],
                 "The 1-RX chain uses amps A and B only, so one LT6231 (dual, SO-8) replaces the quad. The step 3 "
                 "LTspice run already uses the LT6231 subcircuit, so swing, common mode, settling and IF response "
                 "apply unchanged. C grade is 0 to 70 C. The LT6232CGN has stock 2 for a need of 3. If A is "
                 "chosen, U45 amps C and D need the rx1-unused-amps choice.",
                 "B, LT6231CS8#TRPBF: JLC stock 54; footprint change SSOP-16 to SO-8; the unused pair and the "
                 "/ADC_VCMA merge disappear.")
    stock_choice("rx1-ldo", "1-RX choice: LDO U21, 10 V output (LP2985A-10 not in JLC stock)", "U21", ["U21"],
                 "Design change: pin 4 BYPASS becomes FB, two divider resistors; for 10 V, R994 1.15 M / R995 "
                 "162 k gives 10.04 V (9.71 to 10.39 V worst case). Output noise is not covered by any "
                 "simulation: 300 uVrms at 1.24 V scales to about 2.4 mVrms unfiltered, against 30 uVrms for the "
                 "LP2985; the 10 V rail feeds U7 (sim-01, sim-spurs).",
                 "B, TPS7A2401DBVR (stock 10425); C is the alternative; neither noise figure is simulated.")
    stock_choice("rx1-sma", "1-RX choice: SMA connectors P1, U15 (P2 is receive chain 2)", "P1,U15", ["P1"],
                 "A is a vertical, screw-on SMA (6.5 mm square body, through-board pin): a design change to the "
                 "cable direction and board edge. B is an edge-mount SMD jack like today's, but its datasheet is "
                 "not on file (docs/user-fetch.md row amphenol-132134-datasheet), so nothing is claimed about it.",
                 "none recommended: if you save the Amphenol datasheet, B is the like-for-like part; else A is "
                 "the only option with a datasheet on file.")
    stock_choice("rx1-inductor", "1-RX choice: inductors L5-L7 (33 uH, LMR51420 current limit)", "L5,L6,L7",
                 ["L5"],
                 "Only the APS1040M330A has Isat (5.05 A) near the LMR51420 high-side limit (3.5 A typ, 5.1 A max, "
                 "ti-lmr51420-datasheet p.5; p.18: Isat above the limit). SMS0650 and FCH0650 clear the 2 A "
                 "full-load peak only and their ratings are listing figures. The par-09 options saturate near 1 A.",
                 "A, APS1040M330A (11.5 x 10 mm footprint change, board room to check).")
    stock_choice("rx1-atten", "1-RX choice: attenuators U3 and U12 (PAT1220, no MPN in the schematic)", "U3,U12",
                 ["U3", "U12"],
                 "Same Susumu PAT1220 0805 part; the maker's table says DC to 10 GHz where the JLC text says 0-3 "
                 "GHz. U12 has JLC stock 5 for a need of 3: order at once. PAT0816 is a 0603 footprint change at 64 mW.",
                 "A for both (drop-in; fields only).")
    stock_choice("rx1-led", "1-RX choice: LEDs D1-D3, D5-D7 (colour)", "D1,D2,D3,D5,D6,D7", ["D1"],
                 "Red is a drop-in; white, green and blue (Vf up to 3.1 V) need the series resistors re-sized.",
                 "A, red; the colour is yours.")
    stock_choice("rx1-conn", "1-RX choice: barrel jack CON2 and header J2 (through-hole)", "CON2,J2",
                 ["CON2", "J2"],
                 "Both are footprint changes (J2: 2.54 mm part on 2.5 mm pads). Whether JLC places through-hole "
                 "parts for this order is for you to confirm in the order tool.",
                 "A for both (stock 74631 and 17000).")
    stock_choice("rx1-mixer", "1-RX choice: mixer U29 (JLC stock equals the need)", "U29", ["U29"],
                 "Stock 3 for a need of 3 passes with no spare; the stock must be re-read on the day of the order. "
                 "The ADL5801 is a single mixer but its datasheet is not in the manifest, so nothing is claimed.",
                 "A, order at once.")
    c["rx1-mode"] = dict(
        title="1-RX choice: MODE strap R91 / R92", refs="R91;R92", cols=["Option", "MODE level", "Class", "Note"],
        rows=[["A. keep R91 4.7k / R92 10k", "1.95 V = 0.651 AVDD (with the 70 kohm pull-down)", "netlist only",
               "2.5 percent below the 2/3 AVDD row; the datasheet gives nominal levels only"],
              ["B. R92 = 11k", "0.669 AVDD", "value change", "11k 0402 is a JLC Extended part (C25749), a new BOM line"],
              ["C. R91 5.1k / R92 12k", "0.668 AVDD", "value change",
               "both JLC Basic and already on the 1-RX BOM (C25905, C25752)"]],
        consequence="adi-ad9237-datasheet p.21 (Table 10: 2/3 AVDD is twos complement, DCS on) and p.10 (Figure 5, "
                    "70 kohm pull-down). The firmware reads signed twos complement (adc.vhd).",
        recommendation="C, chosen by the user 2026-11-25: on the nominal level with no new BOM line.")
    c["rx1-pdwn"] = dict(
        title="1-RX choice: AD9237 PDWN from the FPGA (abs max AVDD + 0.3 V)", refs="R992",
        cols=["Option", "Change", "Cost", "Effect"],
        rows=[["A. as is, firmware rule", "none", "none",
               "pull-ups (90-330 uA) take PDWN to 3V3D in every configuration; a driven high sits at the limit"],
              ["B. R992 10k in series", "one 0402, C25744 (on the BOM)", "one part to place",
               "clamp current held to 0.33 mA in every case; firmware power-down kept"],
              ["C. PDWN to AGND", "net change, U30.B1 freed", "none",
               "no exposure; ADC always on (as today); no firmware power-down"]],
        consequence="adi-ad9237-datasheet p.7 and p.20 (Table 9); amd-ug470-7series-config p.22 (PUDC_B) and p.81; "
                    "amd-ds181-artix7-datasheet p.3 (IRPU). PUDC_B is tied to GND by R70 (R69 not fitted).",
        recommendation="B, chosen by the user 2026-11-25 (keeps power-down; fits, cap_space.py search).")
    c["rx1-vcma"] = dict(
        title="1-RX choice: C63, C216, C219 left on /ADC_VCMA with no source or load", refs="C63;C216;C219",
        cols=["Option", "Change", "Cost", "Effect"],
        rows=[["A. not fitted (DNP)", "3 DNP marks", "none", "parts stay in the schematic, as the RX2 parts do"],
              ["B. leave fitted", "none", "3 parts placed", "no function; an isolated net with only passives"],
              ["C. remove with the net", "schematic and board edit", "rx1-03 edit time", "no leftover net or parts"]],
        consequence="With the LT6231 (rx1-opamp B) amps C and D are gone, so rx1-unused-amps does not apply.",
        recommendation="C, chosen by the user 2026-11-25.")
    c["rx1-seq"] = dict(
        title="1-RX choice: rail order at the AD9237 (3V0 first) by design", refs="U24;U23",
        cols=["Option", "Change", "Cost", "Effect"],
        rows=[["A. U24 and U23 EN from 3V0", "two net changes", "no parts; two low-current traces",
               "3V3A, 1V8 and 3V3D (U6 clock, FPGA pins) start only after 3V0 passes 0.5-1.2 V"],
              ["B. supervisor on 3V0 drives the enables", "one IC", "part, space", "strict 3V0-good signal"],
              ["C. as is (all EN on 3V8)", "none", "none", "order set by timing only; rx1-05 and bring-up check it"]],
        consequence="st-ld39200-datasheet p.7; ti-lp5907-datasheet p.6 (no power-good output on U39); "
                    "amd-ds181-artix7-datasheet p.8 (FPGA order kept); adi-ad9237-datasheet p.7 and p.10.",
        recommendation="A, chosen by the user 2026-11-25; rx1-05 checks it, lay-03 measures it.")
    c["rx1-unused-amps"] = dict(
        title="1-RX choice: unused U45 amps C and D (only if U45 stays the SSOP-16 quad)", refs="U45",
        cols=["Option", "What changes", "Class", "Note"],
        rows=[["A. merge /ADC_VCMA into /ADC_VCMB", "R31, R38, R63, R64 not fitted; R39, R40, C39, C40 kept", "netlist only",
               "each unused amp is a unity follower on the bias, no floating node"],
              ["B. also not fit R39, R40", "inverting input floats", "netlist only", "not recommended"],
              ["C. tie the + inputs to GND", "outside the input range at 3.3 V", "netlist only", "not recommended"]],
        consequence="adi-lt6232-datasheet p.3 (input common-mode range 1.15 to 2.65 V at 3.3 V). Not needed when "
                    "rx1-opamp is B.",
        recommendation="A.")
    c["rx1-ifbias"] = dict(
        title="1-RX choice: R51, R52 (IF1 pull-ups of the shared mixer)", refs="R51,R52",
        cols=["Option", "What changes", "Class", "Note"],
        rows=[["A. keep fitted", "none", "netlist only", "the ADL5802 IF1 open-collector output keeps its pull-up"],
              ["B. not fitted", "two refs DNP", "netlist only", "your call; no check covers the unused IF1 output"]],
        consequence="adi-adl5802-datasheet p.6 (Table 3: OP1+/- need a pull-up). They are receive-chain-2 only "
                    "electrically but bias the shared part.",
        recommendation="A: leaves the shared mixer exactly as in 2-RX.")
    return c


# ---------------------------------------------------------------------------------------------


def format_choices(data: dict) -> str:
    """Write choices.json in the file's own layout (cols and each row on one line)."""
    inl = lambda x: json.dumps(x, ensure_ascii=False)  # noqa: E731
    out = ["{", f' "_source": {inl(data["_source"])},', ' "choices": {']
    keys = list(data["choices"])
    for ki, key in enumerate(keys):
        ch = data["choices"][key]
        out.append(f'  {inl(key)}: {{')
        out.append(f'   "title": {inl(ch["title"])},')
        out.append(f'   "refs": {inl(ch["refs"])},')
        out.append(f'   "cols": {inl(ch["cols"])},')
        out.append('   "rows": [')
        out.append(",\n".join(f"    {inl(r)}" for r in ch["rows"]))
        out.append("   ],")
        out.append(f'   "consequence": {inl(ch["consequence"])},')
        out.append(f'   "recommendation": {inl(ch["recommendation"])}')
        out.append("  }" + ("," if ki < len(keys) - 1 else ""))
    out += [" }", "}"]
    return "\n".join(out) + "\n"


def merged_choices() -> dict:
    data = json.loads(CHOICES.read_text())
    keep = {k: v for k, v in data["choices"].items() if not k.startswith("rx1-")}
    keep.update(choices())
    data["choices"] = keep
    return data


def write() -> None:
    with CSV_OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(changes())
    CHOICES.write_text(format_choices(merged_choices()))


if __name__ == "__main__":
    write()
    n = len(changes())
    print(f"rx1_changes.py: {n} rows in {CSV_OUT.relative_to(ROOT)}, {len(choices())} rx1- choices in "
          f"{CHOICES.relative_to(ROOT)}")
