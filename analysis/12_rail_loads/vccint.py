"""par-11 step 3: the 1V0 FPGA core current (VCCINT + VCCBRAM of U30, XC7A100T-1FTG256C).

There is no single datasheet number: static current (DS181 Table 5) plus dynamic current that depends on
the design. The estimate starts from the routed Vivado power report committed in the firmware repo
`davidmhunt/fmcw3-ckflight-fw` (read only), FMCW3.runs/impl_1/top_module_power_routed.rpt, for the same
device (xc7a100tftg256-1). A copy is kept in sim/fw_power_routed.rpt so the figures regenerate offline;
`--fetch` refreshes it from the repo (gh api) and records the commit.

Typical (what the board draws running the current design, as Vivado estimates it):
  VCCINT total + VCCBRAM total of section 1.2 of the report (junction 26.3 C, ambient 25 C).
Worst case (bounded; assumptions in WORST_ASSUMES, printed with the numbers):
  static   DS181 Table 5, ICCINTQ 155 mA + ICCBRAMQ 4 mA. The sheet gives these "typical ... at 85 C Tj",
           blank device (note 1, 2), the highest static figure it states; Vivado's own static term is 17 mA
           at 26 C, so this covers a hot junction by a factor of about 9.
  dynamic  the report's VCCINT dynamic current times K_TOGGLE = 4. The report was made with no simulation
           activity file (Setting File and SAIF are "---"), internal-node activity at Vivado's "Medium"
           confidence, so the toggle rates behind its 79 mA are not stated. K_TOGGLE = 4 is a 50 % average
           toggle rate (random data on every net), four times Vivado's usual 12.5 % vectorless default (that default is
           from memory of the tool, not stated in the report), and it scales the
           clock-tree power as well, which does not depend on data, so it is on the high side.
  clocks   as constrained in the report: 40 MHz, 100 MHz (MMCM outputs), 60 MHz (USB), no faster.
  design   the current design (12 % of LUTs, 35 of 135 block RAMs, 15 DSPs, 1 MMCM, ILA and debug hub
           included). Growth of the design is not in the bound.
Power-on current (DS181 Table 6, ICCINTMIN = ICCINTQ + 170 mA, ICCBRAMMIN = ICCBRAMQ + 60 mA) is a
requirement on the supply during configuration, stated apart: it is not a running load.

The Vivado power report of the final design replaces this estimate (confidence "Low" in the committed one).

Run: ./run python3 analysis/12_rail_loads/vccint.py [--check] [--show] [--fetch]   (writes sim/vccint.json)
"""
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RPT = HERE / "sim" / "fw_power_routed.rpt"
OUT = HERE / "sim" / "vccint.json"

REPO = "davidmhunt/fmcw3-ckflight-fw"
RPT_PATH = "FMCW3.runs/impl_1/top_module_power_routed.rpt"
UTIL_PATH = "FMCW3.runs/impl_1/top_module_utilization_placed.rpt"
FW_COMMIT = "1b354b58e57edc47f4b8c0ef2fc1b0c727c780cc"   # last commit that touched the power report (2026-08-04)

# DS181 v1.27.1 (manifest id amd-ds181-artix7-datasheet), XC7A100T, -1 speed grade, 1.0 V; mA
ICCINTQ, ICCBRAMQ = 155, 4            # Table 5, PDF pages 5 and 7
ICCINT_ON, ICCBRAM_ON = 170, 60       # Table 6, PDF page 8: added to ICCINTQ / ICCBRAMQ at power-on
K_TOGGLE = 4.0

SRC_DS181 = [
    ("amd-ds181-artix7-datasheet", 5, "Table 5 ICCINTQ 155 mA, XC7A100T -1, 1.0 V (typical at 85 C Tj, blank device)"),
    ("amd-ds181-artix7-datasheet", 7, "Table 5 ICCBRAMQ 4 mA, XC7A100T -1, and notes 1-3 (85 C Tj; use XPE for other conditions)"),
    ("amd-ds181-artix7-datasheet", 8, "Table 6 power-on: ICCINTMIN = ICCINTQ + 170, ICCBRAMMIN = ICCBRAMQ + 60 (XC7A100T)"),
]

WORST_ASSUMES = [
    "static: DS181 ICCINTQ 155 mA + ICCBRAMQ 4 mA (85 C Tj figures, the highest static the sheet states)",
    "dynamic: the report's VCCINT dynamic 79 mA x 4 (a 50 % average toggle rate on every net; the report's "
    "activity is not recorded: no SAIF, 'Medium' internal-node confidence)",
    "clocks as constrained in the report (40, 100 and 60 MHz); the current design's resource use; no design growth",
]


def parse(text):
    """Pull the figures the estimate uses out of the report text."""
    def rail(name):
        m = re.search(rf"\|\s*{name}\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", text)
        assert m, f"{name} row not found in the power report"
        v, tot, dyn, sta = (float(x) for x in m.groups())
        return dict(v=v, total_mA=round(tot * 1e3), dynamic_mA=round(dyn * 1e3), static_mA=round(sta * 1e3))

    def field(label):
        m = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([^|]+?)\s*\|", text)
        assert m, f"{label} not found in the power report"
        return m.group(1)

    return dict(
        device=re.search(r"\| Device\s*:\s*(\S+)", text).group(1),
        design_state=re.search(r"\| Design State\s*:\s*(\S+)", text).group(1),
        date=re.search(r"\| Date\s*:\s*(.+?)\s*\n", text).group(1),
        tool=re.search(r"\| Tool Version\s*:\s*(.+?)\s*\n", text).group(1),
        vccint=rail("Vccint"), vccbram=rail("Vccbram"), vccaux=rail("Vccaux"),
        tj_c=float(field("Junction Temperature (C)")), total_w=float(field("Total On-Chip Power (W)")),
        confidence=field("Confidence Level"), simulation_activity=field("Simulation Activity File"),
        clocks_ns={m.group(1): float(m.group(2)) for m in
                   re.finditer(r"\|\s*(clk_out\d_clk_wiz_0|sysclk|usb_clk)\s*\|[^|]*\|\s*([\d.]+)\s*\|", text)},
    )


def estimate(p):
    vi, vb = p["vccint"], p["vccbram"]
    typ = vi["total_mA"] + vb["total_mA"]
    dyn_worst = round(vi["dynamic_mA"] * K_TOGGLE)
    static_worst = ICCINTQ + ICCBRAMQ
    return dict(
        typ_mA=typ,
        typ_how=f"Vivado routed power report: Vccint {vi['total_mA']} mA ({vi['dynamic_mA']} dynamic + "
                f"{vi['static_mA']} static) + Vccbram {vb['total_mA']} mA, junction {p['tj_c']} C",
        max_mA=static_worst + dyn_worst,
        max_parts=dict(static_ds181_mA=static_worst, dynamic_scaled_mA=dyn_worst, k_toggle=K_TOGGLE,
                       dynamic_report_mA=vi["dynamic_mA"]),
        power_on_min_mA=(ICCINTQ + ICCINT_ON) + (ICCBRAMQ + ICCBRAM_ON),
    )


def build():
    p = parse(RPT.read_text())
    e = estimate(p)
    return {
        "source": "analysis/12_rail_loads/vccint.py; report copy sim/fw_power_routed.rpt; mA",
        "firmware_repo": REPO, "firmware_commit": FW_COMMIT, "report_path": RPT_PATH,
        "utilization_path": UTIL_PATH,
        "design": dict(device=p["device"], state=p["design_state"], vivado=p["tool"], date=p["date"],
                       luts_logic=6767, luts_total=7831, flip_flops=9932, block_ram_tiles=35, dsps=15, mmcm=1,
                       io=43, note="utilization from top_module_utilization_placed.rpt and the power report 1.1"),
        "report": p, "estimate": e,
        "ds181": [list(s) for s in SRC_DS181], "worst_assumes": WORST_ASSUMES,
        "replaced_by": "the Vivado power report of the final design (the committed one has confidence "
                       f"{p['confidence']})",
    }


def check(d):
    p, e = d["report"], d["estimate"]
    assert p["device"] == "xc7a100tftg256-1" and p["design_state"] == "routed"
    assert e["typ_mA"] == p["vccint"]["total_mA"] + p["vccbram"]["total_mA"] == 96
    assert p["vccint"]["total_mA"] == p["vccint"]["dynamic_mA"] + p["vccint"]["static_mA"] or \
        abs(p["vccint"]["total_mA"] - p["vccint"]["dynamic_mA"] - p["vccint"]["static_mA"]) <= 1
    assert e["max_mA"] == ICCINTQ + ICCBRAMQ + round(p["vccint"]["dynamic_mA"] * K_TOGGLE) == 475
    assert e["typ_mA"] < e["max_mA"] < 2000          # far below the 1.55 A pass mark (step 4)
    assert e["power_on_min_mA"] == 389
    assert p["vccint"]["v"] == 1.0 and p["vccbram"]["v"] == 1.0   # both on the 1V0 rail
    return True


def show(d):
    p, e = d["report"], d["estimate"]
    print(f"VCCINT+VCCBRAM (1V0 rail, U30)  typ {e['typ_mA']} mA   max {e['max_mA']} mA   "
          f"power-on requirement {e['power_on_min_mA']} mA")
    print("  typ:", e["typ_how"])
    for a in d["worst_assumes"]:
        print("  max:", a)
    print(f"  report confidence {p['confidence']}; replaced by the Vivado report of the final design")
    print(f"  also in the report: Vccaux {p['vccaux']['total_mA']} mA ({p['vccaux']['dynamic_mA']} dynamic), "
          "against 36 typ / 76 max mA in currents.py")


def fetch():
    r = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                        f"repos/{REPO}/contents/{RPT_PATH}"], capture_output=True, text=True, check=True)
    RPT.write_text(r.stdout)
    c = subprocess.run(["gh", "api", f"repos/{REPO}/commits?path={RPT_PATH}&per_page=1", "--jq", ".[0].sha"],
                       capture_output=True, text=True, check=True).stdout.strip()
    print("fetched", RPT_PATH, "last commit", c, "(FW_COMMIT in this file:", FW_COMMIT + ")")


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    d = build()
    OUT.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    if "--show" in sys.argv:
        show(d)
    if "--check" in sys.argv:
        check(d)
        print("vccint: check ok")
