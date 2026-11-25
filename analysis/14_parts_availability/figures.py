"""Tables, figures, facts and the deck for the parts-availability report (par-14 step 4).

Run by tools/build_report.py with this folder as the working directory. Reads the latest snapshot
folder under parts/out/availability/ (written by parts/availability_report.py; env
FMCW_AVAIL_DIR overrides the base folder) and writes into build/:

    status_counts.csv/.png     status counts per board
    short.csv/.png, thin.csv/.png, unknown.csv     lines that need action, with need, stock,
                                inventory, route and fallback
    changes.csv/.png           lines whose status or stock changed since the previous snapshot
    sourced.csv/.png           jlc-sourcing and hand-solder lines with DigiKey stock
    facts.json                 numbers and markdown tables for writeup.md

It also writes deck.yaml (the slide titles carry the snapshot date, so the deck is generated, never
edited by hand). The deck has at most 10 slides including the targets slides build_report.py adds.
Running the build again after a new snapshot gives the new report.
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
import yaml  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "parts"), str(ROOT / "tools")]
import availability_report as av  # noqa: E402

BUILD = HERE / "build"
NAVY = "#1f2a44"
W_IN, H_MAX = 12.1, 5.4
LABEL = {"2rx": "2-RX", "1rx": "1-RX"}
STATUSES = ["short", "thin", "unknown", "ok", "no part"]
MAX_ROWS = 14           # most rows of one table on a slide; the rest stay in the PDF and lines.csv
TARGET_SLIDES = 2       # build_report.py adds up to two targets slides after the title


def fnum(x):
    return "-" if x in ("", None) else str(x)


def ascii_text(s):
    s = s or ""
    return s if s.isascii() else s.encode("ascii", "replace").decode().replace("?", "-")


def esc(s):
    return re.sub(r"([\\*_$<>\[\]~^|#@])", r"\\\1", ascii_text(s))


def md_table(header, rows):
    """A pipe table whose separator is long enough that pandoc wraps cells (see par-13)."""
    cells = [[esc(str(c)).replace("\n", " ") for c in r] for r in rows]
    n = len(header)
    w = [min(max([7, len(header[i])] + [len(r[i]) for r in cells]), 30) for i in range(n)]
    scale = max(1.0, 130 / sum(w))
    seps = ["-" * max(3, round(x * scale)) for x in w]
    lines = ["| " + " | ".join(esc(h) for h in header) + " |", "|" + "|".join(seps) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in cells]
    return "\n".join(lines)


def render_table(path, header, rows, fracs, font=10.0):
    """A wrapped table as a PNG 12.1 in wide. Returns True if it fits 5.4 in at 6 pt or more."""
    def layout(fs):
        out = []
        for r in [header] + rows:
            cells = []
            for c, f in zip(r, fracs):
                w = max(int(f * W_IN * 72 / (fs * 0.62)) - 1, 4)
                cells.append(textwrap.wrap(ascii_text(str(c)), w, break_long_words=True) or [""])
            out.append(cells)
        return out, [max(len(c) for c in cells) * fs * 1.22 / 72 + 0.14 for cells in out]

    fs = font
    while True:
        lines_by_row, heights = layout(fs)
        if sum(heights) <= H_MAX or fs <= 6.0:
            break
        fs -= 0.5
    if sum(heights) > H_MAX:
        return False
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
    return True


def write_csv(name, header, rows):
    with (BUILD / name).open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def picture(name, header, rows, fracs, empty_msg, font=10.0):
    """Table picture for a slide with the first rows that fit; returns (shown, total)."""
    total = len(rows)
    if not rows:
        render_table(BUILD / name, header, [[empty_msg] + [""] * (len(header) - 1)], fracs, font)
        return 0, 0
    n = min(total, MAX_ROWS)
    while n > 1 and not render_table(BUILD / name, header, rows[:n], fracs, font):
        n -= 1
    if n == 1 and not render_table(BUILD / name, header, rows[:1], fracs, font):
        raise SystemExit(f"error: {name} does not fit even with one row")
    return n, total


def line_row(r):
    stock = r["stock"]
    return [LABEL[r["board"]], r["refs"][:40], r["chosen_mpn"], r["route"], r["need"], fnum(stock),
            fnum(r["inventory"]) if r["route"] == "jlc-library" else "-", r["fallback"]]


LINE_HEAD = ["Board", "Refs", "Part", "Route", "Need", "Stock", "Inventory", "Fallback"]
LINE_FRACS = [0.05, 0.10, 0.14, 0.09, 0.04, 0.05, 0.08, 0.45]


def short_cut(text, n):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: text.rfind(" ", 0, n)].rstrip(";,: ") + " ..."


def main():
    BUILD.mkdir(exist_ok=True)
    base = Path(os.environ.get("FMCW_AVAIL_DIR", av.OUT))
    snaps = [p for p in av.snapshots(base) if (p / "lines.csv").is_file() and (p / "summary.json").is_file()]
    if not snaps:
        raise SystemExit(f"error: no snapshot under {base}: run parts/availability_report.py first")
    snap = snaps[-1]
    lines = av.read_lines(snap)
    summary = json.loads((snap / "summary.json").read_text())
    with (snap / "changes.csv").open(newline="") as fh:
        changes = list(csv.DictReader(fh))
    prev = summary.get("previous_snapshot") or ""
    date, dbdate = snap.name, summary["jlc_database_date"]

    # ---- status counts per board
    boards = [b for b in ("2rx", "1rx") if b in summary["counts_by_board"]]
    head = ["Status"] + [LABEL[b] for b in boards] + ["Both"]
    srows = []
    for s in STATUSES:
        vals = [summary["counts_by_board"][b].get(s, 0) for b in boards]
        srows.append([s] + vals + [sum(vals)])
    srows.append(["Lines"] + [sum(summary["counts_by_board"][b].values()) for b in boards] + [summary["lines"]])
    write_csv("status_counts.csv", head, srows)
    render_table(BUILD / "status_counts.png", head, srows, [0.4] + [0.6 / (len(head) - 1)] * (len(head) - 1), font=14)

    # ---- short, thin, unknown
    def sel(status):
        return [r for r in lines if r["status"] == status]

    pics = {}
    for status in ("short", "thin"):
        rs = sel(status)
        write_csv(f"{status}.csv", LINE_HEAD, [line_row(r) for r in rs])
        rows = [line_row(r)[:-1] + [short_cut(r["fallback"], 170)] for r in rs]
        pics[status] = picture(f"{status}.png", LINE_HEAD, rows, LINE_FRACS, f"no {status} lines", font=10)
    unk = sel("unknown")
    write_csv("unknown.csv", ["Board", "Refs", "Part", "Route", "Need", "Why no data"],
              [[LABEL[r["board"]], r["refs"][:40], r["chosen_mpn"], r["route"], r["need"], r["note"]] for r in unk])

    # ---- changes
    chead = ["Board", "Refs", "Change", "Status", "Stock", "Need"]
    crows = [[LABEL[c["board"]], c["refs"][:40], c["change"], f"{c['old_status'] or '-'} -> {c['new_status'] or '-'}",
              f"{fnum(c['old_stock'])} -> {fnum(c['new_stock'])}", c["need"]] for c in changes]
    write_csv("changes.csv", chead, crows)
    pics["changes"] = picture("changes.png", chead, crows, [0.07, 0.25, 0.12, 0.2, 0.2, 0.16],
                              "no line changed" if prev else "first snapshot: nothing to compare", font=11)

    # ---- sourced and hand-solder lines with DigiKey stock
    dk = [r for r in lines if r["route"] in av.DK_ROUTES]
    dhead = ["Board", "Refs", "Part", "Route", "Need", "DigiKey stock", "DigiKey status", "Status"]
    drows = [[LABEL[r["board"]], r["refs"][:40], r["chosen_mpn"], r["route"], r["need"], fnum(r["dk_stock"]),
              r["dk_status"] or "-", r["status"]] for r in dk]
    write_csv("sourced.csv", dhead, drows)
    pics["sourced"] = picture("sourced.png", dhead, drows, [0.06, 0.12, 0.20, 0.11, 0.06, 0.12, 0.18, 0.15],
                              "no sourced or hand-solder lines", font=11)

    # ---- facts for writeup.md
    facts = {"snapshot": date, "jlc_database_date": dbdate, "digikey": summary["digikey"],
             "boards": summary["boards"], "spares": summary["spares"], "lines": summary["lines"],
             "short": summary["short"], "thin": summary["thin"], "unknown": summary["unknown"], "ok": summary["ok"],
             "previous": prev or "none (first snapshot)", "n_changes": len(changes), "lag_note": summary["lag_note"],
             "n_dk": len(dk),
             "t_counts": md_table(head, srows),
             "t_short": md_table(LINE_HEAD, [line_row(r) for r in sel("short")]) if sel("short") else "None.",
             "t_thin": md_table(LINE_HEAD, [line_row(r) for r in sel("thin")]) if sel("thin") else "None.",
             "t_unknown": md_table(["Board", "Refs", "Part", "Route", "Need", "Why no data"],
                                   [[LABEL[r["board"]], r["refs"][:40], r["chosen_mpn"], r["route"], r["need"], r["note"]]
                                    for r in unk]) if unk else "None.",
             "t_changes": md_table(chead, crows) if crows else ("No line changed." if prev else "First snapshot: nothing to compare."),
             "t_sourced": md_table(dhead, drows) if drows else "None."}
    (BUILD / "facts.json").write_text(json.dumps(facts, indent=1))

    # ---- deck (generated: titles carry the snapshot date)
    def shown(key, what):
        n, total = pics[key]
        return f"{what}" if n >= total else f"{what}, first {n} of {total}"

    slides = [
        {"layout": "title", "title": f"Parts availability {date}",
         "bullets": [f"Snapshot {date}, JLC database {dbdate} (daily, can lag the live site)",
                     f"{summary['lines']} lines, {summary['boards']} boards: short {summary['short']}, "
                     f"thin {summary['thin']}, unknown {summary['unknown']}"],
         "note": f"Built by figures.py from parts/out/availability/{date}/. DigiKey: {summary['digikey']}. "
                 f"{summary['spares']} spares per line not in the JLC Basic library. Previous snapshot: {prev or 'none'}. "
                 "Rerun parts/availability_report.py and the build for a newer snapshot. "
                 "Check every short or thin JLC line on the JLC page (pre-order status is not in the database)."},
        {"layout": "figure", "title": f"Status counts per board ({date})", "figure": "status_counts.png",
         "note": "short: stock below the need; thin: covers the need with less than 3 times the need left; ok; "
                 "unknown: no data (not in the database, or no DigiKey answer cached); no part: pads, vias, holes."},
        {"layout": "figure", "title": f"Short lines: act first ({summary['short']})", "figure": "short.png",
         "note": shown("short", "Need = refs per board x boards + spares. Stock is JLC stock (plus inventory for jlc-library) or DigiKey stock for sourced lines. Check on the JLC page; pre-order status is not in the database") +
                 ". Every line with its fallback is in short.csv and the PDF. A short line goes back to the user; no part was changed."},
        {"layout": "figure", "title": f"Thin lines: watch ({summary['thin']})", "figure": "thin.png",
         "note": shown("thin", "Covered, but stock minus need is below 3 times the need") + ". Full list in thin.csv and the PDF."},
        {"layout": "figure", "title": f"Changes since {prev or 'the last snapshot'}", "figure": "changes.png",
         "note": shown("changes", f"{len(changes)} line(s) changed in status or stock") + ". Lines that appeared or disappeared are included."},
        {"layout": "figure", "title": "Sourced and hand-solder lines: DigiKey stock", "figure": "sourced.png",
         "note": shown("sourced", "jlc-sourcing lines are bought by JLC from distributors; hand-solder lines are bought by the user") +
                 ". Stock is from the DigiKey cache or live answer named on the title slide."},
    ]
    if unk:
        slides.append({"layout": "decisions", "title": f"Unknown lines ({len(unk)}): no stock data",
                       "bullets": [short_cut(f"{LABEL[r['board']]} {r['refs'][:20]} {r['chosen_mpn']}: {r['note']}", 150)
                                   for r in unk[:8]] + ([f"and {len(unk) - 8} more (unknown.csv)"] if len(unk) > 8 else []),
                       "note": "Unknown is not ok: a part not named yet (R19 by par-12) or without a cached DigiKey answer. "
                               "Run parts/availability_report.py without --offline to fill the DigiKey cache."})
    assert len(slides) + TARGET_SLIDES <= 10, "deck would exceed 10 slides"
    header = ("# Generated by figures.py from the latest snapshot; do not edit by hand "
              "(the build rewrites it).\n")
    (HERE / "deck.yaml").write_text(header + yaml.safe_dump({"slides": slides}, sort_keys=False, width=100,
                                                              allow_unicode=False))
    print(f"par-14: snapshot {date}, {summary['lines']} lines, short {summary['short']}, thin {summary['thin']}, "
          f"{len(slides)} slides (+ targets)")


if __name__ == "__main__":
    main()
