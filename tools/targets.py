#!/usr/bin/env python3
"""Load and validate a named system target set from analysis/targets/NAME.yaml.

A set has two groups: `design` (required, printed first everywhere) and `performance`
(optional extras, printed after). Range resolution is derived from the chirp bandwidth
(c / 2B), never set.

usage: targets.py [NAME]   (prints the set, default "default")
API:   load(name) -> {'name', 'description', 'design': {...}, 'performance': {...}};
       params(ts) -> design then performance as one ordered dict; value(ts, key);
       range_resolution_m(ts); describe(ts) -> one-line summary;
       rows(ts) -> [[group, parameter, value, unit, status], ...] (header first);
       format_table(ts) -> markdown table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

TARGETS_DIR = Path(__file__).resolve().parent.parent / "analysis" / "targets"
C_M_S = 299792458.0

# key -> unit, per group
DESIGN = {
    "freq_min_ghz": "GHz",
    "freq_max_ghz": "GHz",
    "chirp_bandwidth_hz": "Hz",
    "sample_rate_hz": "Hz",
    "tx_power_dbm": "dBm",
    "tx_rx_isolation_db": "dB",
    "board_quantity": "boards",
}
PERFORMANCE = {
    "max_range_m": "m",
    "chirp_duration_s": "s",
    "antenna_gain_dbi": "dBi",
}
GROUPS = {"design": DESIGN, "performance": PERFORMANCE}
STATUSES = ("assumed", "set")
NEGATIVE_OK = {"tx_power_dbm", "antenna_gain_dbi"}


class TargetError(ValueError):
    pass


def _check_group(group: str, spec: dict, section, required: bool, label: str) -> list[str]:
    errs: list[str] = []
    if section is None:
        return [f"{label}: missing '{group}' group"] if required else []
    if not isinstance(section, dict):
        return [f"{label}: '{group}' must be a mapping"]
    for key, unit in spec.items():
        p = section.get(key)
        if p is None:
            if required:
                errs.append(f"{label}: missing parameter {key} in {group}")
            continue
        if not isinstance(p, dict):
            errs.append(f"{label}: {key} must be a mapping")
            continue
        v = p.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            errs.append(f"{label}: {key}.value must be a number, got {v!r}")
        elif v <= 0 and key not in NEGATIVE_OK:
            errs.append(f"{label}: {key}.value must be positive, got {v}")
        if p.get("unit") != unit:
            errs.append(f"{label}: {key}.unit must be {unit!r}, got {p.get('unit')!r}")
        if p.get("status") not in STATUSES:
            errs.append(f"{label}: {key}.status must be one of {STATUSES}, got {p.get('status')!r}")
    for key in section:
        if key not in spec:
            errs.append(f"{label}: unknown parameter {key} in {group}")
    return errs


def validate(data, label: str = "targets") -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return [f"{label}: top level must be a mapping"]
    if not isinstance(data.get("name"), str) or not data["name"]:
        errs.append(f"{label}: missing 'name'")
    for key in data:
        if key not in ("name", "description", *GROUPS):
            errs.append(f"{label}: unknown top-level key {key}")
    errs += _check_group("design", DESIGN, data.get("design"), True, label)
    errs += _check_group("performance", PERFORMANCE, data.get("performance"), False, label)
    if errs:
        return errs
    d = data["design"]
    fmin, fmax = d["freq_min_ghz"]["value"], d["freq_max_ghz"]["value"]
    if fmin >= fmax:
        errs.append(f"{label}: freq_min_ghz ({fmin}) must be below freq_max_ghz ({fmax})")
    else:
        span_hz = (fmax - fmin) * 1e9
        bw = d["chirp_bandwidth_hz"]["value"]
        # GHz edges are inexact in binary floating point; allow 1 Hz of slack so a
        # bandwidth equal to the band is accepted.
        if bw > span_hz + 1.0:
            errs.append(f"{label}: chirp_bandwidth_hz ({bw:g}) exceeds freq_max_ghz - freq_min_ghz "
                        f"({span_hz:g} Hz)")
    return errs


def load(name: str = "default") -> dict:
    """Return the validated target set."""
    if not name or "/" in name or name.startswith("."):
        raise TargetError(f"bad target set name {name!r}")
    path = TARGETS_DIR / f"{name}.yaml"
    if not path.is_file():
        avail = ", ".join(sorted(p.stem for p in TARGETS_DIR.glob("*.yaml"))) or "none"
        raise TargetError(f"target set {name!r} not found (available: {avail})")
    data = yaml.safe_load(path.read_text())
    errs = validate(data, path.name)
    if errs:
        raise TargetError("; ".join(errs))
    data.setdefault("performance", {})
    return data


def params(ts: dict) -> dict:
    """Design parameters first, then performance, as one ordered mapping."""
    return {**ts["design"], **ts.get("performance", {})}


def value(ts: dict, key: str) -> float:
    return params(ts)[key]["value"]


def range_resolution_m(ts: dict) -> float:
    """Derived range resolution c / (2 B) in metres."""
    return C_M_S / (2 * value(ts, "chirp_bandwidth_hz"))


def describe(ts: dict) -> str:
    p = params(ts)
    n = sum(v["status"] == "assumed" for v in p.values())
    return f"target set '{ts['name']}' ({n} of {len(p)} values assumed)"


def _fmt(v: float) -> str:
    return f"{v:,.10g}"


def rows(ts: dict, groups: tuple[str, ...] = ("design", "performance", "derived")) -> list[list[str]]:
    """Header plus one row per target: design first, performance next, derived last.

    `groups` selects which of design, performance and derived to include."""
    out = [["Group", "Parameter", "Value", "Unit", "Status"]]
    for group in ("design", "performance"):
        if group in groups:
            for k, p in ts.get(group, {}).items():
                out.append([group, k, _fmt(p["value"]), p["unit"], p["status"]])
    if "derived" in groups:
        out.append(["derived", "range_resolution_m", _fmt(round(range_resolution_m(ts), 4)), "m",
                    "derived: c / 2B"])
    return out


def format_table(ts: dict) -> str:
    r = rows(ts)
    esc = lambda c: c.replace("|", "\\|")  # noqa: E731
    lines = ["| " + " | ".join(r[0]) + " |", "|" + "---|" * len(r[0])]
    lines += ["| " + " | ".join(esc(c) for c in row) + " |" for row in r[1:]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        ts = load(argv[0] if argv else "default")
    except TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(describe(ts))
    print(format_table(ts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
