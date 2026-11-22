"""Figures, tables and facts for the 1-RX board report (rx1-02 step 7).

Run by tools/build_report.py with this folder as the working directory; writes into build/.
Nothing here runs a simulator or reads kicad/: every number comes from the result files of steps
3 to 6 (sim/adc_input.json, sim/rx2_dnp.json, sim/stock_lines.json, sim/data_path.json) and from
adc_numbers.py / rx1_changes.py, so the figures regenerate with plain Python. The pin map is data
below, each row with its manifest id and PDF page (runs/rx1-02/notes.md step 2).
"""
import csv
import importlib.util
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
SIMD = HERE / "sim"
NAVY, RED, GREEN, BLUE, GREY = "#1f2a44", "#c0392b", "#2e7d32", "#1f6fb2", "#888888"
AD = "adi-ad9237-datasheet"
FW_COMMIT = "cb7f097eaf21b407d9dcd2f65e28b1143f1d12d5"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def jload(name):
    return json.loads((SIMD / name).read_text())


# ------------------------------------------------------------------------------ table pictures
def wrap(text, width_in, fs, width_em=0.56):
    n = max(int((width_in * 72 - 6) / (fs * width_em)), 6)
    return textwrap.wrap(str(text), n) or [""]


def table_image(name, cols, rows, widths, fs, fig=(12.1, 5.4), bold_first=False):
    """Draw a table into one picture; SystemExit when it overflows the picture."""
    w_in, h_in = fig
    f = plt.figure(figsize=fig)
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_in)
    ax.set_ylim(h_in, 0)
    ax.axis("off")
    lh = fs * 1.28 / 72
    y = 0.03

    def draw(cells, bold=False, fill=None):
        nonlocal y
        wr = [wrap(t, w * w_in, fs) for t, w in zip(cells, widths)]
        h = max(len(x) for x in wr) * lh + 0.05
        if fill:
            ax.add_patch(Rectangle((0, y), w_in, h, color=fill, lw=0))
        x = 0.04
        for ci, (lines, w) in enumerate(zip(wr, widths)):
            for k, ln in enumerate(lines):
                ax.text(x, y + 0.03 + k * lh, ln, va="top", fontsize=fs, color=NAVY,
                        fontweight="bold" if bold or (bold_first and ci == 0) else "normal")
            x += w * w_in
        y += h

    draw(cols, bold=True, fill="#dfe4ee")
    for i, r in enumerate(rows):
        draw(r, fill="#f4f6fa" if i % 2 else None)
    if y > h_in:
        raise SystemExit(f"figures.py: {name} overflows its picture ({y:.2f} of {h_in} in)")
    f.savefig(BUILD / name, dpi=150)
    plt.close(f)


def write_csv(name, header, rows):
    with open(BUILD / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ------------------------------------------------------------------------------ the pin map
PIN_COLS = ["U8 net (LTC2292 pins)", "AD9237 pin", "Strap or action", "Source"]
PIN_ROWS_1 = [
    ["3V0 (VDD 7, 10, 18, 63)", "AVDD 27, 32", "same 3V0 rail (U39); 2.7 to 3.6 V", f"{AD} p.8, p.3 (Table 1)"],
    ["3V3D (OVDD 32, 49)", "DRVDD 16", "stays 3V3D; 2.25 to 3.6 V, drives 3.3 V logic", f"{AD} p.8, p.3, p.21"],
    ["GND (17, 64; OGND 31, 50; pad 65)", "AGND 28, 31; DGND 15; paddle", "paddle to the ground plane", f"{AD} p.8"],
    ["ADC_CLK (CLKA 8, CLKB 9)", "CLK 2", "R15 33 ohm kept; MUX net removed (no MUX pin; R21 not fitted); "
                                          "CLK high 2.0 V min", f"{AD} p.8, p.4 (Table 2), p.7 (Table 5)"],
    ["D0..D11 (DA0..DA11, 43-48, 51-56)", "D0 7, D1 8, D2 9, D3 10, D4 11, D5 12, D6 13, D7 14, D8 17, D9 18, "
                                          "D10 19, D11 (MSB) 20", "FPGA nets unchanged", f"{AD} p.8"],
    ["OFA (57)", "OTR 21", "same polarity (high = out of range)", f"{AD} p.8, p.21 (Table 11)"],
    ["ADC_OE1 (OEA 58)", "OE 3", "active low; the FPGA holds 0 (control.vhd 121, 193), so outputs enabled",
     f"{AD} p.8, p.21"],
    ["ADC_SHDN1 (SHDNA 59)", "PDWN 4", "GND = run; the FPGA holds 0 (control.vhd 122, 194); abs max AVDD + 0.3 V",
     f"{AD} p.20 (Table 9), p.7"],
    ["AINA+ / AINA- (1, 2): chain from P1", "VIN+ 29, VIN- 30",
     "R97/R99 49.9 ohm and C163-C165 100 pF kept (the simulated network); 7 pF per pin",
     f"{AD} p.8, p.3; p.16-17"],
]
PIN_ROWS_2 = [
    ["SENSEA (62), R93 to 3V0", "SENSE 23", "R93 now to AGND: internal VREF 1.0 V", f"{AD} p.18 (Table 7)"],
    ["(new)", "MODE2 1", "AGND: span factor 2, power scaling off", f"{AD} p.20 (Table 8)"],
    ["span", "-", "4 x VREF / 2 = 2.0 V p-p = +/-1 V: the LTC2292's SENSE = VDD span", f"{AD} p.18, p.3; "
                                                                                       "adi-ltc2292-datasheet p.15, p.3"],
    ["MODE (60), R91 4.7k / R92 10k", "MODE 22", "kept: 1.95 V with the 70 kohm pull-down = 0.65 AVDD against the "
                                                  "2/3 AVDD row (twos complement, DCS on); R92 = 11k gives 0.669",
     f"{AD} p.21 (Table 10), p.10"],
    ["(new)", "GC 5", "AGND: no gray code. Firmware reads signed twos complement (adc.vhd 98-100)", f"{AD} p.21, p.8"],
    ["(new)", "VREF 24", "0.1 uF and 10 uF to AGND (C992, C993); 2 mA max load", f"{AD} p.18 (Figure 39), p.19"],
    ["REFHA 3, 4; REFLA 5, 6", "REFT 26; REFB 25", "0.1 uF each to AGND (C217, C218); 0.1 uF and 10 uF REFT to REFB "
                                                    "(C221, C220)", f"{AD} p.18, p.8"],
    ["AVDD, DRVDD", "27, 32; 16", "0.1 uF with 10 uF per group: 100n and 1u stay (3V0: 4 x 100n; 3V3D: C25, C225, "
                                  "C252); new 10u C994 on 3V0, C995 on 3V3D",
     f"{AD} p.8 (Table 6)"],
    ["VCMA (61)", "none (no VCM pin)", "U45 supplies the common mode: 1.5 V divider R990/R991 1 kohm from 3V0 on "
                                       "/ADC_VCMB (kept chain; C30, C31, C41); 22 uA x 500 ohm = 11 mV",
     "adi-lt6232-datasheet p.3, p.5; " + AD + " p.17"],
    ["DNC", "6", "left open", f"{AD} p.8"],
    ["channel B: DB0-DB11, OFB, OE2, SHDN2, SENSEB, VCMB, REFHB/REFLB, AINB, MUX", "none", "removed; FPGA pins "
     "M1, P1, N2 freed", "rx2_dnp.py; pinout.xdc at " + FW_COMMIT[:7]],
]


def pin_map():
    rows = PIN_ROWS_1 + PIN_ROWS_2
    write_csv("pin_map.csv", PIN_COLS, rows)
    w = [0.22, 0.17, 0.41, 0.20]
    table_image("pin_map_1.png", PIN_COLS, PIN_ROWS_1, w, 8.6, fig=(12.1, 5.4))
    table_image("pin_map_2.png", PIN_COLS, PIN_ROWS_2, w, 8.6, fig=(12.1, 5.4))
    return rows


# ------------------------------------------------------------------------------ the simulation
def sim_figures(adc, nums):
    today, rx1 = adc["cases"]["today"], adc["cases"]["rx1"]
    # IF response, today against 1-RX
    f = rx1["ac"]["f_hz"]
    fig, ax = plt.subplots(1, 2, figsize=(12.1, 4.7), gridspec_kw={"width_ratios": [2, 1]})
    ax[0].semilogx(today["ac"]["f_hz"], today["ac"]["gain_db"], color=BLUE, lw=2.5, label="today (LTC2292 load)")
    ax[0].semilogx(f, rx1["ac"]["gain_db"], color=RED, lw=1.2, ls="--", label="1-RX (AD9237 load, step 2 bias)")
    ax[0].axvline(2e5, color=GREY, ls=":")
    ax[0].text(2.1e5, -30, "200 kHz beat\n(100 m, 300 MHz / 1 ms)", fontsize=8, color=GREY)
    ax[0].axvline(1e6, color=GREY, ls=":")
    ax[0].text(1.05e6, -10, "1 MHz\ndecimated\nNyquist", fontsize=8, color=GREY)
    ax[0].set_ylim(-60, 25)
    ax[0].set_xlabel("frequency (Hz)")
    ax[0].set_ylabel("U45 stage gain to the ADC pins (dB)")
    ax[0].set_title(f"IF response: -3 dB {rx1['f3db_low_hz'] / 1e3:.1f} kHz to {rx1['f3db_high_hz'] / 1e6:.2f} MHz, "
                    "identical in band")
    ax[0].grid(True, which="both", alpha=0.3)
    ax[0].legend(loc="lower left", fontsize=8)
    fs = [10e3, 100e3, 200e3, 1e6, 2e6, 20e6]
    dd = [adc["delta_gain_db"][str(int(x))] for x in fs]
    ax[1].bar(range(len(fs)), [d * 1e3 for d in dd], color=RED)
    ax[1].set_xticks(range(len(fs)))
    ax[1].set_xticklabels(["10k", "100k", "200k", "1M", "2M", "20M"])
    ax[1].set_ylabel("1-RX minus today (mdB)")
    ax[1].set_title("difference (7 pF, against 5 pF + 15 ohm)")
    ax[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(BUILD / "if_response.png", dpi=150)
    plt.close(fig)

    # swing and common mode
    lim = nums["input_limits"]
    sw, swt = rx1["swing"], today["swing"]
    fig, ax = plt.subplots(1, 2, figsize=(12.1, 4.7))
    avail = (0.35, 2.90)  # lt6232 p.4: within 350 mV of GND, 400 mV of V+ at 3.3 V
    ax[0].barh([1, 0], [sw["fs_out_max_v"] - sw["fs_out_min_v"], swt["fs_out_max_v"] - swt["fs_out_min_v"]],
               left=[sw["fs_out_min_v"], swt["fs_out_min_v"]], color=[RED, BLUE], height=0.5)
    ax[0].axvspan(*avail, color=GREEN, alpha=0.12)
    ax[0].axvline(avail[0], color=GREEN)
    ax[0].axvline(avail[1], color=GREEN)
    ax[0].set_yticks([0, 1])
    ax[0].set_yticklabels(["today", "1-RX"])
    ax[0].set_xlim(0, 3.3)
    ax[0].set_xlabel("U45 output (V), 3.3 V supply")
    ax[0].set_title(f"full scale (+/-{sw['fs_diff_peak_v']:.3f} V): {sw['fs_out_min_v']:.2f} to {sw['fs_out_max_v']:.2f} V,\n"
                    f"margin {sw['fs_out_min_v'] - avail[0]:.2f} V below, {avail[1] - sw['fs_out_max_v']:.2f} V above "
                    "(green: output swing, lt6232 p.4)", fontsize=9)
    ax[0].text(0.05, 0.5, f"clips only at {sw['clip_diff_peak_v']:.2f} V peak diff:\n"
                          f"{20 * __import__('math').log10(sw['clip_diff_peak_v'] / 1.0):.1f} dB over the 1 V span peak "
                          f"(OTR first)", transform=ax[0].transAxes, fontsize=8, color=GREY)
    cm = [rx1["op"]["pin_cm"], today["op"]["pin_cm"]]
    ax[1].barh([1, 0], cm, color=[RED, BLUE], height=0.5)
    ax[1].axvspan(lim["vcm_min_v"], lim["vcm_max_v"], color=GREEN, alpha=0.12)
    ax[1].axvline(1.5, color=GREEN, ls="--")
    ax[1].set_yticks([0, 1])
    ax[1].set_yticklabels(["today", "1-RX"])
    ax[1].set_xlim(0, 3.0)
    ax[1].set_xlabel("common mode at the ADC pins (V)")
    ax[1].set_title(f"DC common mode: 1-RX {cm[0]:.4f} V, today {cm[1]:.4f} V;\n"
                    f"allowed {lim['vcm_min_v']:.1f} to {lim['vcm_max_v']:.1f} V (green, ad9237 p.17)", fontsize=9)
    for i, v in enumerate(cm[::-1]):
        ax[1].text(v + 0.03, i, f"{v:.4f}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(BUILD / "swing_cm.png", dpi=150)
    plt.close(fig)

    # settling
    s = {(x["hold"], x["ron_ohm"], x["f_hz"]): x for x in rx1["settling"]}
    st = {(x["hold"], x["ron_ohm"], x["f_hz"]): x for x in today["settling"]}
    w = s[("keep", 10.0, 1e6)]["window"]
    fig, ax = plt.subplots(1, 2, figsize=(12.1, 4.7), gridspec_kw={"width_ratios": [3, 2]})
    t = w["t_ns"]
    ax[0].plot(t, [v * 1e3 for v in w["pin_diff_v"]], color=RED, lw=1.5, label="ADC pins (differential)")
    ax[0].plot(t, [v * 1e3 for v in w["ref_diff_v"]], color=BLUE, lw=1, ls="--", label="static load (reference)")
    for e in w["track_edges_ns"]:
        ax[0].axvline(e, color=GREY, ls=":")
    ax[0].set_xlabel("time (ns); dotted: start of each 12.5 ns track phase")
    ax[0].set_ylabel("mV")
    ax[0].set_title("1 MHz, -1 dBFS: the pin voltage under the sampling load against a static load", fontsize=9)
    ax[0].legend(fontsize=8)
    ax[0].grid(True, alpha=0.3)
    keys = [("keep", 10.0, 2e5), ("keep", 10.0, 1e6)]
    lab = ["200 kHz", "1 MHz"]
    x = range(2)
    ax[1].bar([i - 0.2 for i in x], [st[k]["err_lsb_max"] for k in keys], 0.4, color=BLUE, label="today")
    ax[1].bar([i + 0.2 for i in x], [s[k]["err_lsb_max"] for k in keys], 0.4, color=RED, label="1-RX")
    ax[1].axhline(0.5, color=GREEN, ls="--")
    ax[1].text(0.35, 0.53, "0.5 LSB", color=GREEN, fontsize=8)
    ax[1].set_xticks(list(x))
    ax[1].set_xticklabels(lab)
    ax[1].set_ylabel("held-sample error, max (LSB of 488 uV)")
    r10 = s[("reset", 10.0, 1e6)]
    ax[1].set_title(f"error at 12.5 ns (46 ps delay, 0.04 LSB nonlinear);\nworst-case 'reset' bound {r10['err_lsb_max']:.1f} LSB, "
                    f"{r10['nonlin_resid_lsb_max']:.2f} LSB nonlinear", fontsize=8)
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(BUILD / "settling.png", dpi=150)
    plt.close(fig)


def numbers_figure(nums, dr):
    rail, noise = nums["rail_3v0"], nums["adc_noise"]
    fig, ax = plt.subplots(1, 3, figsize=(12.1, 4.7))
    names = ["today\nLTC2292", "1-RX\nAD9237\n(typ)", "1-RX\nbound"]
    vals = [rail["today_total_ma"], rail["rx1_typ_total_ma"], rail["rx1_bound_total_ma"]]
    ax[0].bar(names, vals, color=[BLUE, RED, "#e08a85"])
    ax[0].axhline(rail["u39_rating_ma"], color=GREEN, ls="--")
    ax[0].text(0.02, rail["u39_rating_ma"] - 22, "U39 LP5907: 250 mA", color=GREEN, fontsize=8)
    for i, v in enumerate(vals):
        ax[0].text(i, v + 4, f"{v:.0f} mA ({100 * v / rail['u39_rating_ma']:.0f} %)", ha="center", fontsize=8)
    ax[0].set_ylim(0, 270)
    ax[0].set_title("3V0 rail load", fontsize=10)
    ax[1].bar(["LTC2292\n(LTC2294 sheet)", "AD9237-40"], [noise["ltc2292"]["snr_dbfs"], noise["ad9237"]["snr_dbfs"]],
              color=[BLUE, RED])
    for i, v in enumerate([noise["ltc2292"]["snr_dbfs"], noise["ad9237"]["snr_dbfs"]]):
        ax[1].text(i, v + 0.5, f"{v:.1f} dBFS", ha="center", fontsize=9)
    ax[1].axhline(noise["ideal_12bit_db"], color=GREY, ls=":")
    ax[1].text(0.0, noise["ideal_12bit_db"] + 0.4, "ideal 12 bit 74.0 dB", fontsize=8, color=GREY, ha="center")
    ax[1].set_ylim(55, 78)
    ax[1].set_title(f"ADC SNR at 40 MSPS: {noise['delta_db']:.1f} dB lower", fontsize=10)
    xs = ["20 MHz band\n(40 MSPS)", "1 MHz band\n(after /20)"]
    ax[2].bar([i - 0.2 for i in range(2)], [dr["ltc2292"]["dr_nyq_db"], dr["ltc2292"]["dr_band_db"]], 0.4,
              color=BLUE, label="today")
    ax[2].bar([i + 0.2 for i in range(2)], [dr["ad9237"]["dr_nyq_db"], dr["ad9237"]["dr_band_db"]], 0.4,
              color=RED, label="1-RX")
    for i, k in enumerate(("nyq", "band")):
        ax[2].text(i - 0.2, dr["ltc2292"][f"dr_{k}_db"] + 0.5, f"{dr['ltc2292'][f'dr_{k}_db']:.1f}", ha="center", fontsize=8)
        ax[2].text(i + 0.2, dr["ad9237"][f"dr_{k}_db"] + 0.5, f"{dr['ad9237'][f'dr_{k}_db']:.1f}", ha="center", fontsize=8)
    ax[2].set_xticks(range(2))
    ax[2].set_xticklabels(xs)
    ax[2].set_ylim(55, 88)
    ax[2].set_title(f"IF dynamic range (dB): loss {dr['loss_nyq_db']:.1f} / {dr['loss_band_db']:.1f} dB", fontsize=10)
    ax[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(BUILD / "rail_snr.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------------------ RX2 not fitted
def rx2_table(rx, ch):
    groups = ch.DNP_GROUPS
    rows = []
    for g, refs in groups.items():
        vals = []
        for r in refs:
            v = rx["values"].get(r, ["", ""])
            vals.append(f"{r} {v[0]}".strip())
        rows.append([g, str(len(refs)), ", ".join(vals)])
    n = sum(len(r) for r in groups.values())
    shared = ", ".join(rx["shared"]) + "; LO split " + ", ".join(rx["lo_split_parts"])
    rows.append(["Shared: kept, not removed", "-", shared + " (dual mixer, quad op-amp, LO split, U8 replaced)"])
    fp = rx["fpga_pins_freed"]
    rows.append(["FPGA pins freed (U30)", "3", ", ".join(f"{p[0]} ({n_})" for n_, p in
                                                         ((k, v) for k, v in fp.items()))])
    cols = ["Group (from antenna port to ADC channel B)", "Refs", "Parts (DNP in 1-RX)"]
    write_csv("rx2_dnp.csv", cols, rows)
    table_image("rx2_dnp.png", cols, rows, [0.27, 0.06, 0.67], 9.5, fig=(12.1, 5.4))
    return n


# ------------------------------------------------------------------------------ stock-only lines
def stock_table(st, ch):
    rows, csv_rows = [], []
    rank = {"drop-in": 0, "footprint change": 1, "design change": 2}
    n_ok = sum(1 for x in st["lines"] if x["status"] == "ok")
    for key, meta in ch.LINES.items():
        ent = st["options"][key]
        opts = {o["id"]: o for o in ent["options"]}
        rec = opts.get(meta["rec"])
        refs = ", ".join(meta["refs"])
        if rec is None:
            rows.append([refs, ent["line_status"], "no recommendation (see rx1-sma)", "-", "-", "-"])
            csv_rows.append(rows[-1])
            continue
        row = [refs, ent["line_status"], f"{rec['id']}. {rec['label']}  {rec['lcsc']}",
               f"{rec['stock']} / {rec['need']}", rec["cls"], meta["choice"]]
        rows.append(row)
        csv_rows.append(row)
    cols = ["Refs", "Line", "Recommended JLC-stocked option", "Stock / need", "Class", "Choice key"]
    write_csv("stock_lines.csv", cols, csv_rows)
    table_image("stock_lines.png", cols, rows, [0.13, 0.07, 0.38, 0.10, 0.15, 0.17], 8.8, fig=(12.1, 5.0))
    lay = st["layout"]
    return n_ok, lay


# ------------------------------------------------------------------------------ data path
def data_figure(dp):
    r = dp["rates"]
    rates = r["rates_mbyte_s"]
    lim = r["limits_mbyte_s"]
    names = ["raw, 12 bit packed\n(40 MSPS)", "raw, 16 bit words\n(40 MSPS)", "decimated /20,\n16 bit, 1 channel",
             "decimated /20,\nfirmware 32 bit word"]
    vals = [rates["raw_12bit_packed"], rates["raw_16bit_padded"], rates["decimated_16bit_one_channel"],
            rates["decimated_firmware_word_32bit"]]
    fig, ax = plt.subplots(figsize=(12.1, 4.8))
    ax.bar(names, vals, color=[RED, RED, GREEN, GREEN])
    for lbl, key, col in (("FT2232H stated: 25 MB/s (p.26)", "datasheet_stated", GREY),
                          ("FT2232H maximum: 40 MB/s (p.1)", "datasheet_max", BLUE),
                          ("60 MHz x 8 bit bus ceiling: 60 MB/s (p.32)", "bus_ceiling", NAVY)):
        ax.axhline(lim[key], color=col, ls="--")
        ax.text(3.45, lim[key] + 1, lbl, color=col, fontsize=8, ha="right")
    for i, v in enumerate(vals):
        ax.text(i, v + 1.2, f"{v:g} MB/s", ha="center", fontsize=10)
    ax.set_ylabel("MB/s")
    ax.set_ylim(0, 95)
    ax.set_title("Data rate off the board (ftdi-ft2232h-datasheet): decimated streams fit, raw does not", fontsize=11)
    fig.tight_layout()
    fig.savefig(BUILD / "data_path.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------------------ choices
def choices_table(ch):
    chs = ch.choices()
    rows = []
    for k, v in chs.items():
        rows.append([k, v["refs"].replace(",", ", "), v["recommendation"]])
    cols = ["Key (parts/choices.json)", "Refs", "Recommendation (yours to decide)"]
    write_csv("choices.csv", cols, rows)
    table_image("choices.png", cols, rows, [0.16, 0.16, 0.68], 8.6, fig=(12.1, 5.4))
    return len(rows)


def change_summary(rows):
    from collections import Counter
    kinds = Counter(r["kind"] for r in rows)
    status = Counter(r["status"] for r in rows)
    return kinds, status


def main() -> None:
    ts = tg.load(os.environ.get("FMCW_TARGETS", "default"))
    print(f"figures.py: {tg.describe(ts)}")
    BUILD.mkdir(exist_ok=True)
    boards = int(tg.value(ts, "board_quantity"))
    an = load_module("adc_numbers")
    ch = load_module("rx1_changes")
    adc, rx, st, dp = jload("adc_input.json"), jload("rx2_dnp.json"), jload("stock_lines.json"), jload("data_path.json")
    nums = adc["numbers"]
    nz = adc["cases"]["rx1"]["noise"]
    dr = an.dynamic_range(nz["rms_to_20MHz_uv"], nz["rms_in_1MHz_uv"])

    pin_rows = pin_map()
    sim_figures(adc, nums)
    numbers_figure(nums, dr)
    n_dnp = rx2_table(rx, ch)
    n_ok, lay = stock_table(st, ch)
    data_figure(dp)
    n_choices = choices_table(ch)
    rows = ch.changes()
    kinds, status = change_summary(rows)
    sumcols = ["Change group", "Rows in parts/rx1_changes.csv", "Status", "Covering check"]
    by_row = {}
    for r in rows:
        by_row.setdefault(r["board_row"], []).append(r)
    n_opt = sum(1 for r in rows if r["status"] == "option" and r["board_row"] not in
                (ch.R_STRAP, ch.R_VCM))
    summary = [
        ["U8 to AD9237BCPZ-40 (LFCSP-32), MODE strap kept", str(len(by_row[ch.R_U8])), "decided (directive)",
         "adc_input_sim.py, adc_numbers.py"],
        ["Straps, bias divider, reference caps", str(len(by_row[ch.R_STRAP]) + len(by_row[ch.R_REF])), "proposed",
         "pin map; adc_input_sim.py for the bias"],
        ["Receive chain 2 not fitted, freed FPGA nets", str(len(by_row[ch.R_DNP])), "decided (directive)",
         "rx2_dnp.py, tests/test_rx1_rx2_dnp.py"],
        ["Unused U45 amps C and D: /ADC_VCMA merge", str(len(by_row[ch.R_VCM])), "option (rx1-unused-amps)",
         "rx2_dnp.py vcm section"],
        ["JLC-stock substitutions", str(n_opt), "option, per rx1- key",
         "stock_lines.py; the simulation only for U45 (LT6231)"],
    ]
    write_csv("change_summary.csv", sumcols, summary)
    table_image("change_summary.png", sumcols, summary, [0.34, 0.16, 0.20, 0.30], 11, fig=(12.1, 3.6))

    sw = adc["cases"]["rx1"]["swing"]
    rail = nums["rail_3v0"]
    nm = nums["adc_noise"]
    s1 = {(x["hold"], x["ron_ohm"], x["f_hz"]): x for x in adc["cases"]["rx1"]["settling"]}
    s0 = {(x["hold"], x["ron_ohm"], x["f_hz"]): x for x in adc["cases"]["today"]["settling"]}
    v = dp["rates"]["verdict"]
    facts = {
        "boards": boards, "jlc_db": st["jlc_database_date"], "fw_commit": FW_COMMIT,
        "n_changes": len(rows), "n_choices": n_choices, "n_dnp": n_dnp,
        "n_status_decided": status["decided"], "n_status_proposed": status["proposed"],
        "n_status_option": status["option"],
        "n_lines": len(st["lines"]), "n_ok": n_ok,
        "n_thin": sum(1 for x in st["lines"] if x["status"] == "thin"),
        "n_fail": sum(1 for x in st["lines"] if x["status"] == "fail"),
        "n_fp_lines": len(lay["footprint_lines"]), "n_design_lines": len(lay["design_lines"]),
        "fp_lines": ", ".join(lay["footprint_lines"]), "design_lines": ", ".join(lay["design_lines"]),
        "n_layout_refs": lay["layout_refs"],
        "fs_min_v": f"{sw['fs_out_min_v']:.2f}", "fs_max_v": f"{sw['fs_out_max_v']:.2f}",
        "clip_peak_v": f"{sw['clip_diff_peak_v']:.2f}",
        "cm_rx1": f"{adc['cases']['rx1']['op']['pin_cm']:.4f}", "cm_today": f"{adc['cases']['today']['op']['pin_cm']:.4f}",
        "settle_rx1_1m": f"{s1[('keep', 10.0, 1e6)]['err_lsb_max']:.2f}",
        "settle_today_1m": f"{s0[('keep', 10.0, 1e6)]['err_lsb_max']:.2f}",
        "settle_rx1_200k": f"{s1[('keep', 10.0, 2e5)]['err_lsb_max']:.2f}",
        "settle_reset": f"{s1[('reset', 10.0, 1e6)]['err_lsb_max']:.1f}",
        "rail_today": f"{rail['today_total_ma']:.1f}", "rail_rx1": f"{rail['rx1_typ_total_ma']:.1f}",
        "rail_bound": f"{rail['rx1_bound_total_ma']:.1f}", "rail_rx1_pct": f"{rail['rx1_typ_pct']:.0f}",
        "rail_today_pct": f"{rail['today_pct']:.0f}", "rail_bound_pct": f"{rail['rx1_bound_pct']:.0f}",
        "snr_ad": f"{nm['ad9237']['snr_dbfs']:.1f}", "snr_ltc": f"{nm['ltc2292']['snr_dbfs']:.1f}",
        "snr_delta": f"{nm['delta_db']:.1f}",
        "dr_ad_nyq": f"{dr['ad9237']['dr_nyq_db']:.1f}", "dr_ltc_nyq": f"{dr['ltc2292']['dr_nyq_db']:.1f}",
        "dr_ad_band": f"{dr['ad9237']['dr_band_db']:.1f}", "dr_ltc_band": f"{dr['ltc2292']['dr_band_db']:.1f}",
        "dr_loss_nyq": f"{dr['loss_nyq_db']:.1f}", "dr_loss_band": f"{dr['loss_band_db']:.1f}",
        "raw_pct25": f"{v['raw_12bit_packed']['pct_of_stated_25']:.0f}",
        "raw_pct40": f"{v['raw_12bit_packed']['pct_of_max_40']:.0f}",
        "dec_pct25": f"{v['decimated_16bit_one_channel']['pct_of_stated_25']:.0f}",
        "decw_pct25": f"{v['decimated_firmware_word_32bit']['pct_of_stated_25']:.0f}",
        "fifos_pct": f"{dp['buffers']['firmware_fifos_pct']:.1f}",
        "raw_chirp_pct": f"{dp['buffers']['chirp_raw_16bit_pct_of_bram']:.1f}",
    }
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print(f"figures.py: {len(rows)} changes, {n_choices} choices, {len(pin_rows)} pin-map rows, "
          f"{n_ok} of {len(st['lines'])} stock lines ok")


if __name__ == "__main__":
    main()
