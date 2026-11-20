#!/usr/bin/env -S uv run --quiet
"""Rebuild every analysis/NN_*/ that has a deck.yaml into reports/.

usage: build_all.py [--targets NAME] [--check] [--out DIR] [--analysis-root DIR]

Built files are never committed (reports/*.pdf and *.pptx are gitignored); run this to
recreate them. --check validates every analysis and builds nothing. Exit 1 if any fails.
Run through ./run so pandoc and LaTeX are available.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as br  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
_NAME = re.compile(r"^\d{2}_")


def find_analyses(root: Path) -> list[Path]:
    """analysis/NN_*/ directories that contain a deck.yaml, sorted by name."""
    return sorted(d for d in root.iterdir()
                  if d.is_dir() and _NAME.match(d.name) and (d / "deck.yaml").is_file())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--targets", default="default", help="target set name (default: default)")
    ap.add_argument("--check", action="store_true", help="validate only, build nothing")
    ap.add_argument("--out", default=str(REPO / "reports"), help="output directory")
    ap.add_argument("--analysis-root", default=str(REPO / "analysis"), help="folder holding NN_* analyses")
    a = ap.parse_args(argv)

    dirs = find_analyses(Path(a.analysis_root))
    if not dirs:
        print(f"error: no analysis/NN_*/ with deck.yaml under {a.analysis_root}", file=sys.stderr)
        return 1
    failed = []
    for d in dirs:
        args = [str(d), "--targets", a.targets, "--out", a.out] + (["--check"] if a.check else [])
        try:
            rc = br.main(args)
        except SystemExit as e:
            rc = 1
            if e.code not in (None, 0, 1):
                print(e.code, file=sys.stderr)
        if rc:
            failed.append(d.name)
    if failed:
        print(f"failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print(f"{'checked' if a.check else 'built'} {len(dirs)} analyses: {', '.join(d.name for d in dirs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
