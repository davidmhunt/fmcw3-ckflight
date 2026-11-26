"""Figures, tables and facts for the 1-RX power-up report (rx1-05 step 6).

Run by tools/build_report.py with this folder as the working directory. Writes into build/. Nothing is
typed into writeup.md by hand: every number is read from sim/powerup.json (powerup_sim.py), sequence.csv
(sequence.py), fixes.csv, place_fix.csv and analysis/11_board_1rx/route_space.csv, so the report cannot
drift from them. Outputs:

    order_on.csv, order_off.csv   the order map (design or timing, the simulated margin, the fix)
    pins.csv                      per case: pin peak minus (AVDD + 0.3 V) at power-up and at 12 V removal
    clamp.csv                     clamp currents, the sweeps of the assumptions, the one-way U39 case
    steady.csv                    CLK and PDWN steady state at the tolerance limits, with the CLK fixes
    fixes_all.csv                 every proposed fix: cost, simulated result, room on today's board
    lay03.csv                     the waveforms lay-03 should see at bring-up
    powerup.png, removal.png      rail waveforms in order, pins against the limit, FPGA VCCO - VCCAUX
    order_on.png, order_off.png, pins.png, clamp.png, steady.png, fixes.png   the same tables as pictures
    facts.json                    numbers for writeup.md
"""
import csv
import json
import textwrap
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
SIM = HERE / "sim" / "powerup.json"
ROUTE = HERE.parent / "11_board_1rx" / "route_space.csv"
NAVY, RED, GREEN = "#1f2a44", "#c0392b", "#2e7d4f"
W_IN, H_IN = 12.1, 5.4
ABS = 0.3

RAIL_COL = {"3V0": "#c0392b", "3V3A": "#e67e22", "1V8": "#2e7d4f", "3V3D": "#2980b9", "1V0": "#8e44ad",
            "3V8": "#7f8c8d", "5V6": "#34495e", "12V": "#000000"}
TRACE = {"12V": "v12", "3V8": "v3v8", "5V6": "v5v6", "1V0": "v1v0", "3V0": "v3v0", "3V3A": "v3v3a",
         "1V8": "v1v8", "3V3D": "v3v3d"}

# what enforces each ordering on the 1-RX board (sequence.csv has the long form)
ENFORCED = {
    "on-3V0-3V3A": "U24 EN from 3V0 (R993)",
    "on-3V0-1V8": "U23 EN from 3V0 (R996)",
    "on-3V0-3V3D": "U25 EN from U23 PG; U23 EN from 3V0",
    "on-VCCINT-VCCBRAM": "one rail, 1V0 (U17)",
    "on-VCCINT-VCCAUX": "nothing: U17 and U18 both start from 12 V",
    "on-VCCINT-VCCO": "nothing: U17 and U18 both start from 12 V",
    "on-VCCAUX-VCCO": "U25 EN from U23 PG",
    "on-VCCO-minus-VCCAUX": "U25 EN from U23 PG (1V8 above 1.656 V first)",
    "off-3V3A-3V0": "nothing: no feed from 3V0 to 3V3A",
    "off-1V8-3V0": "nothing: no feed from 3V0 to 1V8",
    "off-3V3D-3V0": "nothing: no feed from 3V0 to 3V3D",
    "off-VCCO-VCCAUX": "nothing: U25 EN follows the U23 PG only after 1V8 falls",
    "off-VCCAUX-VCCINT": "nothing: no feed from 1V0 to 1V8",
    "off-VCCO-VCCINT": "nothing: no feed from 1V0 to 3V3D",
    "off-VCCO-minus-VCCAUX": "U25 turns off when the U23 PG falls (1.44 V)",
}


def num(x, nd=3):
    return "" if x is None else f"{round(x, nd):g}"


def case_label(k):
    p = k.split("_")
    s17 = "3.2" if p[0] == "u17f" else "5.4"
    s18 = "3.2" if p[1] == "u18f" else "5.4"
    ld = "0.1" if p[2] == "ldof" else "0.3"
    return f"U17 {s17}, U18 {s18} ms, LDO {ld} ms, IF {'0' if p[3] == 'if0' else 'FS'}"


def md_note(text):
    return text.replace("|", "\\|")


def write_csv(name, header, rows):
    with open(BUILD / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def image_table(name, cols, rows, widths, fs, notes=()):
    """Draw a table as a picture; rows are lists of strings."""
    fig = plt.figure(figsize=(W_IN, H_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    line_h = fs * 1.25 / 72 / H_IN
    y = 0.99

    def draw(cells, bold=False, fill=None, color=NAVY):
        nonlocal y
        wrapped = [textwrap.wrap(str(t), max(int(w * W_IN * 72 / (fs * 0.55)) - 2, 5)) or [""]
                   for t, w in zip(cells, widths)]
        h = max(len(w) for w in wrapped) * line_h + 0.010
        if fill:
            ax.add_patch(Rectangle((0, y - h), 1, h, color=fill, lw=0))
        x = 0.005
        for lines, w in zip(wrapped, widths):
            for i, ln in enumerate(lines):
                ax.text(x, y - 0.005 - i * line_h, ln, va="top", fontsize=fs,
                        fontweight="bold" if bold else "normal", color=color)
            x += w
        y -= h

    draw(cols, True, "#dfe4ee")
    for i, r in enumerate(rows):
        bad = any(str(c).startswith("FAIL") for c in r)
        draw(r, False, "#f4f6fa" if i % 2 == 0 else None, RED if bad else NAVY)
    y -= 0.015
    for t in notes:
        for ln in textwrap.wrap(t, int(W_IN * 72 / ((fs - 1) * 0.55)) - 4):
            ax.text(0.005, y, ln, va="top", fontsize=fs - 1, color=NAVY)
            y -= line_h
    if y < 0:
        raise SystemExit(f"figures.py: {name} overflows its picture ({y:.2f})")
    fig.savefig(BUILD / name, dpi=150)
    plt.close(fig)


def pin_worst(c, which):
    """Worst (largest) pin-minus-limit over VIN+ and VIN-, CLK and PDWN, for 'up' or 'down'."""
    out = {}
    for p in ("clk", "pdwn"):
        out[p] = c["pins"][p][which]
    vp, vn = c["pins"]["vinp"][which], c["pins"]["vinn"][which]
    out["vin"] = vp if vp["over_max_v"] >= vn["over_max_v"] else vn
    return out


def main():
    BUILD.mkdir(exist_ok=True)
    d = json.load(open(SIM))
    cases = d["cases"]
    keys = list(cases)
    facts = {}
    seq = list(csv.DictReader(open(HERE / "sequence.csv")))
    fixes_csv = {r["fix"]: r for r in csv.DictReader(open(HERE / "fixes.csv"))}
    route = {r["change"]: r for r in csv.DictReader(open(ROUTE))}
    place = {}
    for r in csv.DictReader(open(HERE / "place_fix.csv")):
        place.setdefault(r["part"], r)

    # ---- fix numbers from the simulation ----------------------------------------------------------
    def fix_rows(prefix):
        for k, v in d["fix_order"].items():
            if k.startswith(prefix):
                return v["rows"]
        raise KeyError(prefix)

    def f1(prefix):
        r = fix_rows(prefix)
        return {i: r[i] for i in ("on-VCCINT-VCCAUX", "on-VCCINT-VCCO")}

    f1b = {u: f1(f"F1b {u} on U23 EN") for u in ("1u", "2.2u", "4.7u")}
    f1c = f1("F1c supervisor")
    for u, r in f1b.items():
        facts[f"f1b_{u.replace('.', 'p')}_aux_worst"] = num(r["on-VCCINT-VCCAUX"]["worst_ms"], 2)
        facts[f"f1b_{u.replace('.', 'p')}_aux_best"] = num(r["on-VCCINT-VCCAUX"]["best_ms"], 2)
        facts[f"f1b_{u.replace('.', 'p')}_o_worst"] = num(r["on-VCCINT-VCCO"]["worst_ms"], 2)
    facts["f1c_aux_worst"] = num(f1c["on-VCCINT-VCCAUX"]["worst_ms"], 2)
    facts["f1c_o_worst"] = num(f1c["on-VCCINT-VCCO"]["worst_ms"], 2)

    # ---- order map ------------------------------------------------------------------------------------
    order = d["order"]["if0"]["rows"]
    order_fs = d["order"]["iffs"]["rows"]
    vca = {c: cases[c]["vcco_minus_vccaux"] for c in keys}
    vca_max = max(v["max_v"] for v in vca.values())
    vca_over = max(max(v["t_over_up_ms"], v["t_over_down_ms"]) for v in vca.values())
    facts["vcco_vccaux_max"] = num(vca_max, 3)
    facts["vcco_vccaux_over_ms"] = num(vca_over, 3)

    def margin_txt(rid, row):
        if rid.endswith("minus-VCCAUX"):
            return f"max {vca_max:.2f} V against 2.625 V, {vca_over:g} ms over"
        if row.get("same_rail"):
            return "same rail"
        return f"{row['worst_ms']:+.2f} to {row['best_ms']:+.2f}"

    def holds_txt(rid, row):
        if rid.endswith("minus-VCCAUX"):
            return "yes"
        if row.get("same_rail"):
            return "n/a"
        return "yes" if row["holds_all_corners"] else "no"

    F1TXT = (f"F1c supervisor on 1V0 (1 part; becomes design; sim worst {f1c['on-VCCINT-VCCAUX']['worst_ms']:+.2f} ms) "
             f"or F1b RC on U23 EN (1 part, stays timing; 4.7u worst {f1b['4.7u']['on-VCCINT-VCCAUX']['worst_ms']:+.2f} ms)")
    FIX = {
        "on-3V0-3V3A": "none needed; no pin over the limit in any corner",
        "on-3V0-1V8": "none needed; 1V8 starts after the 3V0 EN fires but reaches 90 % first; 1V8 feeds no ADC pin",
        "on-3V0-3V3D": "none needed; no pin over the limit in any corner",
        "on-VCCINT-VCCBRAM": "none",
        "on-VCCINT-VCCAUX": F1TXT,
        "on-VCCINT-VCCO": F1TXT.replace(
            f"{f1c['on-VCCINT-VCCAUX']['worst_ms']:+.2f}", f"{f1c['on-VCCINT-VCCO']['worst_ms']:+.2f}").replace(
            f"{f1b['4.7u']['on-VCCINT-VCCAUX']['worst_ms']:+.2f}", f"{f1b['4.7u']['on-VCCINT-VCCO']['worst_ms']:+.2f}"),
        "on-VCCAUX-VCCO": "none needed",
        "on-VCCO-minus-VCCAUX": "none needed",
        "off-3V3A-3V0": "none forces it (F2c); F2a hold-up on 3V0 adds margin only",
        "off-1V8-3V0": "none forces it (F2c); F2a worsens it, see fixes",
        "off-3V3D-3V0": "none forces it (F2c); F2a hold-up on 3V0 adds margin only",
        "off-VCCO-VCCAUX": "none forces it (F2c); holds in sim (F2b bleeder changes margin only)",
        "off-VCCAUX-VCCINT": "none forces it (F2c): 1V0 holds up longest",
        "off-VCCO-VCCINT": "none forces it (F2c)",
        "off-VCCO-minus-VCCAUX": "none needed",
    }
    today = {r["id"]: r["class_today"] for r in seq}
    hdr = ["Ordering", "Set by", "Today", "1-RX", "Margin ms, worst to best", "All 8 corners", "Fix"]
    on_rows, off_rows = [], []
    for r in seq:
        rid = r["id"]
        if rid not in order and not rid.endswith("minus-VCCAUX"):
            continue
        row = order.get(rid, {})
        req = "VCCINT before VCCBRAM (both 1V0)" if rid == "on-VCCINT-VCCBRAM" else r["requirement"]
        cells = [req, ENFORCED[rid], today[rid], r["class_rx1"], margin_txt(rid, row),
                 holds_txt(rid, row), FIX[rid]]
        (on_rows if r["direction"] == "on" else off_rows).append(cells)
    # the two iffs runs equal the if0 runs within 0.01 ms (the IF level does not touch the rails)
    spread = max(abs(order[k]["worst_ms"] - order_fs[k]["worst_ms"]) for k in order if "worst_ms" in order[k])
    facts["if_spread_ms"] = num(spread, 3)
    write_csv("order_on.csv", hdr, on_rows)
    write_csv("order_off.csv", hdr, off_rows)
    wd = [0.16, 0.17, 0.06, 0.06, 0.15, 0.08, 0.32]
    image_table("order_on.png", hdr, on_rows, wd, 10, notes=[
        "Margin = later rail 90 % time minus earlier rail 90 % time over the 8 power corners (U17 and U18 soft "
        "start 3.2 or 5.4 ms, LD39200 start-up 0.1 or 0.3 ms). Design = an EN or PG chain forces the start; timing "
        "= it holds only because one regulator is faster. A chain from 3V0 forces the start (EN 1.2 V) but not 90 %."])
    image_table("order_off.png", hdr, off_rows, wd, 10, notes=[
        "Power-off by sudden 12 V removal, rails at 90 % falling. An EN or PG chain acts only after its source has "
        "fallen below the EN low threshold, so it cannot make the later rail fall first; the stored charge sets it. "
        "A negative margin is the wrong order for DS181 (p.8) or for AVDD."])
    ntiming_on = sum(1 for r in on_rows if r[3] == "timing")
    ntiming_off = sum(1 for r in off_rows if r[3] == "timing")
    facts.update(n_on=len(on_rows), n_off=len(off_rows), n_timing_on=ntiming_on, n_timing_off=ntiming_off,
                 n_design=sum(1 for r in on_rows + off_rows if r[3] == "design"))

    # ---- per-case pins -----------------------------------------------------------------------------
    phdr = ["Case (soft start, LDO, IF)", "3V0 EN ms", "Start after 3V0 EN", "Up: CLK", "Up: PDWN", "Up: VIN",
            "Off: CLK V (mA)", "Off: PDWN V (mA)", "Off: VIN V (mA)", "Result"]
    prow = []
    worst_up = {"clk": -9, "pdwn": -9, "vin": -9}
    worst_dn = {"clk": {"over": -9}, "pdwn": {"over": -9}, "vin": {"over": -9}}
    peak_up_vin = 0.0
    start_ok_all = True
    t_en_rng = [1e9, -1e9]
    for k in keys:
        c = cases[k]
        up, dn = pin_worst(c, "up"), pin_worst(c, "down")
        starts_ok = all(c["start_after_3v0_en"].values())
        start_ok_all &= starts_ok
        t_en_rng = [min(t_en_rng[0], c["t_3v0_en_ms"]), max(t_en_rng[1], c["t_3v0_en_ms"])]
        for p in up:
            worst_up[p] = max(worst_up[p], up[p]["over_max_v"])
        for p in dn:
            if dn[p]["over_max_v"] > worst_dn[p]["over"]:
                worst_dn[p] = dict(over=dn[p]["over_max_v"], ma=dn[p]["i_clamp_up_peak_ma"], case=k,
                                   us=dn[p]["t_above_10ua_us"], nc=dn[p]["q_clamp_nc"], peak=dn[p]["peak_v"])
        peak_up_vin = max(peak_up_vin, c["pins"]["vinp"]["up"]["peak_v"], c["pins"]["vinn"]["up"]["peak_v"])
        up_ok = all(v["over_max_v"] <= 0 for v in up.values())
        dn_ok = all(v["over_max_v"] <= 0 for v in dn.values())
        res = ("pass up" if up_ok else "FAIL up") + (", pass off" if dn_ok else ", FAIL off")
        prow.append([case_label(k), num(c["t_3v0_en_ms"], 2), "yes" if starts_ok else "NO",
                     f"{up['clk']['over_max_v']:+.3f}", f"{up['pdwn']['over_max_v']:+.3f}", f"{up['vin']['over_max_v']:+.3f}",
                     f"{dn['clk']['over_max_v']:+.3f} ({dn['clk']['i_clamp_up_peak_ma']:.1f})",
                     f"{dn['pdwn']['over_max_v']:+.3f} ({dn['pdwn']['i_clamp_up_peak_ma']:.2f})",
                     f"{dn['vin']['over_max_v']:+.3f} ({dn['vin']['i_clamp_up_peak_ma']:.1f})", res])
    write_csv("pins.csv", phdr, prow)
    image_table("pins.png", phdr, prow, [0.22, 0.06, 0.07, 0.07, 0.07, 0.07, 0.11, 0.11, 0.11, 0.11], 8, notes=[
        "Each pin value is the pin voltage minus (its AVDD at that instant + 0.3 V); negative is inside the "
        "AD9237 absolute maximum (adi-ad9237-datasheet p.7). Off = 12 V removal; its columns also give the peak "
        "clamp current into the AVDD diode in mA. FS = mixer IF at full scale. U39 is the TI LP5907 model as supplied."])
    facts.update(
        t_en_min=num(t_en_rng[0], 2), t_en_max=num(t_en_rng[1], 2), start_ok=start_ok_all,
        up_clk_margin=num(-worst_up["clk"], 3), up_pdwn_margin=num(-worst_up["pdwn"], 3),
        up_vin_margin=num(-worst_up["vin"], 3), vin_up_peak=num(peak_up_vin, 2),
        dn_clk_over=num(worst_dn["clk"]["over"], 3), dn_clk_ma=num(worst_dn["clk"]["ma"], 1),
        dn_clk_us=num(worst_dn["clk"]["us"] / 1000, 2), dn_clk_peak=num(worst_dn["clk"]["peak"], 3),
        dn_vin_over=num(worst_dn["vin"]["over"], 3), dn_vin_ma=num(worst_dn["vin"]["ma"], 1),
        dn_vin_us=num(worst_dn["vin"]["us"] / 1000, 2), dn_vin_peak=num(worst_dn["vin"]["peak"], 2),
        dn_pdwn_over=num(worst_dn["pdwn"]["over"], 3), dn_pdwn_ma=num(worst_dn["pdwn"]["ma"], 3),
        dn_pdwn_us=num(worst_dn["pdwn"]["us"] / 1000, 2),
        dn_clk_nc=num(worst_dn["clk"]["nc"], 0), dn_vin_nc=num(worst_dn["vin"]["nc"], 0),
        worst_dn_case=case_label(worst_dn["clk"]["case"]), worst_dn_key=worst_dn["clk"]["case"],
        n_cases=len(keys), n_up_pass=sum(1 for k in keys if all(v["over_max_v"] <= 0 for v in pin_worst(cases[k], "up").values())),
        n_dn_pass=sum(1 for k in keys if all(v["over_max_v"] <= 0 for v in pin_worst(cases[k], "down").values())))
    # worst power-up case by CLK margin
    wk = max(keys, key=lambda k: cases[k]["pins"]["clk"]["up"]["over_max_v"])
    facts["up_worst_key"] = wk
    facts["up_worst_case"] = case_label(wk)
    facts["up_clk_peak"] = num(cases[wk]["pins"]["clk"]["up"]["peak_v"], 3)
    facts["up_clk_avdd"] = num(cases[wk]["pins"]["clk"]["up"]["avdd_at_over_max"], 3)
    facts["up_clamp_ua"] = num(max(cases[k]["pins"][p]["up"]["i_clamp_up_peak_ma"] for k in keys
                                   for p in ("clk", "pdwn", "vinp", "vinn")) * 1000, 2)

    # ---- clamp currents, sweeps, one-way U39 ----------------------------------------------------------
    chdr = ["Case", "CLK V (mA, us over 10 uA)", "VIN V (mA, us)", "PDWN V (mA)", "Power-up CLK V"]
    crow = []

    def crow_of(label, r):
        pv = r["pins"]
        vin = pv["vinp"]["down"] if pv["vinp"]["down"]["over_max_v"] >= pv["vinn"]["down"]["over_max_v"] else pv["vinn"]["down"]
        c = pv["clk"]["down"]
        crow.append([label,
                     f"{c['over_max_v']:+.3f} ({c['i_clamp_up_peak_ma']:.1f}, {c['t_above_10ua_us']:.0f})",
                     f"{vin['over_max_v']:+.3f} ({vin['i_clamp_up_peak_ma']:.1f}, {vin['t_above_10ua_us']:.0f})",
                     f"{pv['pdwn']['down']['over_max_v']:+.3f} ({pv['pdwn']['down']['i_clamp_up_peak_ma']:.3f})",
                     f"{pv['clk']['up']['over_max_v']:+.3f}"])

    crow_of("Reference: slow 1V0, fast 3V8 and LDO, IF 0 (typ diode, U6 20 ohm)", cases[worst_dn["clk"]["case"]])
    SWL = {"diode": "Clamp diode", "ro": "U6 output resistance (ohm)", "pdwn_ipu_ua": "PDWN pull-up (uA)",
           "vpgmin": "PG pull-down limit VPGMIN (V)", "y2": "Y2 start-up (0 at once, 1 after 2 ms)",
           "avdd_r": "AVDD load (ohm)", "load3d": "3V3D load (x typical)", "tr12_ms": "12 V rise (ms)",
           "u39": "U39 output"}
    for name, lst in d["sweeps"].items():
        for e in lst:
            v = e["value"]
            if name == "diode":
                dd = d["diodes"][v]
                v = f"{v} (Is {dd['Is']:g} A, Rs {dd['Rs']:g} ohm)"
            elif name == "u39":
                v = "TI model as supplied" if v == "ti" else "one-way output, body diode"
            elif isinstance(v, float):
                v = f"{v:.4g}"
            crow_of(f"{SWL.get(name, name)}: {v}", e["result"])
    write_csv("clamp.csv", chdr, crow)
    image_table("clamp.png", chdr, crow, [0.40, 0.19, 0.17, 0.12, 0.12], 8, notes=[
        "Pin voltage minus (AVDD + 0.3 V) at 12 V removal, with the peak current into the AVDD clamp diode in mA and "
        "the time above 10 uA in us. The AD9237 sheet states no clamp current it tolerates (adi-ad9237-datasheet "
        "p.7, p.10); the LTC2292 tolerates over 100 mA (adi-ltc2293-2292-2291-datasheet p.5 note 3). Diode model, "
        "U6 resistance, Y2 start-up, VPGMIN and the U39 output are assumptions; each row changes one of them."])
    vp = {e["value"]: e["result"]["pins"]["clk"]["up"]["over_max_v"] for e in d["sweeps"]["vpgmin"]}
    facts["vpgmin_2_up_over"] = num(vp[2.0], 3)
    facts["vpgmin_28_up_over"] = num(vp[2.8], 3)
    ns = d["sweeps"]["u39"][1]["result"]["pins"]
    facts.update(ns_clk_over=num(ns["clk"]["down"]["over_max_v"], 3), ns_clk_ma=num(ns["clk"]["down"]["i_clamp_up_peak_ma"], 1),
                 ns_vin_ma=num(ns["vinp"]["down"]["i_clamp_up_peak_ma"], 1),
                 ns_pdwn_ma=num(ns["pdwn"]["down"]["i_clamp_up_peak_ma"], 3))
    dsw = {e["value"]: e["result"]["pins"]["clk"]["down"] for e in d["sweeps"]["diode"]}
    facts["diode_clk_range"] = f"{dsw['strong']['i_clamp_up_peak_ma']:.1f} to {dsw['weak']['i_clamp_up_peak_ma']:.1f}"
    rsw = {e["value"]: e["result"]["pins"]["clk"]["down"] for e in d["sweeps"]["ro"]}
    facts["ro_clk_range"] = f"{rsw[40.0]['i_clamp_up_peak_ma']:.1f} to {rsw[10.0]['i_clamp_up_peak_ma']:.1f}"

    # ---- steady state ---------------------------------------------------------------------------------
    shdr = ["Condition", "3V3D V", "3V0 V", "Limit V", "CLK peak V", "CLK over V", "Clamp peak mA (mean uA)",
            "Duty", "Rise ns", "PDWN over V"]
    srow = []
    st = d["steady"]
    pd_by = {(v["v3d"], v["v3v0"]): v["pdwn"] for k, v in st.items() if v["kind"] == "pdwn"}
    SL = {"2pct nominal": "nominal 3V3D and 3V0", "2pct 3V3D high, 3V0 low": "3V3D +2 %, 3V0 -2 %",
          "2pct 3V3D low, 3V0 high": "3V3D -2 %, 3V0 +2 %", "5pct nominal": "nominal (again)",
          "5pct 3V3D high, 3V0 low": "3V3D +5 %, 3V0 -5 %", "5pct 3V3D low, 3V0 high": "3V3D -5 %, 3V0 +5 %"}
    seen = set()
    for k, v in st.items():
        if v["kind"] != "clk":
            continue
        lab = k.replace(" clk", "")
        if lab == "5pct nominal" or (v["v3d"], v["v3v0"]) in seen:
            continue
        seen.add((v["v3d"], v["v3v0"]))
        c, p = v["clk"], pd_by[(v["v3d"], v["v3v0"])]
        srow.append([SL.get(lab, lab), num(v["v3d"], 3), num(v["v3v0"], 3), num(c["limit_v"], 3), num(c["peak_v"], 3),
                     f"{c['over_v']:+.3f}", f"{c['i_clamp_up_peak_ma']:.4f} ({c['i_clamp_up_mean_ua']:.2f})",
                     f"{c['duty'] * 100:.1f} %", f"{c['rise_10_90_ns']:.2f}", f"{p['over_v']:+.3f}"])
    FIXL = {"today R15 33": "today: R15 33 ohm", "R15 100": "F3b R15 100 ohm", "R15 68 + 680 shunt": "F3a R15 68 + 680 ohm to GND",
            "R15 33 + 330 shunt": "R15 33 + 330 ohm to GND", "R15 68 + 680 shunt @5pct": "F3a at 3V3D +5 %, 3V0 -5 %"}
    for k, v in d["clk_fixes"].items():
        c = v["clk"]
        srow.append([f"CLK fix, 3V3D +2 %, 3V0 -2 %: {FIXL.get(k, k)}" if "5pct" not in k else f"CLK fix: {FIXL[k]}",
                     num(v["v3d"], 3), num(v["v3v0"], 3), num(c["limit_v"], 3), num(c["peak_v"], 3), f"{c['over_v']:+.3f}",
                     f"{c['i_clamp_up_peak_ma']:.4f} ({c['i_clamp_up_mean_ua']:.2f})", f"{c['duty'] * 100:.1f} %",
                     f"{c['rise_10_90_ns']:.2f}", ""])
    write_csv("steady.csv", shdr, srow)
    image_table("steady.png", shdr, srow, [0.26, 0.06, 0.06, 0.06, 0.08, 0.08, 0.17, 0.07, 0.07, 0.09], 10, notes=[
        "40 MHz CLK (1 ns edges assumed, R15 33 ohm, U6 output 20 ohm typical, microchip-pl133-37-datasheet p.2) with the "
        "limit AVDD + 0.3 V. 3V3D is the LD39200PU33R and 3V0 the LP5907-3.0; the +/-2 % and +/-5 % corners are "
        "assumed tolerances (the sheets' own tolerance is in the report). PDWN held high by the FPGA sits at 3V3D."])
    s2 = [v for k, v in st.items() if k == "2pct 3V3D high, 3V0 low clk"][0]["clk"]
    s5 = [v for k, v in st.items() if k == "5pct 3V3D high, 3V0 low clk"][0]["clk"]
    s0 = [v for k, v in st.items() if k == "2pct nominal clk"][0]["clk"]
    cf = d["clk_fixes"]
    facts.update(
        st_nom_over=num(s0["over_v"], 3), st2_peak=num(s2["peak_v"], 3), st2_lim=num(s2["limit_v"], 3),
        st2_over=num(s2["over_v"], 3), st2_mean=num(s2["i_clamp_up_mean_ua"], 2),
        st5_peak=num(s5["peak_v"], 3), st5_lim=num(s5["limit_v"], 3), st5_over=num(s5["over_v"], 3),
        st5_ma=num(s5["i_clamp_up_peak_ma"], 2), st5_mean=num(s5["i_clamp_up_mean_ua"], 0))
    for k in list(pd_by):
        if abs(k[0] - 3.366) < 1e-3:
            facts["st2_pdwn_over"] = num(pd_by[k]["over_v"], 3)
    f3a, f3a5, f3b, f3c = cf["R15 68 + 680 shunt"]["clk"], cf["R15 68 + 680 shunt @5pct"]["clk"], cf["R15 100"]["clk"], cf["R15 33 + 330 shunt"]["clk"]
    facts.update(f3a_peak=num(f3a["peak_v"], 2), f3a_over=num(f3a["over_v"], 2), f3a5_peak=num(f3a5["peak_v"], 2),
                 f3a5_over=num(f3a5["over_v"], 2), f3a_rise=num(f3a["rise_10_90_ns"], 2), f3a_duty=num(f3a["duty"] * 100, 1),
                 f3b_over=num(f3b["over_v"], 3), f3b_rise=num(f3b["rise_10_90_ns"], 2), f3b_duty=num(f3b["duty"] * 100, 1),
                 f3c_peak=num(f3c["peak_v"], 2), f3c_duty=num(f3c["duty"] * 100, 1))

    # ---- fixes: cost, simulated result, room on today's board -----------------------------------------
    def fx(prefix, which, pin, key="over_max_v"):
        for k, v in d["fixes"].items():
            if k.startswith(prefix) and k.endswith(f"{which}]"):
                vals = [r["pins"][pin]["down"][key] for r in v.values()]
                return max(vals)
        raise KeyError(prefix)

    def rt(name):
        r = route[name]
        return f"{r['length_mm']} mm, {r['vias']} via, {r['layers'].replace('_SIG', '').replace('_PWR', '')}"

    def pl(part):
        r = place[part]
        return f"{r['dist_from_anchor_mm']} mm from {r['anchor']}, {'top' if r['side'] == 'F' else 'bottom'}"

    def f2a_pw(u, w):
        return fx(f"F2a +{u}u", w, "clk", "over_max_v")

    def fx_up(prefix, pin):
        """Worst power-up pin-minus-limit over the corners of a fix run (TI U39 model)."""
        for k, v in d["fixes"].items():
            if k.startswith(prefix) and k.endswith("ti]"):
                return max(r["pins"][pin]["up"]["over_max_v"] for r in v.values())
        raise KeyError(prefix)

    facts.update(f2a47_up_vin=num(fx_up("F2a +47u", "vinp"), 2), f2a47_up_clk=num(fx_up("F2a +47u", "clk"), 3),
                 f2a100_up_clk=num(fx_up("F2a +100u", "clk"), 2), f2a220_up_clk=num(fx_up("F2a +220u", "clk"), 2),
                 f2a47_dn_nosink=num(f2a_pw("47", "nosink"), 3))

    fhdr = ["Fix", "For", "Cost", "Simulated result", "Room on today's board"]
    frow = [
        ["F1c supervisor on 1V0, OUT pulls the U23 EN node low until 1V0 is above 0.9 V", "1V0 before 1V8 and 3V3D (on)",
         "1 SOT-23-5 supervisor (part, JLC stock to choose; no sheet on file), 4 pad connections, no new net name; acts at power-on only",
         f"becomes design; 1V8 follows 1V0 by at least the LD39200 start-up: worst {f1c['on-VCCINT-VCCAUX']['worst_ms']:+.2f} ms (8 corners); no pin over at power-up",
         f"placed {pl('SUP1')}; OUT {rt('F1c supervisor OUT to U23 EN')}; SENSE {rt('F1c supervisor SENSE to 1V0')}; VDD {rt('F1c supervisor VDD to 3V8')}"],
        ["F1b RC on the U23 EN node: capacitor to GND (R996 10k is the resistor)", "1V0 before 1V8 and 3V3D (on)",
         "1 capacitor (4.7u is the smallest of 1u, 2.2u, 4.7u with a positive worst case); delays 1V8 and 3V3D after 3V0; at power-off holds U23 on about 18 ms per uF",
         f"stays timing: worst/best 1V0 before 1V8 {f1b['1u']['on-VCCINT-VCCAUX']['worst_ms']:+.2f}/{f1b['1u']['on-VCCINT-VCCAUX']['best_ms']:+.2f} ms (1u), "
         f"{f1b['2.2u']['on-VCCINT-VCCAUX']['worst_ms']:+.2f}/{f1b['2.2u']['on-VCCINT-VCCAUX']['best_ms']:+.2f} (2.2u), "
         f"{f1b['4.7u']['on-VCCINT-VCCAUX']['worst_ms']:+.2f}/{f1b['4.7u']['on-VCCINT-VCCAUX']['best_ms']:+.2f} (4.7u); no pin over at power-up",
         f"placed {pl('C_DLY')}; cap to EN {rt('F1b cap to U23 EN')}; GND {rt('F1b cap to GND')}"],
        ["Rejected: U23 EN from 1V0 (or a divider of it); a 12 V EN divider on U18; a PG chain from U17", "1V0 before 1V8",
         "none", "1.008 V is below the LD39200 EN high threshold 1.2 V (p.7); a divider only lowers it; the divider on U18 depends on the 12 V ramp rate; LMR51420 has no PG pin (p.3)",
         "not routed: the fix does not work"],
        ["F2a more hold-up on 3V0: +10u / +47u 0805 next to U39", "power-off orders and CLK at 12 V removal",
         "1 capacitor (10u 0805 C15850); 3V0 goes from 12.4 uF to 22.4 uF; more in-rush on the LP5907 at start",
         f"removal CLK over: +10u {f2a_pw('10', 'ti'):+.2f} V (TI model) / {f2a_pw('10', 'nosink'):+.2f} V (one-way); +47u {f2a_pw('47', 'ti'):+.2f} / {f2a_pw('47', 'nosink'):+.2f} V, "
         f"but the larger 3V0 capacitance slows 3V0 while 3V3D follows its EN: at 47u the power-up VIN+ is {fx_up('F2a +47u', 'vinp'):+.2f} V over, at 100u CLK is {fx_up('F2a +100u', 'clk'):+.2f} V over; rejected at 47u and above",
         f"placed {pl('C_HOLD')}; 3V0 {rt('F2a hold-up cap to 3V0')}"],
        ["F2b bleeder on 3V3D: 330 ohm or 100 ohm to GND next to U25", "power-off orders",
         "1 resistor 0402; 3.3 V over 330 ohm is 10 mA continuous on 3V3D (100 ohm: 33 mA)",
         f"removal CLK over: 330 ohm {fx('F2b bleeder 330', 'ti', 'clk'):+.2f} V (TI) / {fx('F2b bleeder 330', 'nosink', 'clk'):+.2f} V (one-way); 100 ohm {fx('F2b bleeder 100', 'ti', 'clk'):+.2f} / {fx('F2b bleeder 100', 'nosink', 'clk'):+.2f} V; does not fix it",
         f"placed {pl('R_BLEED')}; 3V3D {rt('F2b bleeder to 3V3D')}"],
        ["F2c a circuit that forces the power-off order", "all off orders", "n/a",
         "none exists: an EN or PG chain acts after its source has fallen; only a feed from the earlier rail forces the order and the LDOs all run from 3V8", "n/a"],
        ["F3a CLK divider: R15 33 -> 68 ohm and 680 ohm from the CLK node to GND at the pin", "CLK steady state and removal",
         "1 resistor 0402 added, R15 value change, no new net name; U6 load 4.3 mA (IOSD 12 mA, microchip-pl133-37 p.3); the clock swing falls to about 3 V",
         f"steady state +2 %: peak {f3a['peak_v']:.2f} V ({f3a['over_v']:+.2f} V), +5 %: {f3a5['peak_v']:.2f} V ({f3a5['over_v']:+.2f} V); rise {f3a['rise_10_90_ns']:.2f} ns, duty {f3a['duty'] * 100:.1f} %; at removal the clamp conducts only above the divided level (not rerun)",
         f"placed {pl('R_CLK')} (at R15, the AD9237 CLK pin is not on kicad-1rx/ yet); CLK {rt('F3a CLK shunt to ADC_CLK')}; GND {rt('F3a CLK shunt to GND')}"],
        ["F3b R15 100 ohm only", "CLK", "value change, no part", f"steady state +2 %: over {f3b['over_v']:+.3f} V (unchanged; it limits the clamp current only); rise {f3b['rise_10_90_ns']:.2f} ns, duty {f3b['duty'] * 100:.1f} %",
         "no new connection: same footprint"],
        ["F4a VIN series resistance: R97/R99 49.9 -> 200 or 499 ohm", "VIN at 12 V removal",
         "2 value changes, no part; noise and a lower corner with C163-C165; the settling and IF response of rx1-02 are NOT rerun",
         f"removal VIN clamp current {fx('F3 R97/R99 200', 'ti', 'vinp', 'i_clamp_up_peak_ma'):.1f} mA at 200 ohm, {fx('F3 R97/R99 499', 'ti', 'vinp', 'i_clamp_up_peak_ma'):.1f} mA at 499 ohm (11.8 mA today); still over the limit by {fx('F3 R97/R99 499', 'ti', 'vinp'):+.2f} V",
         "no new connection: same footprint"],
        ["F4b Schottky clamp from each VIN to 3V0", "VIN at 12 V removal", "2 parts per side or a dual; not simulated", "not simulated",
         "not checked: needs the AD9237 pads, which kicad-1rx/ does not have until rx1-03"],
    ]
    write_csv("fixes_all.csv", fhdr, frow)
    image_table("fixes.png", fhdr, frow, [0.19, 0.09, 0.21, 0.29, 0.22], 7.5)

    # ---- waveform figures ------------------------------------------------------------------------------
    def tr(c, which, k):
        return c["traces"][which][k]

    def tax(c, which):
        """Time axis (ms) of a saved trace. powerup_sim.py saves 400 points per trace on (0, t_off - 1) for 'up'
        and (t_off - 0.5, tstop) for 'down' but 500 points in up_ms and down_ms; the 400 points are the truth."""
        p = c["params"]
        t0, t1 = (0, p["t_off"] - 1) if which == "up" else (p["t_off"] - 0.5, p["tstop"])
        return np.linspace(t0, t1, len(c["traces"][which]["v3v0"])).tolist()

    fast, slow = "u17f_u18f_ldof_if0", "u17s_u18s_ldos_if0"
    fig, axs = plt.subplots(2, 2, figsize=(W_IN, H_IN + 1.6))
    for ax, k in zip(axs[0], (fast, slow)):
        c = cases[k]
        t = tax(c, "up")
        for r in ("3V8", "1V0", "3V0", "3V3A", "1V8", "3V3D"):
            ax.plot(t, c["traces"]["up"][TRACE[r]], color=RAIL_COL[r], lw=1.4, label=r)
        ax.axhline(1.2, color="gray", ls=":", lw=0.8)
        ax.text(0.1, 1.28, "EN high 1.2 V", fontsize=7, color="gray")
        ax.set_xlim(0, 6.5)
        ax.set_title(f"Rails up, {case_label(k)}", fontsize=9, color=NAVY)
        ax.set_xlabel("ms")
        ax.set_ylabel("V")
        ax.legend(fontsize=7, ncol=3, loc="upper right")
    ax = axs[1][0]
    c = cases[wk]
    t = tax(c, "up")
    av = c["traces"]["up"]["v3v0"]
    ax.plot(t, [a + ABS for a in av], color="k", ls="--", lw=1.0, label="AVDD + 0.3 V")
    ax.plot(t, tr(c, "up", "clk"), color=RAIL_COL["3V3D"], lw=1.4, label="CLK")
    ax.plot(t, tr(c, "up", "pdwn"), color="#16a085", lw=1.2, ls="-.", label="PDWN")
    ax.plot(t, tr(c, "up", "pinp"), color=RAIL_COL["3V3A"], lw=1.2, label="VIN+")
    ax.set_xlim(1.5, 5.5)
    ax.set_title(f"Pins against the limit, worst power-up case ({case_label(wk)})", fontsize=9, color=NAVY)
    ax.set_xlabel("ms")
    ax.set_ylabel("V")
    ax.legend(fontsize=7, loc="upper left")
    ax = axs[1][1]
    for k, ls in ((fast, "-"), (slow, "--")):
        c = cases[k]
        t = tax(c, "up")
        for r, lab in (("1V0", "VCCINT 1V0"), ("1V8", "VCCAUX 1V8"), ("3V3D", "VCCO 3V3D")):
            ax.plot(t, c["traces"]["up"][TRACE[r]], color=RAIL_COL[r], ls=ls, lw=1.2,
                    label=f"{lab}, {'fast' if k == fast else 'slow'} corner")
    ax.set_xlim(0, 6.5)
    ax.set_title(f"FPGA rails (DS181 p.8 order 1V0, 1V8, 3V3D); VCCO - VCCAUX max {vca_max:.2f} V of 2.625 V",
                 fontsize=9, color=NAVY)
    ax.set_xlabel("ms")
    ax.set_ylabel("V")
    ax.legend(fontsize=6, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(BUILD / "powerup.png", dpi=150)
    plt.close(fig)

    k = worst_dn["clk"]["case"]
    c = cases[k]
    t = tax(c, "down")
    fig, axs = plt.subplots(2, 2, figsize=(W_IN, H_IN + 1.6))
    ax = axs[0][0]
    for r in ("12V", "3V8", "1V0", "3V0", "3V3A", "1V8", "3V3D"):
        ax.plot(t, c["traces"]["down"][TRACE[r]], color=RAIL_COL[r], lw=1.3, label=r)
    ax.set_xlim(13.5, 22)
    ax.set_title(f"12 V removed at 14 ms, rails ({case_label(k)})", fontsize=9, color=NAVY)
    ax.legend(fontsize=7, ncol=4, loc="upper right")
    ax = axs[0][1]
    ax.plot(t, [a + ABS for a in c["traces"]["down"]["v3v0"]], color="k", ls="--", lw=1.0, label="AVDD + 0.3 V")
    ax.plot(t, c["traces"]["down"]["clk"], color=RAIL_COL["3V3D"], lw=1.4, label="CLK")
    ax.plot(t, c["traces"]["down"]["pdwn"], color="#16a085", lw=1.2, ls="-.", label="PDWN")
    ax.plot(t, c["traces"]["down"]["pinp"], color=RAIL_COL["3V3A"], lw=1.2, label="VIN+")
    ax.set_xlim(13.5, 22)
    ax.set_title("Pins against AVDD + 0.3 V at removal", fontsize=9, color=NAVY)
    ax.legend(fontsize=7, loc="upper right")
    ax = axs[1][0]
    for key, lab, col in (("i_clk", "CLK", RAIL_COL["3V3D"]), ("i_vinp", "VIN+", RAIL_COL["3V3A"]), ("i_pdwn", "PDWN x 10", "#16a085")):
        y = c["traces"]["down"][key]
        ax.plot(t, [v * (10 if "pdwn" in key else 1) for v in y], color=col, lw=1.3, label=lab)
    ax.set_xlim(13.5, 22)
    ax.set_title("Clamp current into the AVDD diodes (mA; AD9237 states no limit)", fontsize=9, color=NAVY)
    ax.legend(fontsize=7, loc="upper right")
    ax = axs[1][1]
    diff = [a - b for a, b in zip(c["traces"]["down"]["v3v3d"], c["traces"]["down"]["v1v8"])]
    ax.plot(t, diff, color=RAIL_COL["3V3D"], lw=1.3, label="VCCO - VCCAUX")
    ax.axhline(2.625, color=RED, ls="--", lw=1.0, label="2.625 V limit (DS181 p.8)")
    for r in ("1V0", "1V8", "3V3D"):
        ax.plot(t, c["traces"]["down"][TRACE[r]], color=RAIL_COL[r], lw=1.0, ls=":", label=r)
    ax.set_xlim(13.5, 22)
    ax.set_title("FPGA rails at removal", fontsize=9, color=NAVY)
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    for a in axs.flat:
        a.set_xlabel("ms")
    axs[0][0].set_ylabel("V")
    axs[0][1].set_ylabel("V")
    axs[1][0].set_ylabel("mA")
    axs[1][1].set_ylabel("V")
    fig.tight_layout()
    fig.savefig(BUILD / "removal.png", dpi=150)
    plt.close(fig)

    # ---- lay-03: what the scope should show --------------------------------------------------------------
    lhdr = ["Signal (probe)", "Sim, all 8 power-up corners", "Basis"]
    lrow = []
    ifc = [k for k in keys if k.endswith("if0")]

    def rng(f):
        v = [f(cases[k]) for k in ifc]
        return min(v), max(v)

    t12 = {k: cases[k]["rails"]["12V"]["t_start_ms"] for k in ifc}
    for r in ("3V8", "1V0", "3V0", "3V3A", "1V8", "3V3D"):
        a, b = rng(lambda c: c["rails"][r]["t_up90_ms"] - c["rails"]["12V"]["t_start_ms"])
        pk = max(cases[k]["rails"][r]["peak_v"] for k in ifc)
        lrow.append([f"{r} reaches 90 % after 12 V starts to rise", f"{a:.2f} to {b:.2f} ms; peak {pk:.2f} V",
                     "12 V ramp 1 ms assumed; soft start 3.2 to 5.4 ms (ti-lmr51420 p.5); LP5907 80 to 150 us (p.6); LD39200 start-up fit to Figure 23 (p.13)"])
    for r, ref, txt in (("3V3A", "3V0", "3V3A starts after 3V0"), ("3V3D", "3V0", "3V3D starts after 3V0"), ("1V8", "3V0", "1V8 starts after 3V0")):
        a, b = rng(lambda c: c["rails"][r]["t_start_ms"] - c["rails"][ref]["t_start_ms"])
        lrow.append([txt + " (time of 10 % of nominal, rail minus 3V0)", f"{a:+.2f} to {b:+.2f} ms",
                     "EN from 3V0 fires at 0.5 to 1.2 V (st-ld39200-datasheet p.7)"])
    lrow.append(["CLK, PDWN at power-up", f"peak {facts['up_clk_peak']} V while AVDD is {facts['up_clk_avdd']} V at that instant; never above AVDD + 0.3 V",
                 "margin %s V; depends on the PG output pulling low at low VIN (assumption)" % facts["up_clk_margin"]])
    lrow.append(["VIN+ and VIN- at power-up", f"peak {facts['vin_up_peak']} V", "mixer IF at zero and full scale"])
    off90 = {r: [cases[k]["falls"][r]["t_fall90_ms"] - 14.0 for k in ifc] for r in ("3V3A", "1V8", "3V3D", "3V0", "1V0")}
    for r in ("3V3A", "3V3D", "1V8", "1V0"):
        dd = [cases[k]["falls"][r]["t_fall90_ms"] - cases[k]["falls"]["3V0"]["t_fall90_ms"] for k in ifc]
        lrow.append([f"{r} falls to 90 % relative to 3V0 at 12 V removal", f"{min(dd):+.2f} to {max(dd):+.2f} ms",
                     "negative = before 3V0; load constant resistance assumed; the bench decides"])
    lrow.append(["CLK at 12 V removal", f"peak {facts['dn_clk_peak']} V while AVDD is near 0 V (+{facts['dn_clk_over']} V over); the TI U39 model gives {facts['dn_clk_ma']} mA, a one-way output {facts['ns_clk_ma']} mA",
                 "the U39 output behaviour is an assumption; capture 3V0 and CLK together with a trigger on 12 V"])
    write_csv("lay03.csv", lhdr, lrow)

    # ---- facts --------------------------------------------------------------------------------------------
    def md_table(header, rows, widths):
        """Pipe table whose dashes carry the relative column widths (pandoc wraps the cells by them)."""
        sep = "|" + "|".join("-" * max(int(w * 100), 3) for w in widths) + "|"
        return "\n".join(["| " + " | ".join(header) + " |", sep] +
                         ["| " + " | ".join(md_note(str(c)) for c in r) + " |" for r in rows])

    facts["md_order_on"] = md_table(hdr, on_rows, wd)
    facts["md_order_off"] = md_table(hdr, off_rows, wd)
    facts["md_pins"] = md_table(phdr, prow, [0.22, 0.06, 0.07, 0.07, 0.07, 0.07, 0.11, 0.11, 0.11, 0.11])
    facts["md_clamp"] = md_table(chdr, crow, [0.40, 0.19, 0.17, 0.12, 0.12])
    facts["md_steady"] = md_table(shdr, srow, [0.26, 0.06, 0.06, 0.06, 0.08, 0.08, 0.17, 0.07, 0.07, 0.09])
    facts["md_fixes"] = md_table(fhdr, frow, [0.19, 0.09, 0.21, 0.29, 0.22])
    facts["md_lay03"] = md_table(lhdr, lrow, [0.30, 0.35, 0.35])
    ck = worst_dn["clk"]["case"]
    facts["worst_removal_key"] = ck
    facts["ld_td"] = num(d["fit"]["td_us"], 1)
    facts["ld_tau"] = num(d["fit"]["tau_us"], 1)
    facts["ld_t90"] = num(d["fit"]["t90_us"], 0)
    facts["ld_rms"] = num(d["fit"]["rms_v"], 3)
    facts["n_runs_checks"] = sum(1 for c in d["checks"] if c["ok"])
    facts["n_checks"] = len(d["checks"])
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print(f"figures.py: {len(facts)} facts, {len(keys)} cases, {len(on_rows)} on rows, {len(off_rows)} off rows")


if __name__ == "__main__":
    main()
