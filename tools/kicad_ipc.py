#!/usr/bin/env -S uv run --quiet --group ipc python
"""Drive a running KiCad 10 session through its IPC API (kicad-python, `kipy`).

Library plus CLI.  Run natively, because the API socket belongs to the GUI on the host:

    K="./run --native uv run --group ipc python tools/kicad_ipc.py"
    $K status [--project DIR | PROJECT.kicad_pro]     # DIR: kicad (default) or kicad-1rx
    $K show --refs U30 --nets /ADF_DATA [--sch|--pcb]
    $K set-fields FIELDS.csv [--dry-run]

Rules: this module never calls `save`, `save_as` or `revert` on a document; the user saves.
`kipy` is imported lazily, so the module (and its tests, which use fakes) loads without it.

Known limit (found in step 2): kicad-python 0.8.0 marks its whole schematic API "KiCad 11" and
`kipy.schematic_types` does not even import against its own protobufs.  Schematic operations
therefore refuse with a clear message until a release that works is pinned; the board side works.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence

DEFAULT_PROJECT = "kicad/fmcw3.kicad_pro"
DOCTYPE_SCHEMATIC = 1  # kipy DocumentType.DOCTYPE_SCHEMATIC
DOCTYPE_PCB = 3  # kipy DocumentType.DOCTYPE_PCB
KICAD_PROCESS_NAMES = ("kicad", "pcbnew", "eeschema")
BUILTIN_FIELDS = {
    "reference": "reference_field",
    "value": "value_field",
    "footprint": "footprint_field",
    "datasheet": "datasheet_field",
    "description": "description_field",
}


class IpcError(Exception):
    """A refusal or failure the CLI reports as one message."""


class VersionMismatch(IpcError):
    pass


# ---------------------------------------------------------------- connection

def kicad_running() -> bool:
    """True when any KiCad process (kicad, pcbnew, eeschema) exists."""
    for name in KICAD_PROCESS_NAMES:
        if subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0:
            return True
    return False


def connect():
    """Open a kipy connection to the GUI's API socket (raises if kipy is missing)."""
    try:
        from kipy import KiCad
    except ImportError as exc:
        raise IpcError(
            "kicad-python (kipy) is not installed; run natively with the ipc group: "
            "./run --native uv run --group ipc python tools/kicad_ipc.py ..."
        ) from exc
    return KiCad(client_name="fmcw3-ckflight-tools")


def _vtuple(v) -> tuple[int, int, int]:
    return (int(v.major), int(v.minor), int(v.patch))


def check_version(kicad) -> None:
    """Refuse unless KiCad is the same major.minor as the API and no newer in patch."""
    k, a = _vtuple(kicad.get_version()), _vtuple(kicad.get_api_version())
    if k[:2] != a[:2] or k > a:
        raise VersionMismatch(
            f"refusing: KiCad {'.'.join(map(str, k))} does not match the kicad-python API "
            f"{'.'.join(map(str, a))} (need the same major.minor and a KiCad patch no newer)"
        )


# -------------------------------------------------------------------- status

def _doc_paths(doc) -> Iterable[Path]:
    """Candidate project file paths for an open document."""
    proj = getattr(doc, "project", None)
    if proj is not None and getattr(proj, "path", ""):
        base = Path(proj.path)
        if base.suffix == ".kicad_pro":
            yield base
        else:
            yield base / f"{proj.name}.kicad_pro"
    bf = getattr(doc, "board_filename", "")
    if bf:
        yield Path(bf).with_suffix(".kicad_pro")


def _open_docs(kicad) -> list:
    docs = []
    for t in (DOCTYPE_SCHEMATIC, DOCTYPE_PCB):
        docs.extend(kicad.get_open_documents(t))
    return docs


def has_project_open(kicad, project: Path) -> bool:
    want = Path(project).resolve()
    for doc in _open_docs(kicad):
        for p in _doc_paths(doc):
            if p.resolve() == want:
                return True
    return False


def project_file(project_dir: str | None = None, project_file_arg: str | None = None) -> Path:
    """The .kicad_pro that `status` asks about: `--project DIR` (resolved by tools/project.py,
    an unknown directory is an IpcError), else the positional .kicad_pro, else the default."""
    if project_dir and project_file_arg:
        raise IpcError("give either --project DIR or a .kicad_pro path, not both")
    if project_dir:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import project
        try:
            return project.resolve(project_dir).pro
        except project.ProjectError as exc:
            raise IpcError(str(exc)) from exc
    return Path(project_file_arg or DEFAULT_PROJECT)


def status(project: str | Path = DEFAULT_PROJECT, *,
           connect_fn: Callable = connect,
           running_fn: Callable[[], bool] = kicad_running) -> str:
    """Return 'ipc', 'closed' or 'other'."""
    if not running_fn():
        return "closed"
    try:
        kicad = connect_fn()
        kicad.ping()
        return "ipc" if has_project_open(kicad, Path(project)) else "other"
    except Exception:
        return "other"


# ---------------------------------------------------------------- editors

def _open_pcb(kicad):
    return kicad.get_board()


def _open_sch(kicad):
    try:
        from kipy.schematic import Schematic
    except Exception as exc:
        raise IpcError(
            "schematic editing is unavailable: kicad-python 0.8.0 targets the schematic API "
            f"of KiCad 11 and its schematic module does not import ({exc})"
        ) from exc
    docs = kicad.get_open_documents(DOCTYPE_SCHEMATIC)
    if not docs:
        raise IpcError("no schematic is open in KiCad")
    return Schematic(kicad._client, docs[0])


def _ref(sym_or_fp) -> str:
    return sym_or_fp.reference_field.text.value


def _kiid(item) -> str:
    i = item.id
    return getattr(i, "value", i)


def show(kicad, refs: Sequence[str] = (), nets: Sequence[str] = (), *,
         sch: bool = True, pcb: bool = True,
         open_pcb: Callable = _open_pcb, open_sch: Callable = _open_sch) -> dict:
    """Select refs and nets in the editors.  Returns {'pcb': {key: [ids]}, 'sch': {...}}."""
    check_version(kicad)
    out: dict = {}
    if pcb:
        board = open_pcb(kicad)
        found: dict[str, list] = {}
        items: list = []
        want = set(refs)
        for fp in board.get_footprints():
            if _ref(fp) in want:
                found[_ref(fp)] = [_kiid(fp)]
                items.append(fp)
        by_name = {n.name: n for n in board.get_nets()}
        for name in nets:
            if name in by_name:
                got = list(board.get_items_by_net(by_name[name]))
                found[name] = [_kiid(i) for i in got]
                items.extend(got)
        board.clear_selection()
        if items:
            board.add_to_selection(items)
        out["pcb"] = found
    if sch:
        s = open_sch(kicad)
        found = {}
        items = []
        want = set(refs)
        for sym in s.get_symbols():
            if _ref(sym) in want:
                found[_ref(sym)] = [_kiid(sym)]
                items.append(sym)
        wanted_nets = set(nets)
        for lab in s.get_labels():
            if lab.text.value in wanted_nets:
                found.setdefault(lab.text.value, []).append(_kiid(lab))
                items.append(lab)
        s.clear_selection()
        if items:
            s.add_to_selection(items)
        out["sch"] = found
    return out


# ------------------------------------------------------------ edit guards

def require_no_schematic_open(kicad) -> None:
    """Refuse a board edit while the Schematic Editor is open (KiCad 10 freezes, then quits)."""
    if list(kicad.get_open_documents(DOCTYPE_SCHEMATIC)):
        raise IpcError(
            "refusing: board edits through IPC need the Schematic Editor closed on KiCad 10, "
            "because KiCad freezes on begin_commit otherwise; close the Schematic Editor "
            "and retry"
        )


def require_schematic_api(kicad) -> None:
    """Refuse schematic edits below KiCad 11, which has no schematic API."""
    if _vtuple(kicad.get_version())[0] < 11:
        raise IpcError(
            "refusing: there is no schematic API in KiCad 10 (it arrives in KiCad 11); "
            "close KiCad and use file-level edits of the .kicad_sch instead"
        )


def begin_board_commit(kicad, board):
    """Start a board commit after the guard; the only way this tool begins one on a board."""
    require_no_schematic_open(kicad)
    return board.begin_commit()


# --------------------------------------------------------------- set-fields

def read_csv(path: str | Path) -> list[tuple[str, str, str]]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows and not {"ref", "field", "value"} <= set(rows[0]):
        raise IpcError("CSV needs the columns ref, field, value")
    return [(r["ref"].strip(), r["field"].strip(), r["value"]) for r in rows]


def _get_field(sym, name: str):
    """Return the field object for `name`, or None if the symbol has no such field."""
    attr = BUILTIN_FIELDS.get(name.lower())
    if attr:
        return getattr(sym, attr)
    for f in sym.user_fields:
        if f.name == name:
            return f
    return None


def _set_field(sym, name: str, value: str) -> None:
    f = _get_field(sym, name)
    if f is not None:
        f.text.value = value  # fields are proto references: the symbol sees the change
        return
    from kipy.schematic_types import SchematicField  # new user field

    nf = SchematicField()
    nf.name = name
    nf.text.value = value
    sym.user_fields = [*sym.user_fields, nf]


def set_fields(kicad, rows: Sequence[tuple[str, str, str]], *, dry_run: bool = False,
               open_sch: Callable = _open_sch, message: str = "kicad_ipc set-fields") -> list[str]:
    """Set fields in the open schematic in one commit.  Returns the diff lines per ref."""
    check_version(kicad)
    require_schematic_api(kicad)
    s = open_sch(kicad)
    by_ref = {_ref(sym): sym for sym in s.get_symbols()}
    missing = sorted({r for r, _, _ in rows if r not in by_ref})
    if missing:
        raise IpcError(f"no such symbol in the open schematic: {', '.join(missing)}")

    diff: list[str] = []
    changed = []
    for ref in dict.fromkeys(r for r, _, _ in rows):
        sym = by_ref[ref]
        for r, name, value in rows:
            if r != ref:
                continue
            f = _get_field(sym, name)
            old = f.text.value if f is not None else None
            diff.append(f"{ref}.{name}: {old!r} -> {value!r}")
            if not dry_run:
                _set_field(sym, name, value)
        changed.append(sym)
    if dry_run:
        return diff
    commit = s.begin_commit()
    try:
        s.update_items(changed)
    except Exception:
        s.drop_commit(commit)
        raise
    s.push_commit(commit, message)
    return diff


# ----------------------------------------------------------------------- CLI

def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status", help="print ipc, closed or other")
    p.add_argument("project", nargs="?", default=None,
                   help="a .kicad_pro file (default: the kicad/ project)")
    p.add_argument("--project", dest="project_dir", metavar="DIR", default=None,
                   help="project directory, e.g. kicad-1rx (default kicad): is KiCad "
                        "showing that project")
    p = sub.add_parser("show", help="select refs and nets in the editors")
    p.add_argument("--refs", nargs="*", default=[])
    p.add_argument("--nets", nargs="*", default=[])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--sch", action="store_true", help="schematic only")
    g.add_argument("--pcb", action="store_true", help="board only")
    p = sub.add_parser("set-fields", help="set symbol fields from CSV (ref,field,value)")
    p.add_argument("csv")
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "status":
        try:
            print(status(project_file(a.project_dir, a.project)))
        except IpcError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0
    try:
        kicad = connect()
        if a.cmd == "show":
            # Below KiCad 11 there is no schematic API: default to the board only, and let an
            # explicit --sch fail with a clear error instead of after a partial selection.
            major = _vtuple(kicad.get_version())[0]
            want_sch = not a.pcb and (a.sch or major >= 11)
            if not a.pcb and not a.sch and major < 11:
                print(f"note: schematic selection skipped (no schematic API before KiCad 11; "
                      f"this is KiCad {major})")
            res = show(kicad, a.refs, a.nets, sch=want_sch, pcb=not a.sch)
            for editor, found in res.items():
                for key, ids in found.items():
                    print(f"{editor} {key}: {len(ids)} item(s)")
        else:
            for line in set_fields(kicad, read_csv(a.csv), dry_run=a.dry_run):
                print(line)
            if a.dry_run:
                print("dry run: nothing changed")
            else:
                print("committed; save in KiCad (Ctrl+S) to keep it, Ctrl+Z to undo")
    except IpcError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # API errors, socket timeouts
        print(f"error: KiCad API call failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
