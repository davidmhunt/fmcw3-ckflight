"""rx1-02: the decoupling that sits on the U8 supply nets today (kicad/ netlist, kicad_pcb positions).

The LTC2292 VDD pins (7, 10, 18, 63) are on /fpga/adc/3V0 and OVDD (32, 49) on /3V3D. The AD9237
takes AVDD (27, 32) from the first and DRVDD (16) from the second, so the existing caps carry over
(adi-ad9237-datasheet p.8 Table 6: 0.1 uF minimum, 0.1 uF with 10 uF recommended per group).

Run: ./run --native python3 analysis/11_board_1rx/supply_decoupling.py
Read only: nothing is written under kicad/.
"""
import collections
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rx2_dnp  # noqa: E402

ROOT = HERE.parents[1]


def positions(pcb):
    t = pcb.read_text()
    pos = {}
    for m in re.finditer(r'\(footprint "[^"]*"', t):
        seg = t[m.start():m.start() + 4000]
        a = re.search(r'\(at ([-\d.]+) ([-\d.]+)', seg)
        r = re.search(r'\(property "Reference" "([^"]+)"', seg)
        if a and r:
            pos[r.group(1)] = (float(a.group(1)), float(a.group(2)))
    return pos


def main():
    comps, nets = rx2_dnp.netlist(ROOT / "kicad" / "fmcw3.kicad_sch")
    pos = positions(ROOT / "kicad" / "fmcw3.kicad_pcb")
    byref = collections.defaultdict(dict)
    for n, nodes in nets.items():
        for r, p in nodes:
            byref[r][p] = n
    for group, pins in (("AVDD", ("7", "10", "18", "63")), ("DRVDD", ("32", "49"))):
        net = byref["U8"][pins[0]]
        caps = sorted((math.dist(pos[r], pos["U8"]), r, comps[r]["value"]) for r, _ in nets[net]
                      if re.match(r"C\d", r))
        print(f"{group} ({net}): {len(caps)} caps; mm from U8, ref, value")
        for d, r, v in caps:
            print(f"  {d:5.1f}  {r:5s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
