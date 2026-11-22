#!/usr/bin/env python3
"""Resolve a KiCad project directory (`--project DIR`) to its files and output paths.

    kicad/       -> fmcw3.kicad_{pro,sch,pcb}   parts/out/       checks/baseline.json
    kicad-1rx/   -> fmcw3_1rx.kicad_{...}       parts/out/1rx/   checks/baseline-1rx.json

The root files are the `.kicad_pro` in the directory and the `.kicad_sch` / `.kicad_pcb` of the
same name. A directory named `kicad-<tag>` gets the tag `<tag>` for its output paths; plain
`kicad` has none, so its paths stay what they were before `--project` existed.
Nothing here writes anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = "kicad"


class ProjectError(Exception):
    """An unknown or malformed project directory; the message says what to do."""


@dataclass(frozen=True)
class Project:
    dir: Path
    name: str
    tag: str

    @property
    def pro(self) -> Path:
        return self.dir / f"{self.name}.kicad_pro"

    @property
    def sch(self) -> Path:
        return self.dir / f"{self.name}.kicad_sch"

    @property
    def pcb(self) -> Path:
        return self.dir / f"{self.name}.kicad_pcb"

    @property
    def parts_out(self) -> Path:
        base = ROOT / "parts" / "out"
        return base / self.tag if self.tag else base

    @property
    def baseline(self) -> Path:
        return ROOT / "checks" / (f"baseline-{self.tag}.json" if self.tag else "baseline.json")


def resolve(project: str | Path = DEFAULT) -> Project:
    """`project` is a directory, absolute or relative to the repo root."""
    d = Path(project)
    if not d.is_absolute():
        d = ROOT / d
    d = d.resolve() if d.exists() else d
    if not d.is_dir():
        known = sorted(p.name for p in ROOT.glob("kicad*") if p.is_dir())
        raise ProjectError(f"unknown project directory {str(project)!r}: {d} is not a directory "
                           f"(projects here: {', '.join(known) or 'none'})")
    pros = sorted(d.glob("*.kicad_pro"))
    if len(pros) != 1:
        raise ProjectError(f"{d} has {len(pros)} .kicad_pro files; a project directory needs "
                           "exactly one")
    name = pros[0].stem
    for ext in ("kicad_sch", "kicad_pcb"):
        if not (d / f"{name}.{ext}").is_file():
            raise ProjectError(f"{d}: missing {name}.{ext}")
    tag = d.name[len("kicad-"):] if d.name.startswith("kicad-") else ""
    return Project(d, name, tag)


def resolve_or_exit(project: str | Path = DEFAULT) -> Project:
    try:
        return resolve(project)
    except ProjectError as e:
        raise SystemExit(f"error: {e}")
