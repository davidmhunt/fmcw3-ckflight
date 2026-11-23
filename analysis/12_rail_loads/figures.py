"""Figures, tables and facts for the buck-rail load report (par-11 step 6).

Run by tools/build_report.py with this folder as the working directory. Writes into build/.
Nothing is typed into the report by hand: every number is read from sim/*.json, which the scripts
consumers.py, currents.py, vccint.py and loads.py write (run them first with --check; this script
re-runs currents.build() and loads.build() itself so the figures cannot drift from them):

    summary.csv        one row per board and rail (deck table slide)
    peak_vs_limit.png  worst-case DC and peak per rail and board against the limits
    consumers_*.png    consumer tables as pictures (1V0, 3V8 by branch, 5V6)
    facts.json         numbers and the full per-rail consumer tables (markdown) for writeup.md
"""
import json
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import currents  # noqa: E402
import loads  # noqa: E402

BUILD = HERE / "build"
NAVY, RED, GREEN = "#1f2a44", "#c0392b", "#2e7d4f"
W_IN, H_IN = 12.1, 5.4
RAILS = ("1V0", "3V8", "5V6")
BOARDS = (("2rx", "2-RX"), ("1rx", "1-RX"))
LDOS = ("U20", "U23", "U24", "U25", "U39", "U22")


def num(x):
    return "" if x is None else f"{round(x, 3):g}"


def src_text(r):
    if r["how"] in ("datasheet", "power/V"):
        seen, out = set(), []
        for sid, page, _ in r["src"]:
            if (sid, page) not in seen:
                seen.add((sid, page))
                out.append(f"{sid} p{page}")
        s = "; ".join(out)
        if r["how"] == "power/V":
            s = "power / V: " + s
        return s + (f". {r['note']}" if r["note"] else "")
    s = f"{r['how']}: {r['why']}"
    if r["src"]:
        s += " (" + "; ".join(sorted({f"{a} p{b}" for a, b, _ in r["src"]})) + ")"
    return s + (f". {r['note']}" if r["note"] else "")


def merged_rows(tables, rail, v3):
    """Rows of one rail over both boards: (board label, row) with identical rows merged to 'both'."""
    seen, out = {}, []
    for board, label in BOARDS:
        for r in tables[board]:
            if r["rail"] != rail:
                continue
            k = (r["ref"], tuple(r["path"]), r["part"], r["typ"], r["max"])
            if k in seen:
                seen[k][0] = "both"
                continue
            seen[k] = [label, r]
            out.append(seen[k])
    return out


def branch(r):
    if len(r["path"]) > 1:
        return r["path"][1]
    return r["ref"] if r["ref"] in LDOS else "direct"


def md_table(header, rows, widths):
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("-" * w for w in widths) + "|"]
    lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def image_table(name, cols, rows, widths, fs, notes=()):
    """Draw a table as a picture; rows are lists of strings; a row starting with '**' is bold."""
    fig = plt.figure(figsize=(W_IN, H_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    line_h = fs * 1.25 / 72 / H_IN
    y = 0.99

    def draw(cells, bold=False, fill=None):
        nonlocal y
        wrapped = [textwrap.wrap(t, max(int(w * W_IN * 72 / (fs * 0.55)) - 2, 5)) or [""]
                   for t, w in zip(cells, widths)]
        h = max(len(w) for w in wrapped) * line_h + 0.012
        if fill:
            ax.add_patch(Rectangle((0, y - h), 1, h, color=fill, lw=0))
        x = 0.005
        for lines, w in zip(wrapped, widths):
            for i, ln in enumerate(lines):
                ax.text(x, y - 0.007 - i * line_h, ln, va="top", fontsize=fs,
                        fontweight="bold" if bold else "normal", color=NAVY)
            x += w
        y -= h

    draw(cols, True, "#dfe4ee")
    for i, r in enumerate(rows):
        b = r[0].startswith("**")
        draw([c.lstrip("*") if j == 0 else c for j, c in enumerate(r)], b, "#f4f6fa" if i % 2 == 0 else None)
    y -= 0.02
    for t in notes:
        for ln in textwrap.wrap(t, int(W_IN * 72 / (fs * 0.55)) - 4):
            ax.text(0.005, y, ln, va="top", fontsize=fs - 1, color=NAVY)
            y -= line_h
    if y < 0:
        raise SystemExit(f"figures.py: {name} overflows its picture ({y:.2f})")
    fig.savefig(BUILD / name, dpi=150)
    plt.close(fig)


def main():
    BUILD.mkdir(exist_ok=True)
    cons = json.load(open(currents.CONSUMERS))
    v3 = json.load(open(loads.VCCINT))["estimate"]
    L = loads.build()
    tables = {}
    for board, _ in BOARDS:
        rows, problems = currents.table(board, cons)
        assert not problems, problems
        tables[board] = rows
    lim = L["limits"]
    ind = L["inductor"]
    facts = {}

    # ---- summary table and chart --------------------------------------------------------------
    srows = []
    for board, label in BOARDS:
        for rail in RAILS:
            r = L["boards"][board][rail]
            rp = r["ripple_pp_a"]
            ok = r["peak_ok"] and r["dc_ok"]
            srows.append([label, rail, f"{r['vout_v']:.3f}", f"{r['dc_typ_a']:.3f}", f"{r['dc_max_a']:.3f}",
                          f"{rp['500 kHz']:.3f}", f"{r['peak_worst_a']:.3f}",
                          f"{100 * r['peak_worst_a'] / ind['isat_a']:.0f} %",
                          f"{r['copper_loss_typ_w'] * 1e3:.0f}", "pass" if ok else "FAIL"])
    hdr = ["Board", "Rail", "Vout V", "DC typ A", "DC max A", "Ripple A", "Peak A", "Peak / Isat",
           "Cu loss mW", "Result"]
    import csv
    with open(BUILD / "summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(srows)
    facts["summary_table"] = md_table(hdr, srows, [6, 5, 7, 8, 8, 8, 7, 8, 8, 6])

    fig, ax = plt.subplots(figsize=(W_IN, H_IN))
    labels = [f"{lab} {rail}" for _, lab in BOARDS for rail in RAILS]
    xs = range(len(labels))
    dc = [L["boards"][b][r]["dc_max_a"] for b, _ in BOARDS for r in RAILS]
    pk = [L["boards"][b][r]["peak_worst_a"] for b, _ in BOARDS for r in RAILS]
    ax.bar([x - 0.2 for x in xs], dc, 0.4, color=NAVY, label="worst-case DC load")
    ax.bar([x + 0.2 for x in xs], pk, 0.4, color="#6c8ebf", label="worst-case peak (DC + ripple/2, 500 kHz, L -20 %)")
    for y, c, t in ((lim["peak_a"], RED, f"peak pass mark {lim['peak_a']:.2f} A (60 % of Isat)"),
                    (lim["dc_a"], GREEN, f"DC pass mark {lim['dc_a']:.2f} A (2/3 of Irms)"),
                    (ind["isat_a"], "gray", f"Isat {ind['isat_a']} A (40 % inductance drop)"),
                    (ind["irms_a"], "gray", f"Irms {ind['irms_a']} A (40 C rise)")):
        ax.axhline(y, color=c, ls="--", lw=1.2)
        ax.text(len(labels) - 0.45, y + 0.04, t, ha="right", fontsize=9, color=c)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels)
    ax.set_ylabel("current (A)")
    ax.set_ylim(0, 4.0)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title(f"APS0650M330A: worst case against the limits (aps0650_ok = {L['aps0650_ok']})",
                 fontsize=11, color=NAVY)
    fig.tight_layout()
    fig.savefig(BUILD / "peak_vs_limit.png", dpi=150)
    plt.close(fig)

    # ---- full consumer tables (markdown, both boards in one table per rail) -----------------------
    for rail in RAILS:
        rows = []
        for label, r in merged_rows(tables, rail, v3):
            if r["how"] == "step3":
                src = ("step 3 estimate (vccint.py), below. Static floor: " +
                       "; ".join(f"{a} p{b}" for a, b, _ in r["src"]))
                rows.append([r["ref"], r["part"], label, num(v3["typ_mA"]), num(v3["max_mA"]), "step3", src])
            else:
                rows.append([r["ref"] + ("" if len(r["path"]) == 1 else f" ({r['path'][-1]})"),
                             r["part"], label, num(r["typ"]), num(r["max"]), r["how"], src_text(r)])
        for board, label in BOARDS:
            typ = L["boards"][board][rail]["dc_typ_a"] * 1000
            mx = L["boards"][board][rail]["dc_max_a"] * 1000
            rows.append(["**Sum", f"{label} {rail} DC load (mA)", label, num(typ), num(mx), "sum", ""])
        facts[f"table_{rail}"] = md_table(
            ["Ref (via)", "Part", "Board", "Typ mA", "Max mA", "How", "Source (manifest id, PDF page) or basis"],
            [[c.lstrip("*") if j == 0 else c for j, c in enumerate(r)] for r in rows],
            [8, 18, 5, 6, 6, 8, 49])

    # ---- consumer pictures ---------------------------------------------------------------------------
    def pic_rows(rail):
        out = []
        for label, r in merged_rows(tables, rail, v3):
            if r["how"] == "step3":
                t, m, src = num(v3["typ_mA"]), num(v3["max_mA"]), "step 3: Vivado power report, bounded worst case"
            else:
                t, m = num(r["typ"]), num(r["max"])
                src = (", ".join(sorted({f"{a} p{b}" for a, b, _ in r["src"]})) if r["src"] else f"{r['how']}")
            out.append([r["ref"], r["part"], label, t, m, src])
        return out

    cols = ["Ref", "Part", "Board", "Typ mA", "Max mA", "Source (manifest id, PDF page)"]
    wd = [0.06, 0.34, 0.06, 0.07, 0.07, 0.40]
    p = pic_rows("1V0")
    image_table("consumers_1V0.png", cols, p + [
        ["**Sum", "1V0 DC load (both boards)", "both", num(L["boards"]["2rx"]["1V0"]["dc_typ_a"] * 1000),
         num(L["boards"]["2rx"]["1V0"]["dc_max_a"] * 1000), ""]], wd, 11,
        notes=[f"FPGA core: typical from the committed Vivado routed power report (junction 26.3 C), worst case "
               f"{v3['max_mA']} mA = DS181 static 159 mA + 4 x the report's dynamic 79 mA. "
               f"Power-on requirement {v3['power_on_min_mA']} mA is stated apart, not a running load."])
    p = pic_rows("5V6")
    image_table("consumers_5V6.png", cols, p + [
        ["**Sum", "5V6 DC load (both boards)", "both", num(L["boards"]["2rx"]["5V6"]["dc_typ_a"] * 1000),
         num(L["boards"]["2rx"]["5V6"]["dc_max_a"] * 1000), ""]], wd, 10)

    # 3V8 by branch: sum of the rows of each LDO branch, per board
    names = {"direct": "direct: R24 LED, R34 divider, R104 pull-up",
             "U20": "U20 3V0 RF bias: 2 x TRF37A73, HMC431LP4 VCO, SKY65404 LNAs",
             "U23": "U23 1V8: FPGA VCCAUX, divider",
             "U24": "U24 3V3A: ADF4158, LT6232, divider",
             "U25": "U25 3V3D: FPGA VCCO, FT2232H, flash, EEPROM, clock, ADC output drivers, header allowance",
             "U39": "U39 3V0 ADC analog: ADC AVDD, MODE and VCM dividers"}
    brows = []
    for br in ("direct", "U20", "U23", "U24", "U25", "U39"):
        cells = []
        for board, _ in BOARDS:
            rr = [r for r in tables[board] if r["rail"] == "3V8" and branch(r) == br]
            cells += [num(sum(r["typ"] or 0 for r in rr)), num(sum(r["max"] or 0 for r in rr))]
        brows.append([br, names[br]] + cells)
    tot = [L["boards"][b]["3V8"] for b, _ in BOARDS]
    brows.append(["**Sum", "3V8 DC load (the branches include each LDO's ground current)",
                  num(tot[0]["dc_typ_a"] * 1000), num(tot[0]["dc_max_a"] * 1000),
                  num(tot[1]["dc_typ_a"] * 1000), num(tot[1]["dc_max_a"] * 1000)])
    image_table("consumers_3V8.png", ["Branch", "Consumers", "2-RX typ mA", "2-RX max mA", "1-RX typ mA", "1-RX max mA"],
                brows, [0.07, 0.51, 0.105, 0.105, 0.105, 0.105], 11,
                notes=["Row by row, with the manifest id and page of every current, in the written report. "
                       "1-RX: receive chain 2 (U13, U16) not fitted; AD9237 in place of the LTC2292; R990/R991 added. "
                       "Header J2 allowance 100 mA is a stated bound, not a datasheet number."])

    # ---- facts -----------------------------------------------------------------------------------------
    f = L["fault"]
    facts.update(
        isat=ind["isat_a"], irms=ind["irms_a"], dcr=ind["dcr_ohm"] * 1000,
        peak_limit=f"{lim['peak_a']:.3f}", dc_limit=f"{lim['dc_a']:.3f}",
        peak_max=f"{L['peak_max_a']:.3f}", dc_max=f"{L['dc_max_a']:.3f}",
        ok=L["aps0650_ok"], l_low=f"{L['l_low_uh']:.1f}",
        vccint_typ=v3["typ_mA"], vccint_max=v3["max_mA"], vccint_on=v3["power_on_min_mA"],
        ilim_min=f["ihs_pk_oc_a"]["min"], ilim_typ=f["ihs_pk_oc_a"]["typ"], ilim_max=f["ihs_pk_oc_a"]["max"],
        ilim_min_pct=f"{100 * f['peak_limit_over_isat']['min']:.0f}",
        ilim_typ_pct=f"{100 * f['peak_limit_over_isat']['typ']:.0f}",
        ilim_max_pct=f"{100 * f['peak_limit_over_isat']['max']:.0f}",
        iout8_min=f["iout_max_eq8_a"]["min"], iout8_typ=f["iout_max_eq8_a"]["typ"], iout8_max=f["iout_max_eq8_a"]["max"],
        hiccup_trigger=f["hiccup"]["trigger"], hiccup_action=f["hiccup"]["action"],
        hiccup_blank=f["hiccup"]["blanking"])
    # worst over the two boards, per rail
    for rail in RAILS:
        rr = [L["boards"][b][rail] for b, _ in BOARDS]
        k = rail.lower()
        facts[f"dc_{k}"] = f"{max(r['dc_max_a'] for r in rr):.3f}"
        facts[f"dc_{k}_margin"] = f"{min(r['dc_margin_a'] for r in rr):.3f}"
        facts[f"pk_{k}"] = f"{max(r['peak_worst_a'] for r in rr):.3f}"
        facts[f"pk_{k}_margin"] = f"{min(r['peak_margin_a'] for r in rr):.3f}"
    # the ripple and peak table with both frequencies (writeup)
    rrows = []
    for board, label in BOARDS:
        for rail in RAILS:
            r = L["boards"][board][rail]
            rp, rn, pt, pm = r["ripple_pp_a"], r["ripple_nominal_L_pp_a"], r["peak_typ_a"], r["peak_max_a"]
            rrows.append([label, rail, f"{r['vout_v']:.3f}", f"{rn['500 kHz']:.3f}", f"{rp['500 kHz']:.3f}",
                          f"{rp['1.1 MHz']:.3f}", f"{r['dc_typ_a']:.3f}", f"{r['dc_max_a']:.3f}",
                          f"{pt['500 kHz']:.3f}", f"{pm['500 kHz']:.3f}", f"{pm['1.1 MHz']:.3f}",
                          f"{r['copper_loss_typ_w'] * 1e3:.0f}", f"{r['copper_loss_max_w'] * 1e3:.0f}"])
    facts["ripple_table"] = md_table(
        ["Board", "Rail", "Vout V", "dI 33 uH 500k A", "dI 26.4 uH 500k A", "dI 26.4 uH 1.1M A", "DC typ A",
         "DC max A", "Peak typ 500k A", "Peak max 500k A", "Peak max 1.1M A", "Cu typ mW", "Cu max mW"],
        rrows, [6, 5, 7, 8, 8, 8, 7, 7, 8, 8, 8, 7, 7])
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print(f"figures.py: wrote {len(facts)} facts, aps0650_ok = {L['aps0650_ok']}")


if __name__ == "__main__":
    main()
