#!/usr/bin/env -S uv run --quiet
"""Turn an analysis folder into reports/NN_name.pdf and reports/NN_name.pptx.

usage: build_report.py <analysis dir> [--targets NAME] [--check] [--out DIR]

Runs <dir>/figures.py (cwd = the analysis dir, env FMCW_TARGETS = target set name), then
--check: validates deck.yaml and writeup.md references and text fit, builds nothing;
otherwise: builds the PDF with pandoc and the deck with python-pptx.
Run through ./run so pandoc and LaTeX are available.
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
        expand_report(text, adir / "build", ts or {"name": "?", "parameters": {}})
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
            return f"Target set used: {tg.describe(ts)}.\n\n{tg.format_table(ts)}" if ts["parameters"] else ""
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
    slides = load_deck(adir)
    errs = check_deck(slides, build) + check_report(adir, ts)
    if errs:
        print("check failed:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1
    if a.check:
        print(f"check ok: {adir.name} ({len(slides)} slides)")
        return 0
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    build_pdf(adir, out / f"{adir.name}.pdf", ts)
    build_pptx(slides, build, out / f"{adir.name}.pptx")
    print(f"built {out / (adir.name + '.pdf')} and {out / (adir.name + '.pptx')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
