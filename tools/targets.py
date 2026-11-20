#!/usr/bin/env python3
"""Load and validate a named system target set from analysis/targets/NAME.yaml.

usage: targets.py [NAME]   (prints the set, default "default")
API:   load(name) -> {'name', 'description', 'parameters': {key: {value, unit, status, note?}}};
       value(ts, key); describe(ts) -> one-line summary; format_table(ts) -> markdown table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

TARGETS_DIR = Path(__file__).resolve().parent.parent / "analysis" / "targets"
REQUIRED = {
    "max_range_m": "m",
    "range_resolution_m": "m",
    "chirp_bandwidth_hz": "Hz",
    "chirp_duration_s": "s",
    "sample_rate_hz": "Hz",
    "tx_power_dbm": "dBm",
    "antenna_gain_dbi": "dBi",
    "tx_rx_isolation_db": "dB",
    "board_quantity": "boards",
}
STATUSES = ("assumed", "set")
NEGATIVE_OK = {"tx_power_dbm", "antenna_gain_dbi"}


class TargetError(ValueError):
    pass


def validate(data, label: str = "targets") -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return [f"{label}: top level must be a mapping"]
    if not isinstance(data.get("name"), str) or not data["name"]:
        errs.append(f"{label}: missing 'name'")
    params = data.get("parameters")
    if not isinstance(params, dict):
        return errs + [f"{label}: missing 'parameters' mapping"]
    for key, unit in REQUIRED.items():
        p = params.get(key)
        if p is None:
            errs.append(f"{label}: missing parameter {key}")
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
    for key in params:
        if key not in REQUIRED:
            errs.append(f"{label}: unknown parameter {key}")
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
    return data


def value(ts: dict, key: str) -> float:
    return ts["parameters"][key]["value"]


def describe(ts: dict) -> str:
    n = sum(p["status"] == "assumed" for p in ts["parameters"].values())
    return f"target set '{ts['name']}' ({n} of {len(ts['parameters'])} values assumed)"


def format_table(ts: dict) -> str:
    rows = ["| parameter | value | unit | status |", "|---|---|---|---|"]
    for k, p in ts["parameters"].items():
        rows.append(f"| {k} | {p['value']:g} | {p['unit']} | {p['status']} |")
    return "\n".join(rows)


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
