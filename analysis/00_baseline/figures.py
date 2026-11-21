"""Figures and tables for the baseline report: ERC/DRC counts by type from checks/baseline.json.

Run by tools/build_report.py with this folder as the working directory. Writes into build/.
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import targets as tg  # noqa: E402

# type -> (meaning, goal that handles it). Goals: layout-review (lay-01 triage), parts, sim-spurs.
INFO = {
    "erc:power_pin_not_driven": ("GND power pin has no driver", "layout-review"),
    "erc:lib_symbol_issues": ("Symbol library missing", "layout-review"),
    "erc:lib_symbol_mismatch": ("Symbol differs from library", "layout-review"),
    "erc:footprint_link_issues": ("Footprint not resolved", "layout-review"),
    "erc:endpoint_off_grid": ("Wire end off grid", "layout-review"),
    "erc:pin_to_pin": ("Forbidden pin pair (U40)", "layout-review"),
    "drc:clearance": ("Copper too close (coupler Z1)", "layout-review"),
    "drc:solder_mask_bridge": ("Mask web too thin", "layout-review"),
    "drc:lib_footprint_issues": ("Footprint differs from library", "layout-review"),
    "drc:isolated_copper": ("Copper island, no net", "layout-review"),
    "drc:nonmirrored_text_on_back_layer": ("Back text not mirrored", "layout-review"),
}


def main() -> None:
    ts = tg.load(__import__("os").environ.get("FMCW_TARGETS", "default"))
    print(f"figures.py: {tg.describe(ts)} (baseline counts do not depend on targets)")
    data = json.loads((REPO / "checks" / "baseline.json").read_text())
    build = HERE / "build"
    build.mkdir(exist_ok=True)

    rows = []
    for check in ("erc", "drc"):
        for key, n in sorted(data[check]["by_type"].items(), key=lambda kv: -kv[1]):
            sev, typ = key.split(":", 1)
            meaning, goal = INFO[f"{check}:{typ}"]
            rows.append((check.upper(), typ, sev, n, meaning, goal))

    for check in ("ERC", "DRC"):
        with open(build / f"{check.lower()}_types.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Type", "Count", "Meaning", "Handled by"])
            for c, typ, sev, n, meaning, goal in rows:
                if c == check:
                    w.writerow([typ, f"{n} ({sev})", meaning, goal])

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, check in zip(axes, ("ERC", "DRC")):
        sel = [r for r in rows if r[0] == check][::-1]
        colors = ["#c0392b" if r[2] == "error" else "#1f2a44" for r in sel]
        ax.barh([r[1] for r in sel], [r[3] for r in sel], color=colors)
        ax.set_xscale("log")
        ax.set_xlim(0.7, 2000)
        for i, r in enumerate(sel):
            ax.text(r[3] * 1.12, i, str(r[3]), va="center", fontsize=10)
        ax.set_title(f"{check}: {sum(r[3] for r in sel)} items")
        ax.set_xlabel("count (log scale)")
        ax.tick_params(axis="y", labelsize=9)
    fig.suptitle("Violations by type as inherited (red = error, blue = warning)")
    fig.tight_layout()
    fig.savefig(build / "counts_by_type.png", dpi=150)
    plt.close(fig)

    with open(build / "summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Check", "Errors", "Warnings", "Other"])
        for check in ("erc", "drc"):
            d = data[check]
            tot = sum(d["by_type"].values())
            other = (f"unconnected {d['unconnected_items']}, parity {d['schematic_parity']}"
                     if check == "drc" else "-")
            w.writerow([check.upper(), d["errors"], tot - d["errors"], other])

    meta = {"lib_symbol_issues", "footprint_link_issues", "endpoint_off_grid",
            "lib_symbol_mismatch", "lib_footprint_issues"}
    total = sum(r[3] for r in rows)
    bulk = sum(r[3] for r in rows if r[1] in meta)
    count = {r[1]: r[3] for r in rows}
    facts = {
        "total_items": total,
        "metadata_items": bulk,
        "errors_total": sum(data[c]["errors"] for c in ("erc", "drc")),
        "isolated_copper": count["isolated_copper"],
        "pin_to_pin": count["pin_to_pin"],
    }
    (build / "facts.json").write_text(json.dumps(facts, indent=1) + "\n")

    with open(build / "folder_map.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Folder", "Content"])
        w.writerows([
            ["`kicad/`", "KiCad 10 project, root sheet `fmcw3.kicad_sch`"],
            ["`production/`", "As-ordered XC7A35T fab package, never regenerated"],
            ["`checks/`", "ERC/DRC gate, baseline and recorded reports"],
            ["`analysis/`, `reports/`, `tools/`", "Report sources, built PDF and decks, pipeline"],
            ["`parts/`, `datasheets/`, `docs/`, `legacy/`, `docker/`, `runs/`",
             "BOM, manifests, plans, old exports"],
        ])

    with open(build / "roadmap.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Goal", "Covers", "Review-plan phase"])
        w.writerows([
            ["foundation", "Repo layout, environment, report pipeline, tools", "setup"],
            ["parts", "BOM, DigiKey and JLCPCB checks, datasheets", "1"],
            ["rf-review", "RF level plan, 50 ohm impedance", "2, 3"],
            ["layout-review", "ERC/DRC triage, layout checks, bring-up", "4, 5"],
            ["sim-spurs", "Supply noise, IF filter, PLL, frequency plan", "6, 7"],
        ])


if __name__ == "__main__":
    main()
