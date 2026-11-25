"""Tables, figures, facts and substitution entries for the final parts report (par-13 step 5).

Run by tools/build_report.py with this folder as the working directory (env FMCW_TARGETS names the
target set, for board_quantity). Everything is read from the committed record, nothing is typed
into the report by hand:

    parts/final_parts.csv   one row per ref group and board (parts/final_parts.py checks it)
    parts/inventory.csv     parts the user has bought

Writes into build/:

    the tables of parts/final_parts.py (by_route, by_change, by_status, substitutions, ...)
    counts_route.png, counts_change.png   count tables as pictures (deck)
    counts.png                            refs by route and change class, both boards (deck)
    group_<key>.png                       one table picture per substitution group (deck)
    g_<key>.csv                           the same groups as tables (PDF)
    side.csv, counts.csv, sourcing_2rx.csv, handsolder.csv, inventory_need.csv
    facts.json                            numbers and the per-group entries (markdown) for writeup.md

A change to a row changes the report; a pending-review row stops the build until the title slide
of deck.yaml says so.
"""
import csv
import json
import os
import re
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "parts"), str(ROOT / "tools")]
import final_parts as fp  # noqa: E402
import targets as tg  # noqa: E402

BUILD = HERE / "build"
NAVY, RED, GREEN, GREY = "#1f2a44", "#c0392b", "#2e7d4f", "#888888"
W_IN, H_MAX = 12.1, 5.4
LABEL = {"2rx": "2-RX", "1rx": "1-RX"}

GROUPS = [
    ("fpga", "FPGA, ADC and clock"),
    ("power", "Power: inductors, bucks, LDO, FB4"),
    ("rf", "RF: PA, mixer, baluns, attenuators, SMA"),
    ("if", "IF op-amp"),
    ("conn", "Connectors and LEDs"),
    ("rx1adc", "1-RX only: AD9237 and its decoupling"),
    ("rx1rx2", "1-RX only: receive chain 2 not fitted"),
    ("rx1straps", "1-RX only: straps, bias and rail order"),
]
ORDER = {
    "fpga": ["U30", "U8", "U6", "Y2", "R19"],
    "power": ["L5", "U17", "U21", "U22", "U25", "FB4"],
    "rf": ["U14", "U12", "U3", "U10", "U26", "U29", "P1"],
    "if": ["U45"],
    "conn": ["CON2", "J2", "D1", "J1"],
    "rx1adc": ["U8", "C217", "C220", "C992", "C993", "C63"],
    "rx1straps": ["R91", "R92", "R93", "R990", "R992", "R993"],
}
STRAPS = {"R91", "R92", "R93", "R990", "R991", "R992", "R993", "R996"}
FIRST_OF = {
    "fpga": {"U30", "U8", "U6", "Y2", "R19"},
    "power": {"L5", "U21", "FB4", "U17", "U22", "U25"},
    "rf": {"U14", "U12", "U3", "U10", "U26", "U29", "P1"},
    "if": {"U45"},
    "conn": {"CON2", "J2", "D1", "J1"},
}


def split(text):
    return fp.split_refs(text)


def ascii_text(s):
    return (s or "").encode("ascii", "replace").decode().replace("?", "-") if not (s or "").isascii() else (s or "")


def group_of(r):
    refs = set(split(r["refs"]))
    role = r["role"]
    if r["board"] == "1rx":
        if r["fitted"] == "no" and r["change"] != "none":
            return "rx1adc" if "VCMA" in role else "rx1rx2"
        if "AD9237" in role and not refs & STRAPS or "U8" in refs:
            return "rx1adc"
        if refs & STRAPS:
            return "rx1straps"
    for g, keys in FIRST_OF.items():
        if refs & keys:
            return g
    return None


def in_entries(r):
    if r["fitted"] == "no" and r["change"] == "none":
        return False                      # not fitted upstream either
    return r["change"] != "none" or (r["status"] != "applied" and r["route"] != "")


def natkey(ref):
    m = re.match(r"([A-Za-z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def esc(s):
    s = ascii_text(s)
    return re.sub(r"([\\*_$<>\[\]~^|#@])", r"\\\1", s)


def sentence_cut(text, n):
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n]
    stop = cut.rfind(". ")
    if stop > n * 0.5:
        return cut[: stop + 1]
    return cut[: cut.rfind(" ")].rstrip(";,: ") + " ..."


def evidence_md(text):
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\S+)\s+(pp?\.?\s*\S+)$", part)
        out.append(f"`{m.group(1)}` {esc(m.group(2))}" if m else f"`{part}`")
    return "; ".join(out) if out else "none"


# ---------------------------------------------------------------- entries

def merge(rows, group):
    """Entries of one group: rows that are the same substitution on both boards are one entry."""
    sel = [r for r in rows if in_entries(r) and group_of(r) == group]
    entries = {}
    for r in sel:
        if group == "rx1rx2":
            key = (r["reason"], r["evidence"], r["analysis"], r["fallback"])
        else:
            key = (r["role"], r["original_mpn"], r["chosen_mpn"], r["lcsc"], r["route"], r["change"])
        entries.setdefault(key, []).append(r)
    out = list(entries.values())
    order = ORDER.get(group, [])

    def sk(rs):
        first = split(rs[0]["refs"])[0]
        return (order.index(first) if first in order else 99, natkey(first), rs[0]["board"])

    return sorted(out, key=sk)


def refs_union(rs):
    seen = []
    for r in rs:
        for x in split(r["refs"]):
            if x not in seen:
                seen.append(x)
    return seen


def boards_text(rs):
    bs = [LABEL[b] for b in ("2rx", "1rx") if any(r["board"] == b for r in rs)]
    return " and ".join(bs)


def field(rs, col):
    """One value if the boards agree, else '2-RX: a; 1-RX: b'."""
    vals = {}
    for r in rs:
        vals.setdefault(r[col], []).append(r["board"])
    if len(vals) == 1:
        return next(iter(vals))
    return "; ".join(f"{' and '.join(LABEL[b] for b in bs)}: {v}" for v, bs in vals.items())


def applied_text(rs):
    vals = {}
    for r in rs:
        vals.setdefault(r["applied_by"], []).append(r["board"])
    if len(vals) == 1:
        return next(iter(vals)) or "(not applied by a directive)"
    return "; ".join(f"{v or 'none'} ({' and '.join(LABEL[b] for b in bs)})" for v, bs in vals.items())


def entry_md(rs, group):
    r0 = rs[0]
    refs = refs_union(rs)
    lines = []
    if group == "rx1rx2":
        lines.append(f"#### Not fitted, 1-RX: {esc(', '.join(refs[:5]))}{' and others' if len(refs) > 5 else ''}")
        lines.append("")
        lines.append(f"- **Board:** 1-RX (not fitted, DNP)")
        lines.append(f"- **Refs ({len(refs)}):** {esc(', '.join(refs))}")
        roles = {}
        for r in rs:
            roles.setdefault(re.sub(r"^not fitted:\s*", "", r["role"]), []).extend(split(r["refs"]))
        lines.append("- **Where:** " + "; ".join(f"{esc(k)} ({esc(', '.join(v))})" for k, v in roles.items()))
        lines.append(f"- **Why:** {esc(r0['reason'])}")
        lines.append(f"- **Evidence:** {evidence_md(r0['evidence'])}")
        lines.append(f"- **Analysis behind it:** {esc(r0['analysis'])}")
        lines.append(f"- **Alternatives and fallback:** {esc(r0['fallback'])}")
        lines.append(f"- **Applied by:** {esc(applied_text(rs))}; status: {esc(field(rs, 'status'))}")
        return "\n".join(lines) + "\n"
    lines.append(f"#### {esc(', '.join(refs))}: {esc(r0['role'])}")
    lines.append("")
    kind = {"none": "kept as designed", "fields": "fields changed", "footprint": "footprint changes",
            "design": "design change"}[r0["change"]]
    lines.append(f"- **Board:** {boards_text(rs)}; refs {esc(', '.join(refs))}; "
                 f"{'not fitted' if all(r['fitted'] == 'no' for r in rs) else 'fitted'}")
    lines.append(f"- **Original:** `{ascii_text(r0['original_mpn'])}`")
    chosen = f"`{ascii_text(r0['chosen_mpn'])}`"
    extra = [x for x in (r0["manufacturer"], f"LCSC {r0['lcsc']}" if r0["lcsc"] else "",
                         f"DigiKey {r0['digikey_pn']}" if r0["digikey_pn"] else "") if x]
    lines.append(f"- **Chosen:** {chosen}" + (f" ({esc('; '.join(extra))})" if extra else ""))
    lines.append(f"- **Change class and route:** {kind}; route {r0['route'] or 'no part to buy'}")
    lines.append(f"- **Why:** {esc(field(rs, 'reason'))}")
    lines.append(f"- **Evidence (manifest id, page):** {evidence_md(field(rs, 'evidence'))}")
    lines.append(f"- **Analysis behind it:** {esc(field(rs, 'analysis'))}")
    lines.append(f"- **Alternatives and fallback:** {esc(field(rs, 'fallback'))}")
    lines.append(f"- **Applied by:** {esc(applied_text(rs))}; status: {esc(field(rs, 'status'))}")
    return "\n".join(lines) + "\n"


def group_table(entries, group):
    head = ["Board", "Refs", "Original", "Chosen", "Route", "Applied by", "Status"]
    out = []
    for rs in entries:
        r0 = rs[0]
        if group == "rx1rx2":
            for r in rs:
                out.append(["1-RX", ", ".join(split(r["refs"])), re.sub(r"^not fitted:\s*", "", r["role"]),
                            "not fitted", "-", r["applied_by"], r["status"]])
            continue
        out.append([boards_text(rs), ", ".join(refs_union(rs)), r0["original_mpn"], r0["chosen_mpn"],
                    r0["route"] or "-", applied_text(rs).replace("(not applied by a directive)", "-"),
                    field(rs, "status")])
    if group == "rx1rx2":
        head = ["Board", "Refs", "Where", "Chosen", "Route", "Applied by", "Status"]
    return head, out


# ---------------------------------------------------------------- picture tables

def render_table(path, header, rows, fracs, font=9.0, title=None):
    """A wrapped table as a PNG of 12.1 in wide; the font shrinks until it fits 5.4 in."""
    def layout(fs):
        lines_by_row = []
        for r in [header] + rows:
            cells = []
            for c, f in zip(r, fracs):
                w = max(int(f * W_IN * 72 / (fs * 0.62)) - 1, 4)
                cells.append(textwrap.wrap(str(c), w, break_long_words=True) or [""])
            lines_by_row.append(cells)
        heights = [max(len(c) for c in cells) * fs * 1.22 / 72 + 0.14 for cells in lines_by_row]
        return lines_by_row, heights

    fs = font
    while True:
        lines_by_row, heights = layout(fs)
        if sum(heights) <= H_MAX or fs <= 6.0:
            break
        fs -= 0.5
    if sum(heights) > H_MAX:
        raise SystemExit(f"error: {path.name} does not fit ({sum(heights):.2f} in at {fs} pt)")
    H = sum(heights)
    fig = plt.figure(figsize=(W_IN, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_IN)
    ax.set_ylim(H, 0)
    ax.axis("off")
    y = 0.0
    xs = [sum(fracs[:i]) * W_IN for i in range(len(fracs))]
    for i, (cells, h) in enumerate(zip(lines_by_row, heights)):
        if i == 0:
            ax.add_patch(plt.Rectangle((0, y), W_IN, h, color=NAVY))
        elif i % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y), W_IN, h, color="#eef0f5"))
        for x, c in zip(xs, cells):
            ax.text(x + 0.06, y + 0.07, "\n".join(c), va="top", ha="left", fontsize=fs,
                    color="white" if i == 0 else NAVY, fontweight="bold" if i == 0 else "normal",
                    linespacing=1.22)
        y += h
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return fs


TABLES = {}


def md_table(header, rows):
    """A pipe table whose separator line is long enough that pandoc wraps the cells (relative widths
    from the dashes); the shared {{table:}} placeholder does not, so cells overlap in the PDF."""
    cells = [[esc(str(c)).replace("\n", " ") for c in r] for r in rows]
    n = len(header)
    w = [min(max([7, len(header[i])] + [len(r[i]) for r in cells]), 30) for i in range(n)]
    scale = max(1.0, 130 / sum(w))
    seps = ["-" * max(3, round(x * scale)) for x in w]
    lines = ["| " + " | ".join(esc(h) for h in header) + " |", "|" + "|".join(seps) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in cells]
    return "\n".join(lines)


def write_csv(name, header, rows):
    BUILD.mkdir(exist_ok=True)
    TABLES["t_" + Path(name).stem] = md_table(header, rows)
    with (BUILD / name).open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- main

def nrefs(rows, **kw):
    return sum(len(split(r["refs"])) for r in rows if all(r[k] == v for k, v in kw.items()))


def main():
    BUILD.mkdir(exist_ok=True)
    rows, inventory = fp.load_parts(), fp.load_inventory()
    fp.write_tables(rows, inventory, BUILD)
    ts = tg.load(os.environ.get("FMCW_TARGETS", "default"))
    nb = int(tg.value(ts, "board_quantity"))
    pending = [r for r in rows if r["status"] == "pending review"]
    if pending:
        raise SystemExit(f"error: {len(pending)} row(s) are pending review: say so on the title slide of "
                         "deck.yaml, then drop this guard for them")
    facts = {"n_boards": nb, "pending_n": len(pending), "rows": len(rows),
             "rows_2rx": sum(r["board"] == "2rx" for r in rows), "rows_1rx": sum(r["board"] == "1rx" for r in rows)}

    # ---- counts
    cnt = []
    for b in ("2rx", "1rx"):
        sel = [r for r in rows if r["board"] == b]
        fit = [r for r in sel if r["fitted"] == "yes"]
        cnt.append({
            "groups": len(sel), "refs": nrefs(sel), "fitted": nrefs(fit), "notfit": nrefs(sel, fitted="no"),
            **{f"route:{k}": nrefs(fit, route=k) for k in ("jlc-stock", "jlc-library", "jlc-sourcing", "hand-solder", "")},
            **{f"change:{k}": nrefs(sel, change=k) for k in ("none", "fields", "footprint", "design")},
            **{f"status:{k}": nrefs(sel, status=k) for k in ("applied", "decided", "pending review")},
        })
        facts[f"refs_{b}"] = cnt[-1]["refs"]
        facts[f"fitted_{b}"] = cnt[-1]["fitted"]
        facts[f"notfit_{b}"] = cnt[-1]["notfit"]
    route_rows = [["Ref groups in the record", cnt[0]["groups"], cnt[1]["groups"]],
                  ["Refs placed", cnt[0]["refs"], cnt[1]["refs"]],
                  ["Refs fitted", cnt[0]["fitted"], cnt[1]["fitted"]],
                  ["Refs not fitted (DNP)", cnt[0]["notfit"], cnt[1]["notfit"]],
                  ["Fitted, route jlc-stock (JLC buys and places)", cnt[0]["route:jlc-stock"], cnt[1]["route:jlc-stock"]],
                  ["Fitted, route jlc-library (bought into the JLC library)", cnt[0]["route:jlc-library"], cnt[1]["route:jlc-library"]],
                  ["Fitted, route jlc-sourcing (JLC global sourcing, consigned)", cnt[0]["route:jlc-sourcing"], cnt[1]["route:jlc-sourcing"]],
                  ["Fitted, route hand-solder (DigiKey, by the user)", cnt[0]["route:hand-solder"], cnt[1]["route:hand-solder"]],
                  ["Fitted, nothing to buy (pads, vias, holes, couplers)", cnt[0]["route:"], cnt[1]["route:"]]]
    change_rows = [["Change class none (kept or only unchanged)", cnt[0]["change:none"], cnt[1]["change:none"]],
                   ["Change class fields (MPN or ordering fields only)", cnt[0]["change:fields"], cnt[1]["change:fields"]],
                   ["Change class footprint (land pattern or pin map)", cnt[0]["change:footprint"], cnt[1]["change:footprint"]],
                   ["Change class design (circuit or net change, DNP)", cnt[0]["change:design"], cnt[1]["change:design"]],
                   ["Status applied (nothing to write: no part, or DNP as upstream)", cnt[0]["status:applied"], cnt[1]["status:applied"]],
                   ["Status decided (part fields or change still to write: par-04, par-12, rx1-03)", cnt[0]["status:decided"], cnt[1]["status:decided"]],
                   ["Status pending review", cnt[0]["status:pending review"], cnt[1]["status:pending review"]]]
    hdr = ["Count of refs", "2-RX (kicad/)", "1-RX (kicad-1rx/)"]
    write_csv("counts.csv", hdr, route_rows + change_rows)
    render_table(BUILD / "counts_route.png", hdr, route_rows, [0.64, 0.18, 0.18], font=14)
    render_table(BUILD / "counts_change.png", hdr, change_rows, [0.64, 0.18, 0.18], font=14)

    # ---- figure: refs by route and change class
    fig, axs = plt.subplots(1, 2, figsize=(12.1, 5.2))
    x = range(4)
    keys = ["jlc-stock", "jlc-library", "jlc-sourcing", "hand-solder"]
    for ax, ks, pre, ttl in ((axs[0], keys, "route:", "Fitted refs by route"),
                             (axs[1], ["none", "fields", "footprint", "design"], "change:", "Refs by change class")):
        for i, (c, col) in enumerate(zip(cnt, (NAVY, RED))):
            vals = [c[pre + k] for k in ks]
            xs = [j + (i - 0.5) * 0.38 for j in x]
            bars = ax.bar(xs, vals, 0.36, color=col, label=("2-RX", "1-RX")[i])
            for b_, v in zip(bars, vals):
                ax.text(b_.get_x() + b_.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=10)
        ax.set_xticks(list(x))
        ax.set_xticklabels(ks, fontsize=11)
        ax.set_title(ttl, fontsize=14, color=NAVY)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.08)
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(BUILD / "counts.png", dpi=150)
    plt.close(fig)

    # ---- groups
    sections = {}
    for g, title in GROUPS:
        ents = merge(rows, g)
        head, trows = group_table(ents, g)
        write_csv(f"g_{g}.csv", head, trows)
        sections[g] = "\n".join(entry_md(rs, g) for rs in ents)
        facts[f"entries_{g}"] = sections[g]
        facts[f"n_{g}"] = len(ents)
        # slide pictures: if and conn share one, rf is split in two (below)
        if g in ("if", "conn", "rf"):
            continue
        if g == "rx1rx2":
            by_role = {}
            for rs in ents:
                for r in rs:
                    by_role.setdefault(re.sub(r"^not fitted:\s*", "", r["role"]), []).append(r)
            srows = [[role, f"{sum(len(split(r['refs'])) for r in rs)}: " + ", ".join(x for r in rs for x in split(r["refs"])),
                      sentence_cut(rs[0]["reason"], 90)] for role, rs in by_role.items()]
            render_table(BUILD / f"group_{g}.png", ["Where", "Refs not fitted", "Why"], srows, [0.32, 0.38, 0.30], font=10)
            continue
        srows = []
        for rs in ents:
            r0 = rs[0]
            src = r0["route"] or "-"
            srows.append([f"{', '.join(refs_union(rs))}\n({boards_text(rs).replace(' and ', ' + ')})",
                          r0["original_mpn"], f"{r0['chosen_mpn']}\n{src}" + (f"\n{r0['lcsc']}" if r0["lcsc"] else ""),
                          sentence_cut(field(rs, "reason"), 230), sentence_cut(field(rs, "fallback"), 120)])
        facts[f"slide_rows_{g}"] = len(srows)
        render_table(BUILD / f"group_{g}.png", ["Refs (board)", "Original", "Chosen, route, LCSC", "Why (full text in the PDF)",
                                                "Fallback"], srows, [0.10, 0.14, 0.15, 0.40, 0.21], font=9)
    # IF op-amp and connectors share a slide
    ifc = []
    for g in ("if", "conn"):
        for rs in merge(rows, g):
            r0 = rs[0]
            ifc.append([f"{', '.join(refs_union(rs))}\n({boards_text(rs).replace(' and ', ' + ')})", r0["original_mpn"],
                        f"{r0['chosen_mpn']}\n{r0['route'] or '-'}" + (f"\n{r0['lcsc']}" if r0["lcsc"] else ""),
                        sentence_cut(field(rs, "reason"), 170), sentence_cut(field(rs, "fallback"), 90)])
    render_table(BUILD / "group_ifconn.png", ["Refs (board)", "Original", "Chosen, route, LCSC", "Why (full text in the PDF)",
                                              "Fallback"], ifc, [0.10, 0.14, 0.15, 0.40, 0.21], font=9)
    # RF is long: two pictures
    rf = merge(rows, "rf")
    for name, part in (("rfa", rf[:4]), ("rfb", rf[4:])):
        srows = []
        for rs in part:
            r0 = rs[0]
            srows.append([f"{', '.join(refs_union(rs))}\n({boards_text(rs).replace(' and ', ' + ')})", r0["original_mpn"],
                          f"{r0['chosen_mpn']}\n{r0['route'] or '-'}" + (f"\n{r0['lcsc']}" if r0["lcsc"] else ""),
                          sentence_cut(field(rs, "reason"), 230), sentence_cut(field(rs, "fallback"), 120)])
        render_table(BUILD / f"group_{name}.png", ["Refs (board)", "Original", "Chosen, route, LCSC", "Why (full text in the PDF)",
                                                   "Fallback"], srows, [0.10, 0.14, 0.15, 0.40, 0.21], font=9)
        facts[f"slide_rows_{name}"] = len(srows)

    # ---- side by side (PDF): one line per first ref
    side = {}
    for r in rows:
        g = group_of(r)
        if not in_entries(r) or g in (None, "rx1rx2"):
            continue
        first = split(r["refs"])[0]
        d = side.setdefault(first, {"role": r["role"], "orig": r["original_mpn"], "2rx": "-", "1rx": "-", "g": g})
        d[r["board"]] = r["chosen_mpn"] + ("" if r["fitted"] == "yes" else " (not fitted)")
    srows = [[k, v["role"], v["orig"], v["2rx"], v["1rx"]] for k, v in
             sorted(side.items(), key=lambda kv: (str(kv[1]["g"]), natkey(kv[0])))]
    write_csv("side.csv", ["Ref", "Role", "Original", "2-RX chosen", "1-RX chosen"], srows)
    rx2 = [r for r in rows if group_of(r) == "rx1rx2"]
    facts["rx1rx2_refs"] = nrefs(rx2)

    # ---- sourcing
    def part_lines(sel):
        out = {}
        for r in sel:
            k = (r["chosen_mpn"], r["board"])
            d = out.setdefault(k, {"r": r, "refs": []})
            d["refs"] += split(r["refs"])
        return out

    src = part_lines([r for r in rows if r["route"] == "jlc-sourcing" and r["fitted"] == "yes"])
    s_rows = []
    for (mpn, b), d in src.items():
        r = d["r"]
        s_rows.append([mpn, LABEL[b], ", ".join(d["refs"]), len(d["refs"]), len(d["refs"]) * nb,
                       r["lcsc"] or "-", r["digikey_pn"] or "-", sentence_cut(r["reason"], 150)])
    s_head = ["Part", "Board", "Refs", "Per board", f"For {nb} boards", "LCSC", "DigiKey PN", "Why sourced"]
    write_csv("sourcing_2rx.csv", s_head, s_rows)
    render_table(BUILD / "sourcing_2rx.png", s_head, s_rows, [0.15, 0.06, 0.09, 0.06, 0.07, 0.08, 0.17, 0.32], font=10)
    facts["sourcing_lines"] = len(s_rows)
    facts["sourcing_qty"] = sum(r[4] for r in s_rows)

    hs = part_lines([r for r in rows if r["route"] == "hand-solder" and r["fitted"] == "yes"])
    h_rows = []
    for (mpn, b), d in hs.items():
        r = d["r"]
        h_rows.append([mpn, LABEL[b], ", ".join(d["refs"]), len(d["refs"]), len(d["refs"]) * nb,
                       r["digikey_pn"] or "-", sentence_cut(r["reason"], 190)])
    h_head = ["Part", "Board", "Refs", "Per board", f"For {nb} boards", "DigiKey PN", "Why hand-soldered"]
    write_csv("handsolder.csv", h_head, h_rows)
    render_table(BUILD / "handsolder.png", h_head, h_rows, [0.14, 0.06, 0.09, 0.06, 0.07, 0.15, 0.43], font=11)
    facts["handsolder_qty"] = sum(r[4] for r in h_rows)

    i_rows = []
    for inv in inventory:
        need = sum(len(split(r["refs"])) for r in rows if r["route"] == "jlc-library" and r["lcsc"] == inv["lcsc"]
                   and r["fitted"] == "yes") * nb
        qty = int(inv["qty"])
        i_rows.append([inv["mpn"], inv["lcsc"], qty, inv["date"] or "(not recorded)", inv["held"], inv["for"],
                       need, qty - need])
    i_head = ["Part", "LCSC", "Bought", "Date", "Held", "For", f"Need for {nb} boards", "Spare"]
    write_csv("inventory_need.csv", i_head, i_rows)
    render_table(BUILD / "inventory_need.png", i_head, i_rows, [0.15, 0.09, 0.07, 0.12, 0.10, 0.22, 0.15, 0.10], font=13)
    facts["inventory_missing_dates"] = sum(1 for inv in inventory if not inv["date"])

    # ---- substitutions whose fallback the record does not name (sent back to the user)
    nf = [r for r in rows if r["change"] != "none" and r["fitted"] == "yes"
          and r["fallback"].strip().lower().startswith("none")]
    write_csv("no_fallback.csv", ["Board", "Refs", "Role", "Original", "Chosen"],
              [[LABEL[r["board"]], ", ".join(split(r["refs"])), r["role"], r["original_mpn"], r["chosen_mpn"]]
               for r in nf])
    facts["no_fallback_n"] = len(nf)
    facts["no_fallback_refs"] = ", ".join(dict.fromkeys(x for r in nf for x in split(r["refs"])[:1]))

    # ---- records that still name an open analysis (PDF)
    op = {}
    for r in rows:
        if "planned" in r["analysis"] or "not run" in r["analysis"] or "open" in r["analysis"].split(";")[-1]:
            op.setdefault((r["role"], r["analysis"]), []).append(r)
    write_csv("open_analyses.csv", ["Board", "Refs", "Role", "Analysis named in the record"],
              [[boards_text(rs), ", ".join(refs_union(rs)), role, an] for (role, an), rs in op.items()])

    facts.update(TABLES)
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1))
    print(f"par-13: {len(rows)} rows, {sum(facts[f'n_{g}'] for g, _ in GROUPS)} entries, board_quantity {nb}")


if __name__ == "__main__":
    main()
