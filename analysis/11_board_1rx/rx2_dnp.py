"""rx1-02 step 4: which parts exist only for receive chain 2 (RX2).

Reads the kicad/ netlist (kicad-cli sch export netlist, headless, nothing is written under
kicad/), walks the signal path from each antenna port through the parts that pass the signal
(passives, the baluns, the LNA and gain-block pairs, the ADL5802 channel pairs, the LT6232 amps)
and compares the two walks.

  RX1 (kept)    : P1 -> U11 -> U9 -> U27 -> U29 RF2 -> IF2 -> U45 amps A/B -> U8 AINA
  RX2 (removed) : P2 -> U16 -> U13 -> U28 -> U29 RF1 -> IF1 -> U45 amps C/D -> U8 AINB

Channel pairing inside the ADL5802 is from adi-adl5802-datasheet p.6 Table 3 (RF1 pins 22/23 go
with OP1 pins 3/4; RF2 pins 19/20 go with OP2 pins 15/16). The walk crosses U29 and U45 only along
those pairs, so a part reached by both walks is a shared part.

Run: ./run python3 analysis/11_board_1rx/rx2_dnp.py   (writes sim/rx2_dnp.json)
"""
import collections
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "sim" / "rx2_dnp.json"

# Signal passes through these ICs only between the listed pins (ref -> list of pin groups).
THRU = {
    "U9": [{"2", "7"}], "U13": [{"2", "7"}],  # TRF37A73 gain blocks
    "U11": [{"3", "4"}], "U16": [{"3", "4"}],  # SKY65404 LNAs
    "U27": [{"1", "3", "4"}], "U28": [{"1", "3", "4"}],  # RF baluns
    "U29": [{"19", "20", "15", "16"}, {"22", "23", "3", "4"}],  # ADL5802 ch2, ch1
    "U45": [{"2", "1"}, {"6", "7"}, {"11", "10"}, {"15", "16"}],  # LT6232 inverting pairs
}
BIG = 14  # a net with more nodes than this is a rail or ground, never a signal path


def netlist(kicad_sch):
    out = pathlib.Path(tempfile.mkdtemp()) / "n.net"
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", str(out), str(kicad_sch)], check=True, capture_output=True)
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', out.read_text())
    pos = 0

    def rd():
        nonlocal pos
        tk = toks[pos]
        pos += 1
        if tk == "(":
            lst = []
            while toks[pos] != ")":
                lst.append(rd())
            pos += 1
            return lst
        return tk.strip('"')

    tree = rd()
    sub = lambda n, k: [x for x in n if isinstance(x, list) and x and x[0] == k]
    comps = {}
    for c in sub(sub(tree, "components")[0], "comp"):
        d = {x[0]: x[1:] for x in c if isinstance(x, list)}
        comps[d["ref"][0]] = dict(value=d.get("value", [""])[0],
                                  fp=d.get("footprint", [""])[0].split(":")[-1],
                                  sheet=d["sheetpath"][0][1] if "sheetpath" in d else "")
    nets = {}
    for n in sub(sub(tree, "nets")[0], "net"):
        name = [x for x in n if isinstance(x, list) and x[0] == "name"][0][1]
        nets[name] = [(x[1][1], x[2][1]) for x in n if isinstance(x, list) and x[0] == "node"]
    shutil.rmtree(out.parent)
    return comps, nets


def passive(ref, comps):
    return (re.match(r"(C|R|L|FB|JP|F)\d", ref) is not None
            or comps[ref]["value"].startswith("SolderPad"))


def walk(start, comps, nets, byref):
    seen, parts, q = set(), [], [start]
    while q:
        n = q.pop()
        if n in seen or n == "GND" or len(nets[n]) > BIG or re.search(r"/3V|VCC|5V|VCM", n):
            continue
        seen.add(n)
        for ref, pin in nets[n]:
            if ref in THRU:
                if ref not in parts:
                    parts.append(ref)
                for g in THRU[ref]:
                    if pin in g:
                        q.extend(byref[ref][p] for p in g)
            elif passive(ref, comps):
                if ref not in parts:
                    parts.append(ref)
                q.extend(byref[ref].values())
            elif ref in ("P1", "P2"):
                parts.append(ref) if ref not in parts else None
            elif ref == "U8":
                if ref not in parts:
                    parts.append(ref)
    return parts, seen


def analyse(kicad_sch=ROOT / "kicad" / "fmcw3.kicad_sch"):
    comps, nets = netlist(kicad_sch)
    byref = collections.defaultdict(dict)
    for n, nodes in nets.items():
        for r, p in nodes:
            byref[r][p] = n
    def supply(ics):
        """Bias and decoupling parts on the supply and enable nets of the RF ICs (not rails)."""
        got, q, seen = [], [n for ic in ics for n in byref[ic].values()], set()
        while q:
            n = q.pop()
            if n in seen or n == "GND" or len(nets[n]) > BIG or re.search(r"/3V|/5V", n):
                continue
            seen.add(n)
            for ref, _ in nets[n]:
                if passive(ref, comps) and ref not in got:
                    got.append(ref)
                    q.extend(byref[ref].values())
        return got

    rx1, _ = walk("Net-(U11-RF_IN)", comps, nets, byref)
    rx2, _ = walk("Net-(U16-RF_IN)", comps, nets, byref)
    rx1 += [r for r in supply(["U9", "U11"]) if r not in rx1]
    rx2 += [r for r in supply(["U13", "U16"]) if r not in rx2]
    only2 = sorted(set(rx2) - set(rx1))
    only1 = sorted(set(rx1) - set(rx2))
    shared = sorted(set(rx1) & set(rx2))

    # Which U8 input pair does each chain end on.
    ends = {}
    for name, start in (("RX1", "Net-(U11-RF_IN)"), ("RX2", "Net-(U16-RF_IN)")):
        pins = sorted({byref["U8"][p] for p in ("1", "2", "15", "16")
                       if byref["U8"][p] in walk(start, comps, nets, byref)[1]})
        ends[name] = pins

    # U8 channel B pins that are not on the signal path: reference, SENSEB, and their caps.
    chb_pins = {"REFHB": ("11", "12"), "REFLB": ("13", "14"), "SENSEB": ("19",)}
    chb_parts = sorted({r for pins in chb_pins.values() for p in pins
                        for r, _ in nets[byref["U8"][p]] if r != "U8"})
    # Bias nets: VCMA (U8.61) feeds U45.12/14 (amps C/D, RX2); VCMB (U8.20) feeds U45.3/5 (A/B, RX1).
    vcm = {k: {"net": byref["U8"][p], "parts": sorted(r for r, _ in nets[byref["U8"][p]]
                                                      if r not in ("U8", "U45"))}
           for k, p in (("VCMA_pin61", "61"), ("VCMB_pin20", "20"))}
    vcm["VCMA_pin61"]["u45_pins"] = sorted(p for r, p in nets[byref["U8"]["61"]] if r == "U45")
    vcm["VCMB_pin20"]["u45_pins"] = sorted(p for r, p in nets[byref["U8"]["20"]] if r == "U45")

    # FPGA pins: U8 channel-B control nets.
    chb_ctl = {"23": "ADC_OE2", "22": "ADC_SHDN2", "40": "OFB"}
    freed = {}
    for p, nm in chb_ctl.items():
        n = byref["U8"][p]
        freed[nm] = sorted(pin for r, pin in nets[n] if r == "U30")
    # Every other U30 net on U8 is channel A.
    chA = sorted(byref["U8"][p] for p in byref["U8"]
                 if any(r == "U30" for r, _ in nets[byref["U8"][p]]) and p not in chb_ctl)
    # FPGA nets that touch any RX2-only part: none expected.
    u30_on_rx2 = sorted({r for p in only2 for n in byref[p].values() if n != "GND"
                         for r, _ in nets[n] if r == "U30"})

    # Shared parts that must stay: ADL5802, LO split, LT6232, ADC, mixer supply and VSET.
    lo_split = sorted(r for r, p in nets["/LO"])
    res = dict(
        rx1_parts=rx1, rx2_parts=rx2, only_rx2=only2, only_rx1=only1, shared=shared,
        chain_end_nets=ends, adc_channel_b_parts=chb_parts, vcm=vcm,
        fpga_pins_freed=freed, fpga_nets_adc_channel_a=chA, u30_on_rx2_parts=u30_on_rx2,
        lo_split_parts=lo_split,
        values={r: [comps[r]["value"], comps[r]["fp"]] for r in sorted(set(rx2) | set(chb_parts))},
    )
    return res


def main():
    res = analyse()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print("RX2 only (%d):" % len(res["only_rx2"]), " ".join(res["only_rx2"]))
    print("shared:", " ".join(res["shared"]))
    print("ends:", res["chain_end_nets"])
    print("U8 channel B parts:", " ".join(res["adc_channel_b_parts"]))
    print("FPGA pins freed:", res["fpga_pins_freed"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
