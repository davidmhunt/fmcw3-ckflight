"""Figures and tables for the parts report: availability, routes, user choices, cost.

Run by tools/build_report.py with this folder as the working directory. Writes into build/.
Inputs: parts/out/availability.csv and bom.csv (parts/bom.py live run), parts/decisions.csv.
The option tables of the user choices are read from parts/choices.json (the step-2 findings
of par-03: alternatives that parts/out/ does not hold); cells {REF.field} take the schematic's
own part from availability.csv. Every user-choice row of decisions.csv must have a choice.
"""
import csv
import json
import os
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import targets as tg  # noqa: E402

OUT = REPO / "parts" / "out"
BUILD = HERE / "build"
NAVY, RED, GREY = "#1f2a44", "#c0392b", "#888888"
VERDICTS = ["JLC assemble", "consign from DigiKey", "hand-solder", "unresolved", "not fitted", "no part"]
VCOLOR = {"JLC assemble": "#2e7d32", "consign from DigiKey": "#1f6fb2", "hand-solder": "#8e6bbf",
          "unresolved": RED, "not fitted": GREY, "no part": "#bbbbbb"}
REC = "Recommendation (labelled as such, the decision is yours): "

CHOICES_FILE = REPO / "parts" / "choices.json"
CELL = re.compile(r"\{(\w+)\.(\w+)\}")


def load_choices(av, dec):
    """Choices from parts/choices.json; {REF.field} cells come from availability.csv.

    Fails when a user-choice ref of decisions.csv is in no choice, so none is left without a slide.
    """
    by_ref = {ref: r for r in av for ref in r["refs"].split(";")}

    def fill(cell):
        def sub(m):
            row = by_ref.get(m.group(1))
            if row is None or m.group(2) not in row:
                raise SystemExit(f"figures.py: {CHOICES_FILE.name}: no availability field {m.group(0)}")
            return row[m.group(2)]
        return CELL.sub(sub, cell)

    choices = json.loads(CHOICES_FILE.read_text())["choices"]
    for c in choices.values():
        c["rows"] = [[fill(x) for x in row] for row in c["rows"]]
        c["recommendation"] = REC + c["recommendation"]
    covered = {r for c in choices.values() for r in c["refs"].split(",") if r}
    missing = [d["ref"] for d in dec if d["status"] == "user-choice" and d["ref"] not in covered]
    if missing:
        raise SystemExit(f"figures.py: user-choice refs with no choice in {CHOICES_FILE.name}: {missing}")
    return choices



def num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write(name, header, rows):
    with open(BUILD / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def short(text, n):
    text = text.replace("\n", " ")
    return text if len(text) <= n else text[: n - 1].rstrip() + "..."


def refs_text(refs):
    return ", ".join(refs.split(";"))


def refs_short(refs, n=3):
    items = refs.split(";")
    return ", ".join(items) if len(items) <= n else f"{', '.join(items[:n])} +{len(items) - n}"


def status_chart(av, dec):
    lines = Counter(r["verdict"] for r in av)
    refs = Counter()
    for r in av:
        refs[r["verdict"]] += int(r["qty"])
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
    for ax, cnt, title in ((axes[0], lines, "BOM lines by route"), (axes[1], refs, "Parts per board by route")):
        names = [v for v in VERDICTS if cnt[v]][::-1]
        ax.barh(names, [cnt[v] for v in names], color=[VCOLOR[v] for v in names])
        for i, v in enumerate(names):
            ax.text(cnt[v] + max(cnt.values()) * 0.01, i, str(cnt[v]), va="center")
        ax.set_title(title)
        ax.set_xlim(0, max(cnt.values()) * 1.15)
    st = Counter(r["status"] for r in dec)
    names = ["proposed", "user-choice", "for-user"][::-1]
    cols = {"proposed": "#2e7d32", "user-choice": "#e0a100", "for-user": RED}
    axes[2].barh(names, [st[n] for n in names], color=[cols[n] for n in names])
    for i, n in enumerate(names):
        axes[2].text(st[n] + 3, i, str(st[n]), va="center")
    axes[2].set_title("Decision rows by status (refs)")
    axes[2].set_xlim(0, max(st.values()) * 1.15)
    fig.tight_layout()
    fig.savefig(BUILD / "status_summary.png", dpi=150)
    plt.close(fig)


def route_table(av):
    expl = {
        "JLC assemble": "stocked at JLC",
        "consign from DigiKey": "not at JLC, DigiKey stock",
        "hand-solder": "through-hole, in stock",
        "unresolved": "no MPN or no stock",
        "not fitted": "DNP",
        "no part": "vias, pads, holes, coupler",
    }
    rows = []
    for v in VERDICTS:
        sel = [r for r in av if r["verdict"] == v]
        rows.append([v, str(len(sel)), str(sum(int(r["qty"]) for r in sel)), expl[v]])
    write("routes.csv", ["Route", "Lines", "Parts per board", "Meaning (examples)"], rows)
    return {v: sum(1 for r in av if r["verdict"] == v) for v in VERDICTS}


def risky_rows(av, boards, dec):
    """Lines with an obsolescence, stock or lead-time risk, computed from availability.csv."""
    out = []
    for r in av:
        if r["class"] in ("dnp",) or r["verdict"] == "no part":
            continue
        need = int(r["need"])
        why = []
        if r["dk_lifecycle"] and r["dk_lifecycle"] not in ("Active",):
            why.append(r["dk_lifecycle"])
        js = num(r["jlc_stock"])
        if r["jlc_status"] in ("Available", "Low stock") and js is not None and js < 2 * need:
            why.append(f"JLC stock {int(js)} for {need}")
        wk = num(r["dk_lead_weeks"])
        if r["verdict"] != "JLC assemble" and wk is not None and wk >= 26:
            why.append(f"DigiKey lead {int(wk)} weeks")
        dks = num(r["dk_stock"])
        if r["verdict"] == "consign from DigiKey" and dks is not None and dks < 2 * need:
            why.append(f"DigiKey stock {int(dks)} for {need} needed")
        if r["verdict"] == "unresolved" and r["class"] == "mpn" and not why:
            why.append(r["reason"])
        if why:
            out.append([refs_short(r["refs"], 3), r["MPN"] or r["value"], "; ".join(why)])
    # Items the BOM numbers cannot show, read from decisions.csv: unverified codes and user choices.
    extra = []
    for d in dec:
        if d["status"] == "proposed" and "unverified" in d["reason"]:
            extra.append([d["ref"], d["MPN"], "reel code unverified in the datasheet"])
        elif d["status"] == "user-choice" and d["ref"] in ("U6", "Y2"):
            extra.append([d["ref"], d["MPN"], "user choice, see choice slide"])
    have = {r[0] for r in out}
    out += [e for e in extra if e[0] not in have]
    return out


def cost(av, boards):
    """Total for `boards` boards (need = refs x boards) priced per source on the lines it can supply."""
    jl = dk = both_j = both_d = 0.0
    n_j = n_d = n_both = n_none = n_mix = 0
    mix = 0.0
    ext = 0
    for r in av:
        if r["verdict"] in ("not fitted", "no part"):
            continue
        need = int(r["need"])
        jp, js = num(r["jlc_unit_price"]), num(r["jlc_stock"], 0)
        dp, ds = num(r["dk_unit_price"]), num(r["dk_stock"], 0)
        j_ok = r["jlc_match"] in ("exact", "package") and r["jlc_status"] in ("Available", "Low stock") \
            and jp is not None and js >= need
        d_ok = r["dk_match"] in ("exact", "package") and r["dk_status"] in ("Active", "Low stock", "NFND") \
            and dp is not None and ds >= need
        if j_ok:
            jl += jp * need
            n_j += 1
            ext += r["jlc_library"] == "Extended"
        if d_ok:
            dk += dp * need
            n_d += 1
        if j_ok and d_ok:
            both_j += jp * need
            both_d += dp * need
            n_both += 1
        if j_ok or d_ok:
            mix += min(p * need for p, ok in ((jp, j_ok), (dp, d_ok)) if ok)
            n_mix += 1
        else:
            n_none += 1
    fmt = lambda x: f"{x:,.2f}"  # noqa: E731
    per = lambda x: f"{x / boards:,.2f}"  # noqa: E731
    rows = [
        ["JLC, its lines", str(n_j), fmt(jl), per(jl)],
        ["DigiKey, its lines", str(n_d), fmt(dk), per(dk)],
        ["Both cover: JLC price", str(n_both), fmt(both_j), per(both_j)],
        ["Both cover: DigiKey price", str(n_both), fmt(both_d), per(both_d)],
        ["Cheapest per line", str(n_mix), fmt(mix), per(mix)],
        ["Not covered today", str(n_none), "not priced", "-"],
    ]
    write("cost.csv", ["Source", "Lines", f"USD for {boards} boards", "USD per board"], rows)
    return dict(boards=boards, jlc=jl, dk=dk, mix=mix, n_none=n_none, n_ext=ext, n_j=n_j, n_d=n_d, n_both=n_both)


def choice_image(key, c):
    """Render options table plus consequence and recommendation as one slide-sized picture."""
    cols, rows = c["cols"], c["rows"]
    widths = [0.24, 0.26, 0.26, 0.24]
    fs = 11.5
    fig = plt.figure(figsize=(12.1, 5.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    line_h = 0.047
    y = 0.99

    def draw_row(cells, bold=False, fill=None):
        nonlocal y
        wrapped = [textwrap.wrap(t, max(int(w * 12.1 * 72 / (fs * 0.55)) - 2, 8)) or [""]
                   for t, w in zip(cells, widths)]
        h = max(len(w) for w in wrapped) * line_h + 0.012
        if fill:
            ax.add_patch(Rectangle((0, y - h), 1, h, color=fill, lw=0))
        x = 0.005
        for lines, w in zip(wrapped, widths):
            for i, ln in enumerate(lines):
                ax.text(x, y - 0.008 - i * line_h, ln, va="top", fontsize=fs,
                        fontweight="bold" if bold else "normal", color=NAVY)
            x += w
        y -= h

    draw_row(cols, bold=True, fill="#dfe4ee")
    for i, r in enumerate(rows):
        draw_row(r, fill="#f4f6fa" if i % 2 == 0 else None)
    y -= 0.02
    for para, col, bold in ((c["consequence"], NAVY, False), (c["recommendation"], RED, True)):
        lines = textwrap.wrap(para, int(12.0 * 72 / (fs * 0.55)))
        for ln in lines:
            ax.text(0.005, y, ln, va="top", fontsize=fs, color=col, fontweight="bold" if bold else "normal")
            y -= line_h
        y -= 0.015
    if y < 0:
        raise SystemExit(f"figures.py: choice {key} overflows its picture ({y:.2f})")
    fig.savefig(BUILD / f"choice_{key}.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ts = tg.load(os.environ.get("FMCW_TARGETS", "default"))
    print(f"figures.py: {tg.describe(ts)}")
    BUILD.mkdir(exist_ok=True)
    boards = int(tg.value(ts, "board_quantity"))
    av = read(OUT / "availability.csv")
    bom = read(OUT / "bom.csv")
    dec = read(REPO / "parts" / "decisions.csv")
    if len(av) != len(bom):
        raise SystemExit(f"figures.py: availability.csv has {len(av)} lines, bom.csv {len(bom)}: rerun parts/bom.py")

    status_chart(av, dec)
    routes = route_table(av)

    # Every BOM line once: refs, value, MPN, DigiKey and JLC status, route.
    rows = []
    for r in av:
        jlc = r["jlc_status"] if r["jlc_status"] != "n/a" else "-"
        if r["jlc_library"]:
            jlc += f" {r['jlc_library']}"
        dk = r["dk_status"] if r["dk_status"] != "n/a" else "-"
        rows.append([refs_text(r["refs"]), r["qty"], r["value"], r["MPN"] or "-", dk, jlc, r["verdict"]])
    write("bom_lines.csv", ["Refs", "Qty", "Value", "MPN", "DigiKey", "JLCPCB", "Route"], rows)
    # Markdown pipe table with column widths set by the dash counts (equal widths overlap the
    # long MPNs in the PDF); inserted by {{fact:bom_table}}.
    head = ["Refs (qty)", "MPN", "DigiKey", "JLCPCB", "Route"]
    dashes = [26, 32, 12, 14, 16]
    esc = lambda s: s.replace("|", "\\|")  # noqa: E731
    md = ["| " + " | ".join(head) + " |", "|" + "|".join("-" * d for d in dashes) + "|"]
    md += [f"| {esc(r[0])} ({r[1]}) | {esc(r[3])} | {esc(r[4])} | {esc(r[5])} | {esc(r[6])} |" for r in rows]
    bom_table = "\n".join(md)

    # Suffix decisions with datasheet and page (proposed rows that name a datasheet page).
    drows = [[d["ref"], d["MPN"], d["datasheet_id"], d["page"]] for d in dec
             if d["status"] in ("proposed", "user-choice") and d["page"] and d["datasheet_id"]]
    write("suffix_decisions.csv", ["Ref", "Chosen code", "Datasheet id", "Page"], drows)
    passives = [d for d in dec if d["status"] == "proposed" and not d["page"]]

    # For the user to obtain: refs with status for-user, with what is missing.
    obtain = {}
    for d in dec:
        if d["status"] == "for-user":
            obtain.setdefault((d["datasheet_id"], d["reason"]), []).append(d["ref"])
    orows = [[", ".join(refs), short(reason, 150) or "no part number", sheet or "-"]
             for (sheet, reason), refs in obtain.items()]
    write("obtain.csv", ["Refs", "What is missing", "Datasheet id"], orows)
    write("obtain_short.csv", ["Refs", "What is missing"],
          [[a, short(b, 90)] for a, b, _ in orows])

    risk = risky_rows(av, boards, dec)
    write("risky.csv", ["Refs", "Part", "Risk"], risk)
    c = cost(av, boards)

    for key, ch in load_choices(av, dec).items():
        choice_image(key, ch)
        write(f"choice_{key}.csv", ch["cols"], ch["rows"])
        with open(BUILD / f"choice_{key}.txt", "w") as f:
            f.write(ch["consequence"] + "\n\n" + ch["recommendation"] + "\n")

    st = Counter(d["status"] for d in dec)
    facts = {
        "lines": len(av), "boards": boards,
        "placed_lines": sum(1 for r in av if r["verdict"] not in ("not fitted", "no part")),
        "n_assemble": routes["JLC assemble"], "n_consign": routes["consign from DigiKey"],
        "n_hand": routes["hand-solder"], "n_unresolved": routes["unresolved"],
        "n_proposed": st["proposed"], "n_user_choice": st["user-choice"], "n_for_user": st["for-user"],
        "n_passive_refs": len(passives), "n_suffix_rows": len(drows),
        "cost_jlc": f"{c['jlc']:,.2f}", "cost_dk": f"{c['dk']:,.2f}", "cost_mix": f"{c['mix']:,.2f}",
        "cost_mix_per_board": f"{c['mix'] / boards:,.2f}", "n_uncovered": c["n_none"],
        "n_extended": c["n_ext"],
        "bom_table": bom_table,
    }
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")
    print(f"figures.py: {len(av)} lines, routes {routes}, cost mix USD {c['mix']:.2f} for {boards} boards")


if __name__ == "__main__":
    main()
