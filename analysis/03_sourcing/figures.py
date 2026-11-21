"""Sourcing plan for every line JLCPCB cannot place today (par-09): routes ranked JLC-first.

Run by tools/build_report.py with this folder as the working directory. Writes into build/.
Every figure comes from the par-09 findings in runs/par-09/notes.md (steps 1-4): JLC parts
database 2026-11-21, DigiKey API queried 2026-11-21, datasheets read through the sources
pipeline (manifest id and PDF page cited per route), JLC sourcing-service pages downloaded
2026-11-21. Costs are parts only, for the target set's board_quantity, no spares, no JLC
Extended-part setup fee, no shipping. Only board_quantity is read live; prices are data below.
"""
import csv
import json
import os
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import targets as tg  # noqa: E402

BUILD = HERE / "build"
NAVY, RED = "#1f2a44", "#c0392b"
JLC_DB = "2026-11-21"
DK_DATE = "2026-11-21"
PAGES = 5  # deck.yaml shows routes_1.png .. routes_5.png

SVC = "jlcpcb-global-sourcing-howto"
SVC_LEAD = "9-20 business days after 1-3 days review (howto); 9-15 (instruction page)"
SVC_NOTE = "JLC picks the supplier; unit price shown only in Parts Manager: for the user to confirm"

# Each line: refs, title, per-board qty, routes ranked JLC-first. A route has how, part, price
# (USD each), qty (default need), ref (True: DigiKey price used as a stand-in), cost (text that
# replaces the computed one), lead, work, ev.
LINES = [
    dict(refs="U8", title="ADC U8 (no MPN in schematic; LTC2292 family)", per=1, routes=[
        dict(how="JLC substitute, DESIGN CHANGE", part="ADS7863ARGET C2870160, JLC stock 250", price=14.437,
             lead="JLC stock",
             work="VQFN-24 footprint; SAR serial interface, new FPGA bank-35 pins; adc.vhd and FIR replaced; sim-02, sim-01, sim-spurs (new directive)",
             ev="ti-ads7863-datasheet p1, p3"),
        dict(how="JLC substitute, DESIGN CHANGE", part="AD7356BRUZ-500RL7 C650840, JLC stock 370", price=21.925,
             lead="JLC stock",
             work="TSSOP-16; 2.5 V supply, 2.048 V reference and VCM input network; serial interface, firmware as above",
             ev="adi-ad7356-datasheet p1, p3"),
        dict(how="JLC substitute, DESIGN CHANGE", part="ADS4229IRGCT C2670057, JLC stock 8", price=116.038,
             lead="JLC stock",
             work="VQFN-64 9x9; 1.8 V part, 1.8 V CMOS/LVDS capture, bank VCCO change; decimator kept",
             ev="ti-ads4229-datasheet p1"),
        dict(how="JLC sourcing service", part="LTC2292IUP#PBF (DigiKey stock 334)", price=51.64, ref=True,
             lead=SVC_LEAD, work="none, same part; user orders in Parts Manager. " + SVC_NOTE,
             ev=SVC + "; adi-ltc2292-datasheet p8"),
        dict(how="Consign from DigiKey", part="LTC2292IUP#PBF, stock 334", price=51.64,
             lead="13 wk + shipping to JLC", work="none; user orders and ships",
             ev="adi-ltc2292-datasheet p8; DigiKey " + DK_DATE),
        dict(how="Consign, pin drop-in", part="LTC2298IUP (14-bit), stock 125", price=140.36,
             lead="13 wk + shipping",
             work="none by pin (MSB pin 56); FPGA sees the top 12 bits; costs 2.7x",
             ev="adi-ltc2298-datasheet p12, p5; adi-ltc2292-datasheet p8"),
    ]),
    dict(refs="U30", title="FPGA U30 XC7A100T-1FTG256C (C grade: no JLC row)", per=1, routes=[
        dict(how="JLC stock, grade change", part="XC7A100T-1FTG256I C1521781, JLC stock 59", price=123.59,
             lead="JLC stock", work="drop-in by fields (C to I); decision alone, par-04 writes the value",
             ev="amd-ds180-7series-overview p15 (Table 12: Artix-7 -1C 0-85 C, -1I -40-100 C), p16 (Figure 2); par-03 choice 1 (analysis/01_parts); pin check 256 of 256"),
        dict(how="JLC substitute, DESIGN CHANGE", part="XC7A35T-1FTG256C C1521698, JLC stock 160", price=97.98,
             lead="JLC stock", work="smaller device: 35T bitstream; logic and RAM fit not checked here; same FTG256 package",
             ev="amd-xc7a35t-ftg256-pinout (pin table); amd-ds181-artix7-datasheet p5 (35T supply currents); par-03 choice 1"),
        dict(how="JLC sourcing service", part="XC7A100T-1FTG256C (DigiKey stock 16)", price=126.25, ref=True,
             lead=SVC_LEAD, work="none; DigiKey stock 16 only. " + SVC_NOTE, ev=SVC + "; DigiKey " + DK_DATE),
        dict(how="Consign from DigiKey", part="XC7A100T-1FTG256C, stock 16", price=126.25,
             lead="52 wk + shipping", work="none; the lead time is the problem", ev="DigiKey " + DK_DATE),
    ]),
    dict(refs="U26;U27;U28", title="Baluns U26-U28 5400BL15B0050001E (not in JLC database)", per=3, routes=[
        dict(how="JLC substitute, FOOTPRINT CHANGE", part="HHM1907B1 TDK C531388, JLC stock 7754", price=0.103,
             lead="JLC stock",
             work="0805 5-terminal to 0402 4-terminal footprint; rf-01 (amplitude balance 2.5 dB against 2 dB; TDK S-parameters not on file, user-fetch)",
             ev="tdk-hhm1907b1-datasheet p2, p3; johanson-5400bl15b0050001e-datasheet p1"),
        dict(how="JLC sourcing service", part="5400BL15B0050001E (DigiKey stock 6860)", price=1.09, ref=True,
             lead=SVC_LEAD, work="none; balun customs fee not named on the page (unconfirmed). " + SVC_NOTE,
             ev=SVC),
        dict(how="Consign from DigiKey", part="5400BL15B0050001E, stock 6860", price=1.09,
             lead="18 wk + shipping", work="none; rf-01 already uses its S-parameters",
             ev="johanson-5400bl15b0050001e-datasheet p1; DigiKey " + DK_DATE),
    ]),
    dict(refs="U45", title="Op-amp U45 LT6232IGN#PBF (JLC lists the C grade only)", per=1, routes=[
        dict(how="JLC stock, C grade, mixed", part="LT6232CGN#PBF C673022, JLC stock 2 of 3 + 1 consigned I grade",
             price=None, cost="2 x 17.724 + 14.32 = 49.77",
             lead="JLC stock for 2; 24 wk for the third", work="drop-in; 0-70 C against -40-85 C; two grades across three boards",
             ev="adi-lt6232-datasheet p2, p3"),
        dict(how="JLC substitute, FOOTPRINT CHANGE", part="2 x LT6231CS8#TRPBF per board C4369556, JLC stock 54",
             price=13.059, qty=6, lead="JLC stock",
             work="one SSOP-16 replaced by two SO-8; sim-02 re-run (LTspice model on file); C grade only",
             ev="adi-lt6232-datasheet p3, p4; adi-lt6231-ltspice-bundled"),
        dict(how="JLC sourcing service", part="LT6232IGN#PBF (DigiKey stock 63)", price=14.32, ref=True,
             lead=SVC_LEAD, work="none, same part. " + SVC_NOTE, ev=SVC),
        dict(how="Consign from DigiKey", part="LT6232IGN#PBF, stock 63", price=14.32,
             lead="24 wk + shipping", work="none", ev="adi-lt6232-datasheet p2; DigiKey " + DK_DATE),
    ]),
    dict(refs="U21", title="LDO U21 LP2985A-10DBVR (10 V output; not in JLC database)", per=1, routes=[
        dict(how="JLC substitute, LAYOUT CHANGE", part="TPS7A2401DBVR C2693328, JLC stock 10510", price=0.243,
             lead="JLC stock",
             work="same SOT-23-5; BYPASS pin 4 (C95) becomes an FB divider: two resistors, schematic and layout; noise against 30 uVrms not compared (sim-01, sim-spurs)",
             ev="ti-tps7a24-datasheet p1, p3; ti-lp2985-datasheet p3"),
        dict(how="JLC substitute, LAYOUT CHANGE", part="MIC5205YM5-TR C412820, JLC stock 7432", price=0.325,
             lead="JLC stock", work="same as above; 16 V maximum input on the 12 V rail; noise not compared",
             ev="microchip-mic5205-datasheet p1"),
        dict(how="JLC drop-in, no stock", part="LP2985-10DBVR (non-A, 1.5 %) C2861715, JLC stock 0", price=None,
             cost="not available", lead="-", work="same pins; unavailable today", ev="JLC database " + JLC_DB),
        dict(how="JLC sourcing service", part="LP2985A-10DBVR (DigiKey stock 2467)", price=1.84, ref=True,
             lead=SVC_LEAD, work="none. " + SVC_NOTE, ev=SVC),
        dict(how="Consign from DigiKey", part="LP2985A-10DBVR, stock 2467 (non-A: 17303 at about 0.52)", price=1.84,
             lead="26 wk + shipping", work="none; DigiKey calls the -10 '1V', the board needs 10 V",
             ev="ti-lp2985-datasheet p4; DigiKey " + DK_DATE),
    ]),
    dict(refs="P1;P2;U15", title="SMA edge connectors P1, P2, U15 CONSMA003.062 (not in JLC database)", per=3, routes=[
        dict(how="JLC substitute, FOOTPRINT CHANGE", part="BWSMA-KE-P001 Bat Wireless C496550, JLC stock 84178",
             price=0.407, lead="JLC stock",
             work="footprint change assumed; board-thickness fit UNVERIFIED (datasheet: 0-6 GHz, 50 ohm, 0.15 dB at 6 GHz, so 5.8 GHz is inside the rating)",
             ev="batwireless-bwsma-ke-p001-datasheet p4 (ratings), p6 (drawing, 6.5 mm square body)"),
        dict(how="JLC sourcing service", part="CONSMA003.062 (DigiKey stock 5353)", price=4.35, ref=True,
             lead=SVC_LEAD, work="connector: 20 USD inspection and 3C fee per kind, loose-part fee. " + SVC_NOTE,
             ev=SVC),
        dict(how="Consign from DigiKey", part="CONSMA003.062, stock 5353", price=4.35,
             lead="4 wk + shipping", work="none", ev="parts/decisions.csv; DigiKey " + DK_DATE),
        dict(how="Hand solder", part="CONSMA003.062 bought as above", price=4.35,
             lead="4 wk + hand work", work="user solders 3 edge launches per board after JLC delivers; RF repeatability",
             ev="user choice"),
    ]),
    dict(refs="U29", title="Mixer U29 ADL5802ACPZ-R7 (JLC stock 3 = need, no margin)", per=1, routes=[
        dict(how="JLC stock", part="ADL5802ACPZ-R7 C657785, JLC stock 3", price=19.649, lead="JLC stock",
             work="none; order at once, no stock margin", ev="JLC database " + JLC_DB),
        dict(how="JLC sourcing service", part="ADL5802ACPZ-R7 (DigiKey stock 1470)", price=24.93, ref=True,
             lead=SVC_LEAD, work="none. " + SVC_NOTE, ev=SVC),
        dict(how="Consign from DigiKey", part="ADL5802ACPZ-R7, stock 1470", price=24.93, lead="10 wk + shipping",
             work="none (ADL5801 is a single mixer: design change, not proposed)", ev="DigiKey " + DK_DATE),
    ]),
    dict(refs="U12", title="Attenuator U12 PAT1220 3 dB (JLC stock 5 for 3)", per=1, routes=[
        dict(how="JLC stock", part="PAT1220-C-3DB-T5 C2654158, JLC stock 5", price=0.593, lead="JLC stock",
             work="none; order at once, stock below twice the need", ev="pat1220-attenuator-datasheet p1, p2"),
        dict(how="JLC substitute, FOOTPRINT CHANGE", part="PAT0816-C-3DB-T5 C2655485, JLC stock 401", price=0.646,
             lead="JLC stock", work="1.6x0.8 mm footprint; power at U12 must stay below 64 mW (rf-01 level plan)",
             ev="pat1220-attenuator-datasheet p1, p2 (also covers PAT0816)"),
        dict(how="JLC sourcing service", part="PAT1220-C-3DB-T5 (DigiKey stock 53945)", price=0.29, ref=True,
             lead=SVC_LEAD, work="attenuators named for 3-30 % customs fee. " + SVC_NOTE, ev=SVC),
        dict(how="Consign from DigiKey", part="PAT1220-C-3DB-T5, stock 53945", price=0.29,
             lead="32 wk quoted + shipping", work="none", ev="DigiKey " + DK_DATE),
    ]),
    dict(refs="U3", title="Attenuator U3 PAT1220 6 dB (no decision yet)", per=1, routes=[
        dict(how="JLC stock", part="PAT1220-C-6DB-T5 C32951947, JLC stock 464", price=0.65, lead="JLC stock",
             work="the user accepts the match; JLC text says 0-3 GHz, maker says DC-10 GHz (maker governs)",
             ev="pat1220-attenuator-datasheet p1"),
        dict(how="no other route", part="DigiKey stock 0", price=None, cost="-", lead="-",
             work="no sourcing or consign route: DigiKey has none", ev="DigiKey " + DK_DATE),
    ]),
    dict(refs="L5;L6;L7", title="Inductors L5-L7 SRR6040A-330M (JLC stock 3 of 9; DigiKey NFND)", per=3, routes=[
        dict(how="JLC stock, covers 3 of 9", part="SRR6040A-330M C2042352, JLC stock 3", price=0.996, qty=3,
             lead="JLC stock", work="drop-in for one board only; not recommended for new designs; Isat 1.02 A",
             ev="dk-srr6040a-330m p1"),
        dict(how="JLC substitute, FOOTPRINT CHANGE", part="CDRH6D28NP-330NC Sumida C313052, JLC stock 2386",
             price=0.542, lead="JLC stock",
             work="6.7 mm land pattern differs (user compares); rated 0.97 A, below the LMR51420 3.5 A limit",
             ev="sumida-cdrh6d28-datasheet p2"),
        dict(how="JLC substitute, FOOTPRINT CHANGE", part="SRR6038-330Y Bourns C2041395, JLC stock 88", price=1.059,
             lead="JLC stock", work="6.8x6.8x3.8 mm; Isat 1.20 A; same LMR51420 limit",
             ev="bourns-srr6038-datasheet p1"),
        dict(how="JLC substitute, DESIGN CHANGE", part="APS1040M330A C47327250, JLC stock 19638", price=0.241,
             lead="JLC stock", work="11x10 mm body, board room; Isat 4.4/5.0 A; LMR51420 analysis (choice 4)",
             ev="coilank-aps1040m330a-datasheet p8 (33 uH, 91 mohm, Irms 4.44 A, Isat 5.05 A); par-03 choice 4"),
    ]),
    dict(refs="D1;D2;D3;D5;D6;D7", title="LEDs D1-D3, D5-D7 (0603; no colour or part number)", per=6, routes=[
        dict(how="JLC stock, decision alone", part="KT-0603R red C2286 (Basic), JLC stock 8412802", price=0.008,
             lead="JLC stock", work="user names the colour; par-04 writes the field; series resistors not read",
             ev="kento-kt-0603-led-datasheet p3 (Vf 1.8-2.4 V at 20 mA, IF max 25 mA), p4 (Vf bins)"),
        dict(how="JLC stock, DESIGN CHANGE", part="white C2290 (stock 2367175), green C12624 (205035), blue C2288 (54527)",
             price=None, cost="white 0.012 x 18 = 0.22; others not recorded", lead="JLC stock",
             work="white, green, blue Vf 2.6-3.1 V at 5 mA against red 1.8-2.4 V at 20 mA: series resistor re-sized",
             ev="kento-kt-0603w-led-datasheet p3; kento-kt-0603g-led-datasheet p3; kento-kt-0603b-led-datasheet p3 (each: Vf 2.6-3.1 V at 5 mA, IF max 30 mA)"),
    ]),
    dict(refs="CON2", title="Barrel jack CON2 (through-hole; no part number)", per=1, routes=[
        dict(how="JLC stock, through-hole", part="DC-005-A200 XUNPU C720557, JLC stock 74760", price=0.145,
             lead="JLC stock", work="user names the jack; BarrelJack footprint not compared; JLC through-hole assembly to confirm",
             ev="xunpu-dc-005-a200-datasheet p1 (30 V DC / 3 A, -30 to 70 C, recommended PCB layout)"),
        dict(how="JLC stock, through-hole", part="DC005 SHOU HAN C431533, JLC stock 73526", price=0.055,
             lead="JLC stock", work="as above", ev="shouhan-dc005-datasheet p1 (drawing), p3 (-30 to 70 C; no voltage or current rating given)"),
        dict(how="Hand solder", part="either jack, bought through JLC or elsewhere", price=0.145,
             lead="by the user", work="user solders 3 jacks", ev="user choice"),
    ]),
    dict(refs="J2", title="Header J2 2x8, 2.5 mm pad pitch (through-hole; no part number)", per=1, routes=[
        dict(how="JLC stock, through-hole", part="2.54-2*8PPin C68234, JLC stock 17022", price=0.134,
             lead="JLC stock", work="user confirms the pitch: 2.5 mm pads against a 2.54 mm part (footprint question)",
             ev="boomele-2-54-2x8-header-datasheet p1 (3 A rated, 550 V AC withstand; drawing is the 2.54 mm 1xN family sheet, not 2x8-specific)"),
        dict(how="JLC stock, through-hole", part="HX PZ2.54-2x8P ZZ C32713281, JLC stock 6397", price=None,
             cost="price not recorded", lead="JLC stock", work="as above",
             ev="hanxia-hx-pz2-54-2x8p-datasheet p3 (-40 to 105 C, board 1.2-1.6 mm), p4 (250 V, 3 A)"),
        dict(how="Hand solder", part="either header", price=0.134, lead="by the user", work="user solders 3 headers",
             ev="user choice"),
    ]),
    dict(refs="U14", title="PA U14 QPA9501TR13 (the user's par-07 choice; listed for completeness)", per=1, routes=[
        dict(how="JLC stock", part="QPA9501TR13 C2911573, JLC stock 20", price=6.466, lead="JLC stock",
             work="none; rf-01 and sim-01 cover it (docs/board-changes.md)", ev="qorvo-qpa9501-datasheet"),
        dict(how="Consign from DigiKey", part="QPA9501TR13, stock 12947", price=6.28, lead="27 wk + shipping",
             work="none", ev="DigiKey " + DK_DATE),
    ]),
]

PAGE_LINES = [["U8", "U30"], ["U26;U27;U28", "U45"], ["U21", "P1;P2;U15"],
              ["U29", "U12", "U3", "L5;L6;L7"], ["D1;D2;D3;D5;D6;D7", "CON2", "J2", "U14"]]

COLS = ["Rank and route", "Part, price", "Cost (USD, 3 boards)", "Lead time", "Work it causes", "Datasheet evidence"]
WIDTHS = [0.14, 0.20, 0.13, 0.11, 0.24, 0.18]
DASHES = [12, 20, 14, 11, 24, 19]


def route_cells(line, i, r, boards):
    need = r.get("qty") or line["per"] * boards
    if r.get("cost"):
        cost = r["cost"]
    else:
        tot = r["price"] * need
        cost = f"{r['price']:g} x {need} = {tot:,.2f}"
        if r.get("ref"):
            cost = "about " + cost + " (DigiKey price; JLC's unconfirmed)"
    return [f"{i}. {r['how']}", r["part"], cost, r["lead"], r["work"], r["ev"]]


def wrap(text, width_in, fs, width_em=0.56):
    n = max(int((width_in * 72 - 6) / (fs * width_em)), 6)
    return textwrap.wrap(text, n) or [""]


def table_image(name, cols, rows, widths, fs, bands=None, fig=(12.1, 5.4)):
    """Draw cols+rows (and optional full-width band rows) into one picture; fail on overflow."""
    w_in, h_in = fig
    f = plt.figure(figsize=fig)
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_in)
    ax.set_ylim(h_in, 0)
    ax.axis("off")
    lh = fs * 1.28 / 72
    y = 0.03

    def draw(cells, ws, bold=False, fill=None, color=NAVY):
        nonlocal y
        wr = [wrap(t, w * w_in, fs) for t, w in zip(cells, ws)]
        h = max(len(x) for x in wr) * lh + 0.05
        if fill:
            ax.add_patch(Rectangle((0, y), w_in, h, color=fill, lw=0))
        x = 0.04
        for lines, w in zip(wr, ws):
            for k, ln in enumerate(lines):
                ax.text(x, y + 0.03 + k * lh, ln, va="top", fontsize=fs, color=color,
                        fontweight="bold" if bold else "normal")
            x += w * w_in
        y += h

    draw(cols, widths, bold=True, fill="#dfe4ee")
    for item in rows:
        if isinstance(item, str):
            draw([item], [1.0], bold=True, fill="#c9d3e6")
        else:
            draw(item, widths)
    if y > h_in:
        raise SystemExit(f"figures.py: {name} overflows its picture ({y:.2f} of {h_in} in)")
    f.savefig(BUILD / name, dpi=150)
    plt.close(f)


def write(name, header, rows):
    with open(BUILD / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


SUMMARY = [
    ("Settled by a decision alone",
     "U3 (accept the PAT1220 6 dB match), U12 (JLC stock 5; order at once), U14 (QPA9501, chosen), U29 (JLC stock 3; order at once), "
     "U30 (I grade, JLC stock 59), D1-D3 and D5-D7 (name the colour), CON2 and J2 (name the part)."),
    ("Needing analysis or layout",
     "U26-U28 balun (0402 footprint, rf-01), U21 (FB divider on the BYPASS pin), L5-L7 (land pattern, LMR51420 analysis), "
     "P1/P2/U15 (footprint, datasheets to fetch), U8 as a JLC-stocked ADC (redesign: sim-02, sim-01, sim-spurs, firmware), "
     "U45 as two LT6231 (sim-02), U12 as PAT0816 (rf-01)."),
    ("Must be sourced or consigned",
     "U8 LTC2292IUP (JLC stock 0), U21 LP2985A-10, U26-U28 Johanson balun, P1/P2/U15 CONSMA003.062, "
     "U45 I grade (and the third board of the C-grade mix), U30 only if it stays the C grade. "
     "No route at all for U3 beyond JLC stock."),
]

REC = [
    "U8: keep the LTC2292IUP and source it (JLC sourcing service if Parts Manager lists the MPN near the DigiKey 154.92 for 3, else consign); the JLC-stocked ADCs (43-348 for 3) need a redesign directive",
    "U30: the I grade from JLC stock (370.77 for 3), as in par-03 choice 1. U12 and U29: order from JLC stock at once; U3: accept the JLC match",
    "U26-U28, U21, U45 (I grade), P1/P2/U15: keep the schematic part and source or consign it; the JLC substitutes save under 10 USD for 3 boards and cost a layout change or an analysis, but they cut the lead time (18-26 wk consigned)",
    "L5-L7: do not order the SRR6040A; choose by choice 4 (an LMR51420 analysis). LEDs: red; CON2, J2: JLC part, confirm through-hole assembly",
    "Open: JLC sourcing-service unit prices and per-part lead times (Parts Manager, logged in): for the user to confirm",
]


def main() -> None:
    ts = tg.load(os.environ.get("FMCW_TARGETS", "default"))
    print(f"figures.py: {tg.describe(ts)}")
    BUILD.mkdir(exist_ok=True)
    boards = int(tg.value(ts, "board_quantity"))

    by_refs = {l["refs"]: l for l in LINES}
    placed = [r for page in PAGE_LINES for r in page]
    if sorted(placed) != sorted(by_refs):
        raise SystemExit("figures.py: PAGE_LINES and LINES differ")
    csv_rows, md = [], []
    n_routes = 0
    for pi, page in enumerate(PAGE_LINES, 1):
        rows = []
        for key in page:
            line = by_refs[key]
            need = line["per"] * boards
            rows.append(f"{', '.join(key.split(';'))}: {line['title']}; need {need}")
            md.append(f"### {', '.join(key.split(';'))}: {line['title']}\n\nNeed {need} for {boards} boards.\n")
            md.append("| " + " | ".join(COLS) + " |")
            md.append("|" + "|".join("-" * d for d in DASHES) + "|")
            for i, r in enumerate(line["routes"], 1):
                c = route_cells(line, i, r, boards)
                rows.append(c)
                esc = lambda s: s.replace("|", "\\|")  # noqa: E731
                md.append("| " + " | ".join(esc(x) for x in c) + " |")
                csv_rows.append([key.replace(";", " ")] + c)
                n_routes += 1
            md.append("")
        table_image(f"routes_{pi}.png", COLS, rows, WIDTHS, 7.4)
    if len(PAGE_LINES) != PAGES:
        raise SystemExit(f"figures.py: {len(PAGE_LINES)} pages, deck.yaml expects {PAGES}")
    write("routes_all.csv", ["Line"] + COLS, csv_rows)
    write("summary.csv", ["Group", "Lines and what it takes"], [list(s) for s in SUMMARY])
    table_image("summary.png", ["Group", "Lines and what it takes"], [list(s) for s in SUMMARY],
                [0.2, 0.8], 12, fig=(12.1, 4.2))
    (BUILD / "recommendation.txt").write_text("\n".join(f"- {r}" for r in REC) + "\n")

    facts = {
        "boards": boards, "jlc_db": JLC_DB, "dk_date": DK_DATE, "n_lines": len(LINES), "n_routes": n_routes,
        "routes_md": "\n".join(md),
        "recommendation": "\n".join(f"- {r}" for r in REC),
        "svc_lead": SVC_LEAD,
    }
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print(f"figures.py: {len(LINES)} lines, {n_routes} routes, {PAGES} pages")


if __name__ == "__main__":
    main()
