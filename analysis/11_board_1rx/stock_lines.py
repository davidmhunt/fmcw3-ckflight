"""rx1-02 step 5: JLC stock for every placed 1-RX line, and JLC-stocked options for the failures.

The 1-RX line list is the kicad-1rx/ BOM (a copy of the 2-RX schematic today) with the step 2 and
step 4 changes applied on paper (nothing under kicad-1rx/ is written):
  - the RX2-only parts of sim/rx2_dnp.json are not fitted, except R51/R52 (open-collector pull-ups
    of the shared ADL5802 IF1 output) and R39/R40/C39/C40 (the unused U45 amps), which the step 4
    recommendation keeps fitted;
  - the five U8 channel-B parts (R20, C19, C20, C22, C23) go with the U8 swap;
  - U8 becomes the AD9237BCPZ-40 (LCSC C514275);
  - step 2: C217/C218 1u -> 100n, C220 2.2u -> 10u (adi-ad9237-datasheet p.18 Figure 39), two 1 k
    resistors (R990, R991) for the 1.5 V bias divider, and 100n + 10u on VREF (C992, C993).
Each line is checked against the JLC parts database (parts/check_jlc.py) for stock of at least
qty x board_quantity. OPTIONS holds the JLC-stocked options for every line that fails or has no
margin: class (drop-in, footprint change, design change), datasheet manifest id and page, and the
check that covers it. Stock figures in the output are read from the database, never typed.

Run: ./run python3 analysis/11_board_1rx/stock_lines.py   (writes sim/stock_lines.json)
"""
import datetime
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "parts"))
sys.path.insert(0, str(ROOT / "tools"))
import bom  # noqa: E402
import check_jlc as jl  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "sim" / "stock_lines.json"
SCH = ROOT / "kicad-1rx" / "fmcw3_1rx.kicad_sch"
RX2 = HERE / "sim" / "rx2_dnp.json"
KEEP_FITTED = {"R51", "R52", "R39", "R40", "C39", "C40"}
CH_B_WITH_U8 = {"R20", "C19", "C20", "C22", "C23"}
BOARDS = 3  # board_quantity of analysis/targets/default.yaml
MARGIN = 2  # a line with stock below MARGIN x need passes but is flagged "no margin"

# ---------------------------------------------------------------- the line list


def one_k_fields(rows):
    ref = next(r for r in rows if r["ref"] == "R4")
    return {k: ref[k] for k in ("Value", "Footprint", "MPN", "Manufacturer", "LCSC", "Tolerance",
                                "Voltage", "Dielectric", "DigiKey PN")}


def line_rows():
    """Row-level BOM of the 1-RX board with the changes applied. Returns (rows, removed refs)."""
    rows = bom.merge_decisions(bom.export_rows(SCH), bom.load_decisions())
    rx2 = json.loads(RX2.read_text())
    gone = (set(rx2["only_rx2"]) - KEEP_FITTED) | CH_B_WITH_U8 | {"U8"}
    kept = [dict(r) for r in rows if r["ref"] not in gone]
    removed = sorted(r["ref"] for r in rows if r["ref"] in gone)
    blank = dict(Manufacturer="", LCSC="", Tolerance="", Voltage="", Dielectric="")
    for r in kept:
        if r["ref"] in ("C217", "C218"):
            r.update(Value="100n", MPN="", **blank)
        if r["ref"] == "C220":
            r.update(Value="10u", MPN="", **blank)
    k1 = one_k_fields(rows)
    cap = dict(DNP=False, MPN="", **blank, **{"DigiKey PN": ""})
    new = [
        dict(ref="U8", Value="AD9237", Footprint="LFCSP-32_5x5mm", MPN="AD9237BCPZ-40",
             Manufacturer="Analog Devices", LCSC="C514275", DNP=False, Tolerance="", Voltage="",
             Dielectric="", **{"DigiKey PN": ""}),
        dict(ref="R990", DNP=False, **k1), dict(ref="R991", DNP=False, **k1),
        dict(ref="C992", Value="100n", Footprint="SMD_0402", **cap),
        dict(ref="C993", Value="10u", Footprint="SMD_0603", **cap),
        dict(ref="C994", Value="10u", Footprint="SMD_0603", **cap),
        dict(ref="C995", Value="10u", Footprint="SMD_0603", **cap),
    ]
    return kept + new, removed


# ---------------------------------------------------------------- the checks behind the options

LMR_ILIM_TYP, LMR_ILIM_MAX = 3.5, 5.1   # A, adi: ti-lmr51420-datasheet p.5 IHS_PK(OC)
LMR_IOUT_MAX = 2.0                      # A, ti-lmr51420-datasheet p.1 and p.15
LMR_FSW = 1.1e6                         # Hz, YF variant, ti-lmr51420-datasheet p.3
VIN = 12.0                              # V, net /power/12V
RAILS = {"L5": ("/1V0", 1.0), "L6": ("/3V8", 3.8), "L7": ("/power/5V6", 5.6)}
# (id, mpn, lcsc, L tolerance, Isat A, source). Isat is the rating that bears on saturation.
INDUCTORS = [
    ("SRR6040A-330M (today)", "C2042352", 0.20, 1.02, "dk-srr6040a-330m p.1 (Isat 1.02 A)"),
    ("SRR6038-330Y", "C2041395", 0.30, 1.20, "bourns-srr6038-datasheet p.1 (Isat 1.20 A)"),
    ("CDRH6D28NP-330NC", "C313052", 0.30, 0.97, "sumida-cdrh6d28-datasheet p.2 (rated 0.97 A, "
                                              "inductance down to 65 percent)"),
    ("APS1040M330A", "C47327250", 0.20, 5.05, "coilank-aps1040m330a-datasheet p.8 (Isat 5.05 A typ, "
                                             "40 percent drop)"),
    ("SMS0650-330MT", "C5127476", 0.20, 3.3, "JLC listing only (no datasheet on file)"),
    ("FCH0650-330M", "C20415540", 0.20, 3.2, "JLC listing only (no datasheet on file)"),
]


def inductor_check():
    """Isat of each 33 uH option against the LMR51420 limits, and the ripple/peak at 2 A out."""
    rows = []
    for name, lcsc, tol, isat, src in INDUCTORS:
        per_rail = {}
        for ref, (net, vout) in RAILS.items():
            lmin = 33e-6 * (1 - tol)
            ripple = vout * (1 - vout / VIN) / (lmin * LMR_FSW)       # p.18 Eq. 10
            per_rail[ref] = dict(net=net, vout=vout, ripple_a=round(ripple, 3),
                                 peak_at_2a=round(LMR_IOUT_MAX + ripple / 2, 3))
        worst = max(v["peak_at_2a"] for v in per_rail.values())
        rows.append(dict(option=name, lcsc=lcsc, isat_a=isat, source=src,
                         ok_vs_limit_typ=isat > LMR_ILIM_TYP, ok_vs_limit_max=isat > LMR_ILIM_MAX,
                         ok_vs_full_load=isat > worst, worst_peak_at_2a=worst, rails=per_rail))
    return rows


E96 = [1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30, 1.33, 1.37, 1.40, 1.43,
       1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10,
       2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
       3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12, 4.22, 4.32, 4.42, 4.53,
       4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65,
       6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76]


def e96_values(lo, hi):
    out = []
    dec = 10 ** math.floor(math.log10(lo))
    while dec <= hi:
        out += [round(m * dec, 6) for m in E96 if lo <= m * dec <= hi]
        dec *= 10
    return sorted(set(out))


def ohm_text(v):
    return f"{v / 1e6:g}M" if v >= 1e6 else f"{v / 1e3:g}k"


def jlc_resistor(db, ohms, need=3):
    """Best JLC 0402 chip resistor of this value (stock for `need`, Basic first) or None."""
    text = ohm_text(ohms)
    recs = [r for r in db.by_value("R", "0402", jl.search_term("R", text))
            if jl.value_in_description("R", text, r["description"]) and r["stock"] >= need]
    return jl.best(recs, need) if recs else None


def divider(vref, vout=10.0, db=None, lo=47e3, hi=470e3, n=3):
    """Best E96 (R_top, R_bottom) pairs for VOUT = VREF x (1 + Rtop/Rbottom), R_bottom in lo..hi,
    R_top up to 3.3 M. With `db`, both values must be in JLC 0402 stock."""
    cand = []
    for rb in e96_values(lo, hi):
        for rt in e96_values(100e3, 3.3e6):
            v = vref * (1 + rt / rb)
            cand.append((abs(v - vout), rt, rb, v))
    cand.sort()
    res = []
    for _, rt, rb, v in cand:
        row = dict(r_top=rt, r_bottom=rb, vout=round(v, 4), error_pct=round(100 * (v - vout) / vout, 3))
        if db is not None:
            a, b = jlc_resistor(db, rt), jlc_resistor(db, rb)
            if not (a and b):
                continue
            row.update(top_lcsc=a["lcsc"], top_stock=a["stock"], bottom_lcsc=b["lcsc"],
                       bottom_stock=b["stock"])
        res.append(row)
        if len(res) == n:
            break
    return res


def ldo_check(db=None):
    """Feedback divider for 10 V on the two JLC-stocked adjustable SOT-23-5 LDOs."""
    tps = divider(1.24, db=db)
    pick = tps[0]
    vlo = 1.22 * (1 + pick["r_top"] * 0.99 / (pick["r_bottom"] * 1.01))
    vhi = 1.26 * (1 + pick["r_top"] * 1.01 / (pick["r_bottom"] * 0.99))
    ifb_limit = 10.0 / (10e-9 * 100)  # p.14 Eq. 3: R1 + R2 <= VOUT / (IFB x 100), IFB = 10 nA
    return dict(
        vin=VIN, vout=10.0,
        tps7a2401=dict(vref=1.24, vref_range=[1.22, 1.26], equation="VOUT = VFB x (1 + R1/R2)",
                       best=tps, worst_case_v=[round(vlo, 3), round(vhi, 3)],
                       r_sum_limit_ohm=ifb_limit, r_sum_ohm=pick["r_top"] + pick["r_bottom"],
                       dropout_max_v=0.25, headroom_v=VIN - 10.0,
                       noise_uv_at_1v24=300, noise_gain=round(10.0 / 1.24, 2),
                       noise_uv_scaled=round(300 * 10.0 / 1.24)),
        mic5205=dict(vref=1.242, equation="VOUT = 1.242 V x (1 + R2/R1)", best=divider(1.242, db=db),
                     noise_nv_rthz=260),
        lp2985=dict(noise_uv=30, note="30 uVrms with 10 nF bypass, 300 Hz to 50 kHz at 3.3 V out"))


# ---------------------------------------------------------------- the options

# class: "drop-in" (same footprint and pinout), "footprint change", "design change".
# Each option: lcsc, label, cls, qty_per_board (default: the line's), why, cites, check.
OPTIONS = {
    "U30": dict(refs="U30", need_lines="XC7A100T-1FTG256C", options=[
        dict(id="A", lcsc="C1521781", label="XC7A100T-1FTG256I", cls="drop-in",
             why="same die and FTG256 package, grade C to I; par-03 choice 'fpga' option B "
                 "(the user's choice list)",
             cites=[("amd-ds180-7series-overview", 15), ("amd-xc7a100t-ftg256-pinout", None)],
             check="par-03 choice 1 pin check (same 256 balls); Table 12 lists -1C and -1I"),
        dict(id="B", lcsc="C1521771", label="XC7A100T-2FTG256I", cls="drop-in",
             why="speed grade -2 in the same package",
             cites=[("amd-ds180-7series-overview", 15)], check="no extra check; dearer"),
    ]),
    "U26": dict(refs="U26;U27", options=[
        dict(id="A", lcsc="C531388", label="HHM1907B1 (TDK, 0402)", cls="footprint change",
             why="0402 four-terminal against the 0805 five-terminal 5400BL15B050E; par-09 option B",
             cites=[("tdk-hhm1907b1-datasheet", 2), ("tdk-hhm1907b1-datasheet", 3),
                    ("johanson-5400bl15b0050001e-datasheet", 1)],
             check="rf-01: amplitude balance +-2.5 dB against 2 dB, insertion loss 0.8 dB max, "
                   "phase 170-190 deg (p.3); no TDK S-parameter file on file, so no simulation covers it"),
    ]),
    "U45": dict(refs="U45", options=[
        dict(id="A", lcsc="C673022", label="LT6232CGN#PBF (C grade, SSOP-16)", cls="drop-in",
             why="same package and pinout; JLC stock is below the need of 3",
             cites=[("adi-lt6232-datasheet", 3)], check="stock only: fails for 3 boards"),
        dict(id="B", lcsc="C4369556", label="LT6231CS8#TRPBF (C grade, SO-8), one per board",
             cls="footprint change",
             why="only amps A and B are used by the kept chain; pins 1-3 and 5-7 keep their numbers, "
                 "V+ moves from pin 4 to pin 8 and V- from pin 13 to pin 4, so SSOP-16 becomes SO-8 "
                 "and the unused C/D pair (and the VCMA merge of step 4) disappears",
             cites=[("adi-lt6232-datasheet", 2), ("adi-lt6232-datasheet", 3)],
             check="step 3 simulation (sim/adc_input.json) already runs the LT6231 subcircuit "
                   "(adi-lt6231-ltspice-bundled): its swing, common mode, settling and IF response "
                   "apply unchanged; C grade is 0 to 70 C specified (p.3 order table)",
             qty_per_board=1),
        dict(id="C", lcsc="C580237", label="LT6231CS8#PBF (C grade, SO-8, tube)", cls="footprint change",
             why="same die as B, tube packing", cites=[("adi-lt6232-datasheet", 3)],
             check="as B", qty_per_board=1),
    ]),
    "U21": dict(refs="U21", options=[
        dict(id="A", lcsc="C2861715", label="LP2985-10DBVR (non-A)", cls="drop-in",
             why="same pins, 1.5 percent instead of 1 percent; JLC stock is 0",
             cites=[("ti-lp2985-datasheet", 3), ("ti-lp2985-datasheet", 4)],
             check="stock only: fails"),
        dict(id="B", lcsc="C2693328", label="TPS7A2401DBVR (adjustable, 200 mA)", cls="design change",
             why="same SOT-23-5 pin positions (IN 1, GND 2, EN 3, FB 4, OUT 5); pin 4 BYPASS becomes "
                 "FB, so two divider resistors are added and C95 becomes a feed-forward cap",
             cites=[("ti-tps7a24-datasheet", 3), ("ti-tps7a24-datasheet", 6),
                    ("ti-tps7a24-datasheet", 14), ("ti-lp2985-datasheet", 3)],
             check="divider for 10 V (see ldo_check); dropout 250 mV max at 200 mA against 2 V "
                   "headroom (p.6); noise 300 uVrms at 1.24 V (p.6) scales with the divider gain, "
                   "against 30 uVrms for the LP2985 (p.1): not simulated, sim-01 / sim-spurs"),
        dict(id="C", lcsc="C412820", label="MIC5205YM5-TR (adjustable, 150 mA)", cls="design change",
             why="same SOT-23-5 outline; pin 4 is ADJ (p.9), two divider resistors added",
             cites=[("microchip-mic5205-datasheet", 2), ("microchip-mic5205-datasheet", 9),
                    ("microchip-mic5205-datasheet", 11)],
             check="divider for 10 V (see ldo_check); 12 V input is inside the 16 V maximum; "
                   "noise 260 nV/rtHz (p.4); not simulated"),
    ]),
    "P1": dict(refs="P1;U15", options=[
        dict(id="A", lcsc="C496550", label="BWSMA-KE-P001 (Bat Wireless)", cls="design change",
             why="a vertical, screw-on SMA (6.5 mm square body, through-board pin) against the "
                 "CONSMA003.062 edge-launch jack for a 0.062 in board: the cable direction and the "
                 "board edge change, not only the land pattern",
             cites=[("batwireless-bwsma-ke-p001-datasheet", 3), ("batwireless-bwsma-ke-p001-datasheet", 4),
                    ("batwireless-bwsma-ke-p001-datasheet", 6), ("dk-consma003.062", 1)],
             check="0-6 GHz, 0.15 dB at 6 GHz (p.4) covers 5.6-5.9 GHz; mounting fit is a layout and "
                   "enclosure decision; no simulation covers the pad transition"),
        dict(id="B", lcsc="C3172297", label="132134-15 (Amphenol RF, edge-mount SMD)",
             cls="footprint change",
             why="edge-mount SMA like the CONSMA; its datasheet is not on file (user-fetch row "
                 "amphenol-132134-datasheet), so nothing about it is claimed beyond the JLC listing",
             cites=[], check="user fetches amphenol-132134-datasheet, then compare land pattern and "
                             "board thickness (the board is 1.5266 mm)"),
    ]),
    "L5": dict(refs="L5;L6;L7", options=[
        dict(id="A", lcsc="C47327250", label="APS1040M330A (11.5 x 10 mm)", cls="footprint change",
             why="the only 33 uH part whose Isat (5.05 A) is near the LMR51420 limit",
             cites=[("coilank-aps1040m330a-datasheet", 8), ("ti-lmr51420-datasheet", 5),
                    ("ti-lmr51420-datasheet", 18)],
             check="inductor_check: Isat 5.05 A above the 3.5 A typ and below the 5.1 A max high-side "
                   "peak limit (p.5); p.18 asks for Isat above the peak limit; well above the 2 A "
                   "full-load peak"),
        dict(id="B", lcsc="C5127476", label="SMS0650-330MT (7.1 x 6.6 mm)", cls="footprint change",
             why="smaller body; Isat 3.3 A from the JLC listing only",
             cites=[("ti-lmr51420-datasheet", 5), ("ti-lmr51420-datasheet", 18)],
             check="inductor_check: 3.3 A is below the 3.5 A typ limit but above the 2 A full-load peak; "
                   "no datasheet on file, so the rating is a listing figure"),
        dict(id="C", lcsc="C20415540", label="FCH0650-330M (7.5 x 6.8 mm)", cls="footprint change",
             why="Isat 3.2 A from the JLC listing only; no datasheet on file",
             cites=[("ti-lmr51420-datasheet", 18)], check="inductor_check as B"),
        dict(id="D", lcsc="C2041395", label="SRR6038-330Y (6.8 mm, par-09)", cls="footprint change",
             why="Isat 1.20 A: saturates before the LMR51420 limit",
             cites=[("bourns-srr6038-datasheet", 1)], check="inductor_check: fails the limit"),
        dict(id="E", lcsc="C313052", label="CDRH6D28NP-330NC (6.7 mm, par-09)", cls="footprint change",
             why="rated 0.97 A: saturates before the LMR51420 limit",
             cites=[("sumida-cdrh6d28-datasheet", 2)], check="inductor_check: fails the limit"),
    ]),
    "U29": dict(refs="U29", options=[
        dict(id="A", lcsc="C657785", label="ADL5802ACPZ-R7 (as is, order at once)", cls="drop-in",
             why="JLC stock equals the need of 3: it passes with no spare; it can only be drawn down",
             cites=[("adi-adl5802-datasheet", 30)], check="stock only; the stock must be re-read on the day of the order"),
        dict(id="B", lcsc="C496495", label="ADL5801ACPZ-R7 (single mixer, same LFCSP-24)",
             cls="design change",
             why="one mixer is enough for one chain, but the ADL5801 datasheet is not in the manifest, "
                 "so its pinout, LO range and IF are not claimed here",
             cites=[], check="needs the ADL5801 datasheet and rf-01; not evaluated"),
    ]),
    "U12": dict(refs="U12", options=[
        dict(id="A", lcsc="C2654158", label="PAT1220-C-3DB-T5 (as is)", cls="drop-in",
             why="stock is above the need of 3 but under twice it",
             cites=[("pat1220-attenuator-datasheet", 1)], check="stock only"),
        dict(id="B", lcsc="C2655485", label="PAT0816-C-3DB-T5 (0603)", cls="footprint change",
             why="1.6 x 0.8 mm against 2.0 x 1.25 mm, 64 mW against 100 mW",
             cites=[("pat1220-attenuator-datasheet", 1), ("pat1220-attenuator-datasheet", 2)],
             check="rf-01 level plan: power at U12 must stay below 64 mW (18 dBm); not run"),
    ]),
    "U3": dict(refs="U3", options=[
        dict(id="A", lcsc="C32951947", label="PAT1220-C-6DB-T5", cls="drop-in",
             why="same Susumu PAT1220 0805 part as U12, 6 dB; the user accepts the match "
                 "(decisions.csv U3 is for-user). The JLC text says 0-3 GHz; the maker table says "
                 "DC to 10 GHz for the PAT1220 (read from the page image) and governs",
             cites=[("pat1220-attenuator-datasheet", 1), ("pat1220-attenuator-datasheet", 2)],
             check="rf-01 level plan; no simulation yet"),
    ]),
    "D1": dict(refs="D1;D2;D3;D5;D6;D7", options=[
        dict(id="A", lcsc="C2286", label="KT-0603R red", cls="drop-in",
             why="0603 LED, Basic; the colour is the user's. Green, white or blue (Vf up to 3.1 V) "
                 "need the series resistors re-sized",
             cites=[("kento-kt-0603-led-datasheet", 3)], check="Vf 1.8-2.4 V at 20 mA (p.3)"),
    ]),
    "CON2": dict(refs="CON2", options=[
        dict(id="A", lcsc="C720557", label="DC-005-A200 (Xunpu)", cls="footprint change",
             why="through-hole right-angle jack; the footprint BarrelJack was not compared with its "
                 "PCB layout, so a footprint change is assumed",
             cites=[("xunpu-dc-005-a200-datasheet", 1)],
             check="compare the PCB layout on p.1 with the BarrelJack footprint; whether JLC places "
                   "through-hole parts is for the user to confirm in the order tool"),
        dict(id="B", lcsc="C431533", label="DC005 (Shou Han)", cls="footprint change",
             why="same family of jack", cites=[("shouhan-dc005-datasheet", 1)],
             check="as A"),
    ]),
    "J2": dict(refs="J2", options=[
        dict(id="A", lcsc="C68234", label="2.54-2*8PPin (Boomele)", cls="footprint change",
             why="2.54 mm pitch against the board's 2.5 mm pads (PinHeader_2x8_P2.5mm); through-hole",
             cites=[("boomele-2-54-2x8-header-datasheet", 1)],
             check="the 0.04 mm per row mismatch (0.28 mm over 8 rows) means a new footprint at 2.54 mm"),
        dict(id="B", lcsc="C32713281", label="HX PZ2.54-2x8P ZZ (Hanxia)", cls="footprint change",
             why="same pitch", cites=[("hanxia-hx-pz2-54-2x8p-datasheet", 3)], check="as A"),
    ]),
}

# lines the tool treats as having an options entry; refs in the BOM line -> OPTIONS key
OPTION_KEY = {"U30": "U30", "U26": "U26", "U45": "U45", "U21": "U21", "P1": "P1", "L5": "L5",
              "U29": "U29", "U12": "U12", "U3": "U3", "D1": "D1", "CON2": "CON2", "J2": "J2"}
NEW_PARTS = {"U8": dict(cls="footprint change", why="AD9237BCPZ-40 in LFCSP-32 5x5 (decided by the "
                                                       "directive, not a stock choice)",
                        cites=[("adi-ad9237-datasheet", 8)])}


# ---------------------------------------------------------------- the run


def status_of(g, need, r):
    if g["class"] == "dnp":
        return "dnp"
    if bom.is_mechanical(g):
        return "no part"
    ok = r["jlc_status"] == "Available" and r["jlc_match"] in ("exact", "package")
    if not ok:
        return "fail"
    return "thin" if r["jlc_stock"] < MARGIN * need else "ok"


def run(db):
    rows, removed = line_rows()
    lines = []
    for g in bom.group_rows(rows):
        need = g["qty"] * BOARDS
        r = jl.blank() if g["class"] == "nopart" else jl.check_group(db, g, need)
        lines.append(dict(refs=g["refs"], qty=g["qty"], need=need, value=g["Value"],
                          footprint=g["Footprint"], mpn=g["MPN"], status=status_of(g, need, r),
                          lcsc=r["jlc_lcsc"], library=r["jlc_library"], stock=r["jlc_stock"],
                          match=r["jlc_match"], unit_price=r["jlc_unit_price"]))
    return lines, removed


def option_rows(db, lines):
    """Look every option up in the database; stock is compared with the line's need."""
    by_ref = {ref: ln for ln in lines for ref in ln["refs"]}
    out = {}
    for key, ent in OPTIONS.items():
        refs = ent["refs"].split(";")
        ln = by_ref.get(refs[0])
        nref = len(refs)
        opts = []
        for o in ent["options"]:
            rec = (db.by_lcsc(o["lcsc"]) or [None])[0]
            need = o.get("qty_per_board", nref) * BOARDS
            stock = rec["stock"] if rec else 0
            opts.append(dict(o, mpn=rec["mpn"] if rec else "", stock=stock, need=need,
                             library=rec["library"] if rec else "",
                             price=jl.price_at(rec["breaks"], need) if rec else None,
                             jlc_ok=stock >= need))
        out[key] = dict(refs=refs, line_status=ln["status"] if ln else "", options=opts)
    return out


def layout_count(options):
    """Footprint changes the layout must take: for every line that fails stock or has no part
    number, the least layout work among its JLC-stocked options."""
    rank = {"drop-in": 0, "footprint change": 1, "design change": 2}
    lines, refs = [], 0
    detail = {}
    for key, ent in options.items():
        if ent["line_status"] not in ("fail",):
            continue
        ok = [o for o in ent["options"] if o["jlc_ok"]]
        if not ok:
            detail[key] = "no JLC-stocked option"
            continue
        best = min(ok, key=lambda o: rank[o["cls"]])
        detail[key] = best["cls"]
        if best["cls"] != "drop-in":
            lines.append(key)
            refs += len(ent["refs"])
    return dict(by_line=detail, layout_lines=sorted(lines), layout_refs=refs,
                footprint_lines=sorted(k for k in lines if detail[k] == "footprint change"),
                design_lines=sorted(k for k in lines if detail[k] == "design change"))


def main():
    path = jl.ensure_db(jl.CACHE, offline=True)
    db = jl.Db(path)
    date = datetime.datetime.fromtimestamp(pathlib.Path(path).stat().st_mtime).strftime("%Y-%m-%d")
    lines, removed = run(db)
    options = option_rows(db, lines)
    counts = layout_count(options)
    res = dict(source="analysis/11_board_1rx/stock_lines.py", jlc_database_date=date, boards=BOARDS,
               removed_refs=removed, lines=lines, options=options, layout=counts,
               inductor_check=inductor_check(), ldo_check=ldo_check(db), new_parts=NEW_PARTS)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    tally = {}
    for ln in lines:
        tally[ln["status"]] = tally.get(ln["status"], 0) + 1
    print(f"JLC database {date}, {BOARDS} boards; lines by status: {tally}")
    for ln in lines:
        if ln["status"] in ("fail", "thin"):
            print(f"{ln['status'].upper():5} {';'.join(ln['refs'])[:30]:30} {ln['value'][:24]:24} "
                  f"need {ln['need']:3} stock {ln['stock']!s:>6} {ln['lcsc']}")
    for key, ent in options.items():
        for o in ent["options"]:
            print(f"  {key:5} {o['id']} {o['lcsc']:10} stock {o['stock']:>7} need {o['need']:3} "
                  f"{'ok  ' if o['jlc_ok'] else 'FAIL'} {o['cls']:17} {o['label']}")
    print("layout:", json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
