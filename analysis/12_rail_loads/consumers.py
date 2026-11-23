"""par-11 step 1: which parts load each buck output, on the 2-RX board and the 1-RX board.

Reads the kicad/ and kicad-1rx/ netlists (kicad-cli sch export netlist, headless; nothing is
written under either project). Starts at each buck inductor output and follows the supply:

  U17/L5 -> /1V0           -> U30 (VCCINT, VCCBRAM)
  U18/L6 -> /3V8           -> U20 (3V0), U23 (1V8), U24 (3V3A), U25 (3V3D), U39 (ADC 3V0) + direct loads
  U19/L7 -> /power/5V6     -> U22 (5V) + direct loads

An LDO passes its load current plus its ground current back to its input rail, so every part on an
LDO output is also a consumer of the buck rail that feeds the LDO (the "path" field says how). The
walk goes through ferrite beads, 0 ohm links, the RF bias chokes L1 to L4 and the series resistors
R22, R23 and R302; decoupling capacitors are not consumers (their leakage is below 1 uA).

1-RX board: the netlist of kicad-1rx/ is the 2-RX netlist; the 1-RX changes are a list
(parts/rx1_changes.csv). The receive-chain-2 DNP parts (kind dnp, status decided) are marked not
fitted, U8 is the AD9237BCPZ-40 in place of the LTC2292 (rx1-001, rx1-014, rx1-016), and the new
divider R990/R991 (rx1-005, rx1-006) is added to 3V0. The option rows (op-amp B, SMA, LEDs, ...)
do not change a buck rail load that is known today and are listed under "open_1rx".

Run: ./run python3 analysis/12_rail_loads/consumers.py [--check]   (writes sim/consumers.json)
"""
import csv
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "sim" / "consumers.json"

_spec = importlib.util.spec_from_file_location(
    "rx2_dnp", ROOT / "analysis" / "11_board_1rx" / "rx2_dnp.py")
_rx2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rx2)  # netlist() parser only; nothing runs at import

PROJECTS = {"2rx": ROOT / "kicad" / "fmcw3.kicad_sch",
            "1rx": ROOT / "kicad-1rx" / "fmcw3_1rx.kicad_sch"}

# buck regulator -> (inductor, output net, rail name)
BUCKS = {"U17": ("L5", "/1V0", "1V0"), "U18": ("L6", "/3V8", "3V8"),
         "U19": ("L7", "/power/5V6", "5V6")}

# LDO -> (input pins, output pin, ground pin, output net, its supply is the rail on the input net)
LDOS = {
    "U20": (("1", "3"), "5", "2", "/3V0"),
    "U39": (("1", "3"), "5", "2", "/fpga/adc/3V0"),
    "U23": (("6", "7", "8"), None, "4", "/1V8"),   # LD3920: out pins 1, 2
    "U24": (("6", "7", "8"), None, "4", "/3V3A"),
    "U25": (("6",), None, "3", "/3V3D"),           # LD3920_33: out pins 1, 2
    "U22": (("6", "7", "8"), None, "4", "/5V"),
}
LDO_OUT_PINS = {"U20": {"5"}, "U39": {"5"}, "U23": {"1", "2"}, "U24": {"1", "2"},
                "U25": {"1", "2"}, "U22": {"1", "2"}}

# Parts the supply walk goes through (not consumers themselves).
SERIES = re.compile(r"^(FB\d+|L[1-4]|R22|R23|R302)$")

# 1-RX additions on a buck rail: new parts of parts/rx1_changes.csv (kind new) that touch 3V0.
NEW_1RX = [
    dict(ref="R990", value="1.0 kohm 0402", rail_net="/fpga/adc/3V0", role="divider_top",
         other="/ADC_VCMB", note="rx1-005: 3V0 to /ADC_VCMB, with R991 to GND (1.5 V bias)"),
    dict(ref="R991", value="1.0 kohm 0402", rail_net="/ADC_VCMB", role="divider_bottom",
         other="GND", note="rx1-006: /ADC_VCMB to GND; the 3V0 current is 3.0 V / (R990 + R991)"),
]
# U8 on the 1-RX board: the AD9237BCPZ-40 (rx1-001), supply pins from rx1-014 and rx1-016.
U8_1RX = {"value": "AD9237BCPZ-40 (LFCSP-32)",
          "pins": {"/fpga/adc/3V0": ["27", "32"], "/3V3D": ["16"]},
          "source": "rx1-014 (AVDD pins 27, 32), rx1-016 (DRVDD pin 16)"}


def rx1_dnp():
    rows = list(csv.DictReader(open(ROOT / "parts" / "rx1_changes.csv")))
    dnp = sorted({r["refs"] for r in rows if r["kind"] == "dnp" and r["status"] == "decided"})
    open_ = sorted({r["id"] for r in rows if r["status"] in ("option", "proposed")
                    and r["kind"] in ("swap", "fields", "dnp", "net", "value")
                    and re.search(r"U45|U30|LED|U21", r["board_row"])})
    return dnp, open_


def walk_supply(start, nets, byref, comps):
    """Nets reachable from `start` through series parts only; returns (nets, series parts)."""
    seen, parts, q = set(), [], [start]
    while q:
        n = q.pop()
        if n in seen or n == "GND":
            continue
        seen.add(n)
        for ref, _ in nets[n]:
            ser = SERIES.match(ref) or (ref[0] == "R" and comps[ref]["value"] == "0")
            if ser:
                if ref not in parts:
                    parts.append(ref)
                q.extend(byref[ref].values())
    return seen, parts


def refkey(r):
    return (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))


def analyse(board):
    comps, nets = _rx2.netlist(PROJECTS[board])
    byref = {}
    for n, nodes in nets.items():
        for ref, pin in nodes:
            byref.setdefault(ref, {})[pin] = n

    def on_rail(net_start, path, rail):
        """Consumers of the supply group of `net_start`; LDO inputs recurse."""
        group, series = walk_supply(net_start, nets, byref, comps)
        out, ics = [], {}
        for n in sorted(group):
            for ref, pin in nets[n]:
                if ref in series or ref[0] == "C" or ref in ("L5", "L6", "L7"):
                    continue
                if ref in LDOS and pin in LDO_OUT_PINS[ref]:
                    continue
                if ref[0] == "R":
                    if comps[ref]["value"] == "DNP":
                        continue
                    other = [m for p, m in byref[ref].items() if m != n]
                    other = other[0] if other else n
                    o_parts = sorted((f"{r2}={comps[r2]['value']}" for r2, _ in nets[other]
                                      if r2 != ref and r2[0] in "RD" and comps[r2]["value"] != "DNP"),
                                     key=lambda s: refkey(s.split("=")[0]))
                    role = ("divider_top" if re.search(r"-(FB|ADJ)\)$", other) else
                            "led_branch" if re.search(r"\(D\d+-A\)$", other) else
                            "if_output_bias" if other.startswith("/mixer/IF") else
                            "bias_set" if re.search(r"-VSET\)$", other) else
                            "to_gnd" if other == "GND" else "pullup")
                    out.append(dict(ref=ref, value=comps[ref]["value"], role=role, pins=[pin],
                                    rail_net=n, other_net=other, other_parts=o_parts,
                                    path=path + [n]))
                else:
                    d = ics.setdefault(ref, {"pins": [], "straps": [], "nets": set()})
                    # a pin tied high through a 0 ohm link or pull-up is a strap, not a supply pin
                    d["straps" if re.search(r"SENSE|/fpga/M0$", n) else "pins"].append(pin)
                    d["nets"].add(n)
        for ref, d in ics.items():
            if ref in LDOS:
                out.append(dict(ref=ref, value=comps[ref]["value"], role="ldo", pins=sorted(d["pins"]),
                                rail_net=sorted(d["nets"])[0], out_net=LDOS[ref][3],
                                gnd_pin=LDOS[ref][2], path=path + [sorted(d["nets"])[0]]))
            else:
                key = lambda p: (len(p), p)
                out.append(dict(ref=ref, value=comps[ref]["value"],
                                role="connector" if ref[0] == "J" else "ic",
                                pins=sorted(d["pins"], key=key),
                                strap_pins=sorted(d["straps"], key=key),
                                rail_net=sorted(d["nets"])[0], nets=sorted(d["nets"]),
                                sheet=comps[ref]["sheet"], path=path + [sorted(d["nets"])[0]]))
        for c in list(out):
            if c["role"] == "ldo" and "children" not in c:
                c["children"] = on_rail(c["out_net"], path + [c["ref"]], rail)
        for c in out:
            if c["role"] != "ic":
                c.setdefault("sheet", comps[c["ref"]]["sheet"])
        out.sort(key=lambda c: refkey(c["ref"]))
        return out

    rails = {}
    for reg, (ind, net, name) in BUCKS.items():
        assert byref[ind]["2"] == net, (board, ind, byref[ind])
        assert byref[reg]["3"] == "/power/12V" and byref[reg]["2"] == byref[ind]["1"], reg
        rails[name] = dict(regulator=reg, inductor=ind, net=net, consumers=on_rail(net, [name], name))
    # the LDO input nets must be the buck nets
    for ldo, (ins, _, _, out_net) in LDOS.items():
        feeds = {byref[ldo][p] for p in ins}
        assert len(feeds) == 1 and feeds <= {b[1] for b in BUCKS.values()} | {"/3V8"}, (ldo, feeds)
    return rails, comps


def flat(consumers):
    for c in consumers:
        yield c
        yield from flat(c.get("children", []))


def apply_board(board, rails, comps):
    """Mark which consumers are fitted on the board; add the 1-RX substitutions."""
    dnp, open_ = rx1_dnp() if board == "1rx" else ([], [])
    for r in rails.values():
        for c in flat(r["consumers"]):
            c["fitted"] = c["ref"] not in dnp
            if board == "1rx" and c["ref"] == "U8":
                c["value"] = U8_1RX["value"]
                c["pins_ltc2292"] = c["pins"]
                c["pins"] = U8_1RX["pins"][c["rail_net"]]
                c["note"] = "AD9237BCPZ-40 in place of the LTC2292 (" + U8_1RX["source"] + ")"
    if board == "1rx":
        for n in NEW_1RX:
            host = next(c for c in flat(rails["3V8"]["consumers"]) if c["ref"] == "U39")
            host["children"].append(dict(
                ref=n["ref"], value=n["value"], role=n["role"], pins=["1"] if n["ref"] == "R990" else ["2"],
                rail_net=n["rail_net"], other_net=n["other"], path=["3V8", "U39", n["rail_net"]],
                sheet="/fpga/adc/", fitted=True, note=n["note"]))
    return dnp, open_


def summary(rails):
    s = {}
    for name, r in rails.items():
        fl = [c for c in flat(r["consumers"]) if c["fitted"]]
        s[name] = dict(
            ics=sorted({c["ref"] for c in fl if c["role"] in ("ic", "connector")}, key=refkey),
            ldos=sorted({c["ref"] for c in fl if c["role"] == "ldo"}, key=refkey),
            resistors=sorted({c["ref"] for c in fl if c["role"] not in ("ic", "connector", "ldo")}, key=refkey),
            not_fitted=sorted({c["ref"] for c in flat(r["consumers"]) if not c["fitted"]}, key=refkey))
    return s


def build():
    data = {"source": "kicad-cli sch export netlist of kicad/ and kicad-1rx/; parts/rx1_changes.csv",
            "boards": {}}
    for board in ("2rx", "1rx"):
        rails, comps = analyse(board)
        dnp, open_ = apply_board(board, rails, comps)
        data["boards"][board] = dict(rails=rails, summary=summary(rails),
                                     dnp_applied=dnp, open_rows=open_)
    return data


def check(data):
    b2, b1 = data["boards"]["2rx"], data["boards"]["1rx"]
    # 1V0: the FPGA core only (plus the buck's own feedback resistor).
    assert b2["summary"]["1V0"]["ics"] == ["U30"], b2["summary"]["1V0"]
    assert b2["summary"]["1V0"]["ldos"] == []
    # 3V8: the five LDOs of the brief, and every one reaches its loads.
    assert b2["summary"]["3V8"]["ldos"] == ["U20", "U23", "U24", "U25", "U39"], b2["summary"]["3V8"]
    assert b2["summary"]["5V6"]["ldos"] == ["U22"]
    want_ics = {"3V8": {"U1", "U6", "U8", "U9", "U10", "U11", "U13", "U16", "U30", "U32", "U33",
                        "U40", "U45", "Y2", "J2"},
                "5V6": {"U1", "U14", "U29"}}
    for rail, want in want_ics.items():
        assert set(b2["summary"][rail]["ics"]) == want, (rail, set(b2["summary"][rail]["ics"]) ^ want)
    # 1-RX: the RX2 front end is gone from 3V0, everything else stays.
    gone = set(b1["summary"]["3V8"]["not_fitted"])
    assert {"U13", "U16"} <= gone, gone
    assert {"FB7", "FB8", "R23", "L3", "L4"} <= set(b1["dnp_applied"]), b1["dnp_applied"]
    assert not b2["dnp_applied"]
    assert not (set(b1["summary"]["3V8"]["ics"]) & {"U13", "U16"})
    assert set(b1["summary"]["3V8"]["ics"]) == want_ics["3V8"] - {"U13", "U16"}
    assert b1["summary"]["5V6"]["ics"] == b2["summary"]["5V6"]["ics"]
    assert b1["summary"]["1V0"]["ics"] == ["U30"]
    u8 = next(c for c in flat(b1["rails"]["3V8"]["consumers"]) if c["ref"] == "U8")
    u8s = [c for c in flat(b1["rails"]["3V8"]["consumers"]) if c["ref"] == "U8"]
    assert {tuple(c["pins"]) for c in u8s} == {("27", "32"), ("16",)}, u8s
    assert u8["value"].startswith("AD9237")
    assert {"R990", "R991"} <= {c["ref"] for c in flat(b1["rails"]["3V8"]["consumers"])}
    # every consumer path starts at its buck rail name
    for bd in (b2, b1):
        for name, r in bd["rails"].items():
            assert all(c["path"][0] == name for c in flat(r["consumers"]))
    return True


def show(data):
    for board, bd in data["boards"].items():
        print(f"== {board}  (not fitted on this board: {bd['dnp_applied'] or 'none'})")
        for name, r in bd["rails"].items():
            print(f"  {name} ({r['regulator']}/{r['inductor']}, {r['net']})")

            def rec(cs, ind):
                for c in cs:
                    nf = "" if c["fitted"] else "  [NOT FITTED]"
                    print(f"{ind}{c['ref']:6} {c['value'][:28]:28} {c['role']:12} pins {','.join(c['pins'])[:40]}"
                          f"  on {c['rail_net']}{nf}")
                    rec(c.get("children", []), ind + "    ")
            rec(r["consumers"], "    ")


if __name__ == "__main__":
    d = build()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    if "--show" in sys.argv:
        show(d)
    if "--check" in sys.argv:
        check(d)
        print("consumers: check ok")
