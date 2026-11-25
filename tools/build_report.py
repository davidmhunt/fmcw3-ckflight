#!/usr/bin/env -S uv run --quiet
"""Turn an analysis folder into reports/NN_name.pdf and reports/NN_name.pptx.

usage: build_report.py <analysis dir> [--targets NAME] [--check] [--out DIR]

An analysis whose deck.yaml has `archive: true` is written to <out>/archive/ (reports/archive/).

Runs <dir>/figures.py (cwd = the analysis dir, env FMCW_TARGETS = target set name), then
--check: validates deck.yaml and writeup.md references and text fit, builds nothing;
otherwise: builds the PDF with pandoc, the deck with python-pptx and the deck as a PDF
(reports/NN_name_ppt.pdf) with LibreOffice Impress headless. A targets slide (design targets
first) follows the title slide of every deck. Run through ./run so pandoc, LaTeX and
LibreOffice are available.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_template as dt  # noqa: E402
import targets as tg  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)[^)]*\)")


def run_figures(adir: Path, targets: str) -> None:
    script = adir / "figures.py"
    if not script.is_file():
        raise SystemExit(f"error: {script} not found")
    env = dict(os.environ, FMCW_TARGETS=targets)
    r = subprocess.run([sys.executable, str(script)], cwd=adir, env=env)
    if r.returncode:
        raise SystemExit(f"error: figures.py failed ({r.returncode})")


def load_deck(adir: Path) -> list[dict]:
    p = adir / "deck.yaml"
    if not p.is_file():
        raise SystemExit(f"error: {p} not found")
    data = yaml.safe_load(p.read_text()) or {}
    slides = data.get("slides") if isinstance(data, dict) else None
    if not isinstance(slides, list) or not slides:
        raise SystemExit(f"error: {p} has no 'slides' list")
    return slides


def is_archived(adir: Path) -> bool:
    """True when deck.yaml has `archive: true`: the built files go to <out>/archive/."""
    p = adir / "deck.yaml"
    data = yaml.safe_load(p.read_text()) if p.is_file() else None
    return bool(isinstance(data, dict) and data.get("archive") is True)


def output_dir(adir: Path, out: Path) -> Path:
    return out / "archive" if is_archived(adir) else out


def check_deck(slides: list[dict], build: Path) -> list[str]:
    """Problems with a slide list: bad layout, missing figure/table, text overflow."""
    errs: list[str] = []
    for i, s in enumerate(slides, 1):
        where = f"slide {i} ({s.get('title', '?')!r})"
        layout = s.get("layout")
        if layout not in dt.LAYOUTS:
            errs.append(f"{where}: layout {layout!r} not one of {', '.join(dt.LAYOUTS)}")
            continue
        if not s.get("title"):
            errs.append(f"{where}: missing title")
        for key in ("figure", "table"):
            if layout == key:
                ref = s.get(key)
                if not ref:
                    errs.append(f"{where}: layout {key} needs a '{key}' entry")
                elif not (build / ref).is_file():
                    errs.append(f"{where}: missing {key} build/{ref}")
                elif key == "table":
                    errs += [f"{where}: {m}" for m in dt.table_problems(dt.read_csv(build / ref))]
        errs += [f"{where}: {m}" for m in dt.overflow_problems(s)]
    return errs


def check_report(adir: Path, ts: dict | None = None) -> list[str]:
    """Problems in writeup.md: unresolved local links/images and unresolved placeholders."""
    p = adir / "writeup.md"
    if not p.is_file():
        return [f"{p} not found"]
    text = p.read_text()
    errs = []
    for m in _LINK.finditer(text):
        ref = m.group(1)
        if re.match(r"^(https?:|mailto:|#)", ref):
            continue
        if not (adir / ref).exists():
            errs.append(f"writeup.md: unresolved reference {ref}")
    try:
        expand_report(text, adir / "build", ts or {"name": "?"})
    except ValueError as e:
        errs.append(f"writeup.md: {e}")
    return errs


def _csv_table(path: Path) -> str:
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    esc = lambda c: c.replace("|", "\\|")  # noqa: E731
    out = ["| " + " | ".join(esc(c) for c in rows[0]) + " |",
           "|" + "|".join("---" for _ in rows[0]) + "|"]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows[1:]]
    return "\n".join(out)


_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)(?::([^}\s]+))?\s*\}\}")


def expand_report(text: str, build: Path, ts: dict) -> str:
    """Replace placeholders in writeup.md with generated content, so nothing is typed by hand.

    {{targets}}      the target set used (name, status count, value table), from --targets
    {{table:F.csv}}  build/F.csv as a markdown table
    {{fact:KEY}}     KEY from build/facts.json (written by figures.py)
    """
    def sub(m: re.Match) -> str:
        kind, arg = m.group(1), m.group(2)
        if kind == "targets":
            return (f"Target set used: {tg.describe(ts)}. Design targets first, then performance "
                    f"targets; range resolution is derived, not set.\n\n{tg.format_table(ts)}"
                    if ts.get("design") else "")
        if kind == "table" and arg:
            f = build / arg
            if not f.is_file():
                raise ValueError(f"missing table build/{arg}")
            return _csv_table(f)
        if kind == "fact" and arg:
            f = build / "facts.json"
            facts = json.loads(f.read_text()) if f.is_file() else {}
            if arg not in facts:
                raise ValueError(f"unknown fact {arg!r} (build/facts.json)")
            return str(facts[arg])
        raise ValueError(f"bad placeholder {m.group(0)}")
    return _PLACEHOLDER.sub(sub, text)


def build_pdf(adir: Path, out: Path, ts: dict) -> None:
    if not shutil.which("pandoc"):
        raise SystemExit("error: pandoc not found (run through ./run)")
    expanded = adir / "build" / "writeup.expanded.md"
    expanded.write_text(expand_report((adir / "writeup.md").read_text(), adir / "build", ts))
    subprocess.run(
        ["pandoc", str(expanded.relative_to(adir)), "-o", str(out), "--resource-path", str(adir),
         "-V", "geometry:margin=2.2cm"],
        cwd=adir, check=True)


def build_pptx(slides: list[dict], build: Path, out: Path) -> None:
    prs = dt.new_presentation()
    for s in slides:
        dt.add_slide(prs, s, build)
    prs.save(str(out))


TARGETS_CSV = "targets_design.csv"
PERF_CSV = "targets_performance.csv"


def with_targets_slide(slides: list[dict], build: Path, ts: dict) -> list[dict]:
    """Write the target tables into build/ and put a design-targets slide (with the derived
    range resolution), then a performance-targets slide if the set has any, right after the
    title slide, so the design targets are printed first in every deck."""
    build.mkdir(exist_ok=True)
    for name, groups in ((TARGETS_CSV, ("design", "derived")), (PERF_CSV, ("performance",))):
        with open(build / name, "w", newline="") as f:
            csv.writer(f).writerows(tg.rows(ts, groups))
    if any(s.get("table") == TARGETS_CSV for s in slides):
        return slides
    new = [{"layout": "table", "title": f"Design targets: {ts['name']}", "table": TARGETS_CSV,
            "note": f"{tg.describe(ts)}. Range resolution is derived from the bandwidth, not set."}]
    if ts.get("performance"):
        new.append({"layout": "table", "title": f"Performance targets: {ts['name']}", "table": PERF_CSV,
                    "note": "Optional extras, printed after the design targets."})
    at = 1 if slides and slides[0].get("layout") == "title" else 0
    return slides[:at] + new + slides[at:]


def soffice_bin() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def build_deck_pdf(pptx: Path, out: Path) -> None:
    """Export the deck to a PDF with LibreOffice Impress headless (out = reports/NN_name_ppt.pdf)."""
    exe = soffice_bin()
    if not exe:
        raise SystemExit("error: soffice not found (LibreOffice Impress; run through ./run)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        r = subprocess.run(
            [exe, f"-env:UserInstallation={(tmp_p / 'profile').as_uri()}", "--headless",
             "--convert-to", "pdf", "--outdir", str(tmp_p), str(pptx)],
            capture_output=True, text=True)
        produced = tmp_p / (pptx.stem + ".pdf")
        if r.returncode or not produced.is_file():
            raise SystemExit(f"error: LibreOffice export failed ({r.returncode}): {r.stderr.strip()}")
        shutil.move(str(produced), str(out))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("analysis_dir")
    ap.add_argument("--targets", default="default", help="target set name (default: default)")
    ap.add_argument("--check", action="store_true", help="validate only, build nothing")
    ap.add_argument("--out", default=str(REPO / "reports"), help="output directory")
    a = ap.parse_args(argv)

    adir = Path(a.analysis_dir).resolve()
    if not adir.is_dir():
        raise SystemExit(f"error: {adir} is not a directory")
    try:
        ts = tg.load(a.targets)
    except tg.TargetError as e:
        raise SystemExit(f"error: {e}")
    print(f"using {tg.describe(ts)}")
    print(tg.format_table(ts))
    run_figures(adir, a.targets)
    build = adir / "build"
    slides = with_targets_slide(load_deck(adir), build, ts)
    errs = check_deck(slides, build) + check_report(adir, ts)
    if a.check and not soffice_bin():
        errs.append("soffice not found: the deck PDF export needs LibreOffice Impress (run through ./run)")
    if errs:
        print("check failed:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1
    if a.check:
        print(f"check ok: {adir.name} ({len(slides)} slides)")
        return 0
    out = output_dir(adir, Path(a.out))
    out.mkdir(parents=True, exist_ok=True)
    build_pdf(adir, out / f"{adir.name}.pdf", ts)
    build_pptx(slides, build, out / f"{adir.name}.pptx")
    build_deck_pdf(out / f"{adir.name}.pptx", out / f"{adir.name}_ppt.pdf")
    print(f"built {out / (adir.name + '.pdf')}, {out / (adir.name + '.pptx')} "
          f"and {out / (adir.name + '_ppt.pdf')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
