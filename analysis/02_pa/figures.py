"""Figures and tables for the U14 power amplifier report (par-07).

Run by tools/build_report.py with this folder as the working directory. Writes into build/.
Input: candidates.yaml (requirements and candidate figures, each with its datasheet id and page,
the schematic net, or the database it came from). The requirements slide, the comparison table
and one slide per candidate are drawn from it; nothing is typed into the deck by hand.
"""
import csv
import json
import os
import sys
import textwrap
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import targets as tg  # noqa: E402

BUILD = HERE / "build"
NAVY, RED = "#1f2a44", "#c0392b"
W_IN, H_IN = 12.1, 5.4
REC = "Recommendation (labelled as such, the choice is yours): "


def write_csv(name, header, rows):
    with open(BUILD / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def table_image(name, cols, rows, widths, fs, paras=()):
    """Draw a table (header, rows) and optional paragraphs [(text, colour, bold)] as one picture."""
    fig = plt.figure(figsize=(W_IN, H_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    line_h = fs * 1.25 / 72 / H_IN
    y = 0.99

    def draw_row(cells, bold=False, fill=None):
        nonlocal y
        wrapped = [textwrap.wrap(t, max(int(w * W_IN * 72 / (fs * 0.55)) - 2, 6)) or [""]
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

    draw_row(cols, bold=True, fill="#dfe4ee")
    for i, r in enumerate(rows):
        draw_row(r, fill="#f4f6fa" if i % 2 == 0 else None)
    y -= 0.02
    for text, col, bold in paras:
        for ln in textwrap.wrap(text, int(W_IN * 72 / (fs * (0.66 if bold else 0.55))) - 4):
            ax.text(0.005, y, ln, va="top", fontsize=fs, color=col, fontweight="bold" if bold else "normal")
            y -= line_h
        y -= 0.012
    if y < 0:
        raise SystemExit(f"figures.py: {name} overflows its picture ({y:.2f})")
    fig.savefig(BUILD / name, dpi=150)
    plt.close(fig)


def qpa_s21_figure() -> None:
    """QPA9501 |S21| across the band from the measured s2p, with the datasheet's own points (p2)."""
    # The vendor file is not redistributed (manifest id qorvo-qpa9501-sparams, commit: 'no'); it is read
    # from its pinned local copy, so this figure needs the file fetched first. Option line: Hz S dB R 50;
    # columns: f, S11 dB/deg, S21 dB/deg, S12 dB/deg, S22 dB/deg.
    s2p = HERE.parent.parent / "datasheets" / "files" / "qorvo" / "qpa9501.s2p"
    if not s2p.exists():
        raise SystemExit(f"figures.py: {s2p} is missing; fetch it (manifest id qorvo-qpa9501-sparams)")
    rows = [l.split() for l in s2p.read_text().splitlines() if l.strip() and l[0] not in "!#"]
    rows = [r for r in rows if 4.8e9 <= float(r[0]) <= 6.1e9]
    f = [float(r[0]) / 1e9 for r in rows]
    s11, s21, s22 = ([float(r[i]) for r in rows] for i in (1, 3, 7))
    fig, (a, b) = plt.subplots(2, 1, figsize=(W_IN, H_IN), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    for ax in (a, b):
        ax.axvspan(5.6, 5.9, color="#dfe4ee", label="board band 5.60-5.90 GHz")
        ax.grid(alpha=0.3)
    a.plot(f, s21, color=NAVY, lw=2, label="|S21| measured (s2p, 2015, bias not stated)")
    for fx, lo, ty, hi in ((4.9, None, 33.6, None), (5.2, 30, 34, 36), (5.8, 29.5, 32, 36)):
        a.plot([fx], [ty], "o", color=RED, label="datasheet p2 typ (bar: min-max)" if fx == 4.9 else None)
        if lo:
            a.plot([fx, fx], [lo, hi], color=RED, lw=1)
            a.plot([fx], [lo], "_", color=RED, ms=10)
            a.plot([fx], [hi], "_", color=RED, ms=10)
    a.axhline(32.7, color="gray", ls="--", lw=1)
    a.text(5.62, 35.2, "gain needed about 32.7 dB (25.5 dBm out, -7.2 dBm in)", fontsize=9, color="gray")
    a.set_ylabel("gain (dB)")
    a.set_ylim(26, 38)
    a.set_title("QPA9501 gain across the band: datasheet min/typ/max at 4.9, 5.2, 5.8 GHz (qorvo-qpa9501-datasheet p2) "
                "and measured |S21| (qorvo-qpa9501-sparams)", fontsize=10, color=NAVY)
    a.legend(fontsize=9, loc="lower left")
    b.plot(f, s11, color=NAVY, label="|S11| input")
    b.plot(f, s22, color=RED, label="|S22| output")
    b.set_ylabel("return loss (dB)")
    b.set_xlabel("frequency (GHz)")
    b.legend(fontsize=9, loc="lower left")
    b.set_xlim(4.8, 6.1)
    fig.tight_layout()
    fig.savefig(BUILD / "qpa9501_s21.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ts = tg.load(os.environ.get("FMCW_TARGETS", "default"))
    print(f"figures.py: {tg.describe(ts)}")
    BUILD.mkdir(exist_ok=True)
    data = yaml.safe_load((HERE / "candidates.yaml").read_text())
    reqs = data["requirements"]
    cands = sorted(data["candidates"], key=lambda c: c["rank"])  # JLC-stocked options first
    boards = int(tg.value(ts, "board_quantity"))
    fmin, fmax = tg.value(ts, "freq_min_ghz"), tg.value(ts, "freq_max_ghz")
    pout = tg.value(ts, "tx_power_dbm")

    # The two target values in the requirements must be the target set's own.
    if f"{fmin:.2f} to {fmax:.2f} GHz" not in reqs[0][1] or f"{pout:g} dBm" not in reqs[1][1]:
        raise SystemExit("figures.py: candidates.yaml requirements disagree with the target set")
    for c in cands:
        if c["status"] == "scored" and not all(r[2] for r in c["rows"]):
            raise SystemExit(f"figures.py: {c['id']} has a figure with no source")
        if c["status"] == "obtain" and "NOT on file" not in c["rows"][0][1]:
            raise SystemExit(f"figures.py: {c['id']} lacks its 'not on file' row")

    # Requirements: slide picture and table.
    write_csv("requirements.csv", ["Requirement", "Value", "Source"], reqs)
    table_image("requirements.png", ["Requirement", "Value", "Source"], reqs, [0.14, 0.50, 0.36], 10.5)

    # One comparison table.
    ch = ["Option", "Covers 5.60-5.90 GHz", "Gain / P1dB / Psat typ", "Current, existing supply",
          "Existing U14 footprint", f"Stock ({boards} needed)", f"USD for {boards}", "Datasheet, pages"]
    crow = [[f"{c['rank']}. {c['short']}", *c["cmp"]] for c in cands]
    write_csv("comparison.csv", ch, crow)
    table_image("comparison.png", ch, crow, [0.10, 0.11, 0.12, 0.15, 0.17, 0.10, 0.08, 0.17], 9.5,
                [("Rank: JLC-stocked options first (1-3), then DigiKey-only (4-5); within a group by lifecycle and fit. "
                  "n.g. = not given in the datasheet. Figures are typical; the SE parts are specified at 5.4 GHz, not 5.8 GHz. "
                  "Needed: about 25.5 dBm out of U14 at about -7.2 dBm in, so about 32.7 dB gain.", NAVY, False)])
    qpa_s21_figure()

    # One slide per candidate.
    for c in cands:
        paras = [(c["verdict"], RED if c["status"] == "obtain" else NAVY, True)]
        table_image(f"cand_{c['id']}.png", ["Item", "Value", "Datasheet id, page or source"], c["rows"],
                    [0.15, 0.56, 0.29], 10.5 if len(c["rows"]) > 8 else 11.5, paras)
        write_csv(f"cand_{c['id']}.csv", ["Item", "Value", "Datasheet id, page or source"], c["rows"])

    scored = [c for c in cands if c["status"] == "scored"]
    obtain = [c for c in cands if c["status"] == "obtain"]
    facts = {
        "boards": boards, "fmin": f"{fmin:.2f}", "fmax": f"{fmax:.2f}", "pout": f"{pout:g}",
        "n_cands": len(cands) - 1,  # the stock option is not a replacement
        "n_scored": len(scored), "n_obtain": len(obtain),
        "obtain_names": ", ".join(c["short"] for c in obtain),
        "not_shortlisted": data["not_shortlisted"],
    }
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print(f"figures.py: {len(cands)} options, {len(scored)} scored, {len(obtain)} for the user to obtain")


if __name__ == "__main__":
    main()
