"""par-11 step 2: the current each consumer takes from its supply, typical and maximum, with source.

Joins the consumer list of step 1 (sim/consumers.json, from consumers.py) with the table CURRENTS
below. One row per (part, supply path); a row names the datasheets it reads as
(manifest id, PDF page, what is read there). Page numbers are PDF page indices (page 1 is the first
page of the file), as printed by `pdftotext`, which can differ from the page number printed on the sheet.

How a current was reached (the "how" field):
  datasheet  read from a datasheet on file (datasheets/manifest.yaml), typical and maximum
  power/V    the sheet gives power only: power divided by the rail voltage
  computed   Ohm's law on schematic values, or CV f from the datasheet's own formula
  bound      no datasheet number: a stated upper bound and the reason (field "why")
  step3      the 1V0 FPGA core, estimated in step 3 (analysis/12_rail_loads/vccint.py)

Units are mA. "typ" is the expected operating value, "max" the worst case used for the pass marks.
Nominal rail voltages: 1V0 1.0, 3V8 3.8, 5V6 5.6 (LMR51420 feedback dividers, R32/R33, R34/R35,
R36/R37, 0.6 V reference; the 1V0 divider gives 1.008 V), LDO outputs 3.0 (U20, U39), 1.83 (U23),
3.33 (U24), 3.3 (U25), 5.0 (U22) (manifest note of st-ld39200-datasheet, divider values).

Run: ./run python3 analysis/12_rail_loads/currents.py [--check] [--show]   (writes sim/currents.json)
"""
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
CONSUMERS = HERE / "sim" / "consumers.json"
OUT = HERE / "sim" / "currents.json"

V = {"1V0": 1.0, "3V8": 3.8, "5V6": 5.6, "3V0": 3.0, "1V8": 1.83, "3V3A": 3.33, "3V3D": 3.3, "5V": 5.0}

# LED forward voltage bounds over the KENTO 0603 candidates (colour is not chosen: decisions.csv D1..D7
# "for-user"). Red is the lowest, 1.8 V min / 2.4 V max (kento-kt-0603-led-datasheet p3); white, green,
# blue are 2.6-3.1 V (kento-kt-0603w/g/b p3). Typical uses the red mid value, the maximum uses the
# lowest Vf, which is the highest current.
VF_TYP, VF_MIN = 2.1, 1.8
LED_SRC = [("kento-kt-0603-led-datasheet", 3, "red VF 1.8 min, 2.4 max at 20 mA"),
           ("kento-kt-0603w-led-datasheet", 3, "white VF 2.6 to 3.1 at 5 mA")]

# Clock and bus assumptions used by the computed rows (stated in the notes of each row).
F_ADC = 40.0   # MHz, Y2 ECS-TXO-32CSMV-400 is 40.000 MHz (ecs-txo-32csmv-datasheet p1 code table)
C_LOAD = 10e-12  # F per output pin (pad plus a short trace and one input)


def led(v):
    return (round((v - VF_TYP) / 1.0, 3), round((v - VF_MIN) / 1.0, 3))  # 1 kohm, mA


def div(v, r_k):
    """Feedback or bias divider: v volts over r_k kohm total, mA."""
    return round(v / r_k, 4)


def cvf(v, n, f_mhz, c=C_LOAD):
    """Output switching current, mA: n pins x C x V x f (the datasheet formula of AD9237 p19)."""
    return round(n * c * v * f_mhz * 1e6 * 1e3, 2)


def pull(v, r_k):
    """Pull-up: idle high draws nothing; held low it draws V / R."""
    return 0.0, round(v / r_k, 3)


ad9237_drv_typ = round(4.5 * 3.3 / 2.5, 2)       # IDRVDD typ 4.5 mA at DRVDD 2.5 V, scaled to 3.3 V
ltc2292_ovdd_typ = round(4.9 * 3.3 / 1.8, 2)     # plot value 4.9 mA at 40 Msps, OVDD 1.8 V, scaled to 3.3 V

# key: (ref, supply path). path is the consumer's path in consumers.json without its last element.
# boards: "both", "2rx" or "1rx".
CURRENTS = []


def row(ref, path, part, how, typ, mx, src=(), why="", boards="both", note=""):
    CURRENTS.append(dict(ref=ref, path=list(path), boards=boards, part=part, how=how, typ=typ, max=mx,
                         src=[list(s) for s in src], why=why, note=note))


# ---- 1V0 ---------------------------------------------------------------------------------------
row("R32", ["1V0"], "FB divider R32 68k + R33 100k", "computed", div(1.0, 168), div(1.0, 168),
    why="V/(R32+R33) = 1.0 V / 168 k; the divider is the load of the output, no datasheet needed")
row("U30", ["1V0"], "XC7A100T-1FTG256C VCCINT + VCCBRAM", "step3", None, None,
    src=[("amd-ds181-artix7-datasheet", 5, "ICCINTQ 155 mA (-1, 1.0 V) quiescent"),
         ("amd-ds181-artix7-datasheet", 7, "ICCBRAMQ 4 mA quiescent")],
    why="static plus dynamic current depends on the design; step 3 estimates it from the firmware repo")

# ---- 3V8 direct loads ---------------------------------------------------------------------------
t, m = led(3.8)
row("R24", ["3V8"], "R24 1k + LED D1", "computed", t, m, src=LED_SRC,
    why="(3.8 V - Vf) / 1 k; LED colour not chosen, Vf 2.1 V typ (red mid) and 1.8 V (lowest candidate) for the max")
row("R34", ["3V8"], "FB divider R34 100k + R35 18.7k", "computed", div(3.8, 118.7), div(3.8, 118.7),
    why="V/(R34+R35) = 3.8 V / 118.7 k")
t, m = pull(3.8, 10)
row("R104", ["3V8"], "R104 10k pull-up on U23 PG (open drain)", "computed", t, m,
    why="idle high draws 0; PG pulled low draws 3.8 V / 10 k")

# ---- LDO ground currents (the LDO passes load plus ground current to the buck) ------------------
for ref in ("U20", "U39"):
    row(ref, ["3V8"], "LP5907-3.0 ground current", "datasheet", 0.05, 0.35,
        src=[("ti-lp5907-datasheet", 5, "IG 50 uA at IOUT 100 mA (typ); 14 uA at 0 mA"),
             ("ti-lp5907-datasheet", 7, "Fig 5-5 ground current vs output current, 350 uA axis end at 250 mA")],
        note="max is the plot axis end (the table gives no maximum), above any load here")
for ref in ("U23", "U24", "U25"):
    p = 8 if ref == "U25" else 7
    row(ref, ["3V8"], "LD39200 ground current (IQ at 2 A, covers every load)", "datasheet", 1.0, 3.0,
        src=[("st-ld39200-datasheet", p, "IQ 1 mA typ / 3 mA max at IOUT 2 A, -40 to 125 C"
              + (" (Table 6, fixed version)" if ref == "U25" else " (Table 5, adjustable version)"))],
        note="IQ at 2 A is the largest row in the table, so it bounds every load")
row("U22", ["5V6"], "LD39200 ground current (IQ at 2 A)", "datasheet", 1.0, 3.0,
    src=[("st-ld39200-datasheet", 7, "IQ 1 mA typ / 3 mA max at IOUT 2 A, Table 5 adjustable version")])

# ---- U20 3V0 (RF bias): TRF37A73 x2, HMC431LP4, SKY65404 x2 --------------------------------------
for ref in ("U9", "U13"):
    row(ref, ["3V8", "U20"], "TRF37A73 gain block, ICC on RFOUT bias and VCC pin", "datasheet", 55, 65,
        src=[("ti-trf37a73-datasheet", 5, "Total supply current 55 typ, 65 max mA, VCC 3.3 V, PWDN low")],
        note="board supply is 3.0 V, inside the 3.0-3.45 V operating range (p4); current taken as for 3.3 V")
row("U10", ["3V8", "U20"], "HMC431LP4 VCO", "datasheet", 27, 34,
    src=[("adi-hmc431lp4-datasheet", 1, "Icc 27 mA at Vcc 3.0 V"),
         ("adi-hmc431lp4-datasheet", 3, "Typical supply current vs Vcc: 19 / 27 / 34 mA at 2.75 / 3.0 / 3.25 V")],
    note="max is the 3.25 V row of the table (the sheet gives no maximum); the rail is 3.0 V +-2 %")
for ref in ("U11", "U16"):
    row(ref, ["3V8", "U20"], "SKY65404-31 LNA: drain current plus V_ENABLE pin (tied to VCC)", "datasheet",
        round(11 + 2.3, 2), round(15 + 3.0, 2),
        src=[("skyworks-sky65404-datasheet", 3, "Drain current 10 min / 11 typ / 15 max mA at VCC 3 V, V_ENABLE 3 V"),
             ("skyworks-sky65404-datasheet", 3, "V_ENABLE current IEN_HIGH 2.3 / 3.0 mA at V_ENABLE 3 V")],
        note="IEN_HIGH row shows two values; taken as typ 2.3 and max 3.0 (the order of the Min/Typ/Max columns "
             "is not readable in the text layer)")

# ---- U23 1V8: FPGA VCCAUX ----------------------------------------------------------------------
row("R45", ["3V8", "U23"], "FB divider R45 49.9k + R46 18.7k", "computed", div(1.83, 68.6), div(1.83, 68.6),
    why="V/(R45+R46) = 1.83 V / 68.6 k")
row("U30", ["3V8", "U23"], "XC7A100T VCCAUX", "datasheet", 36, 76,
    src=[("amd-ds181-artix7-datasheet", 6, "ICCAUXQ 36 mA, XC7A100T -1 (typical quiescent)"),
         ("amd-ds181-artix7-datasheet", 8, "Table 6: ICCAUXMIN = ICCAUXQ + 40 mA for XC7A100T = 76 mA")],
    note="typ is the quiescent figure (VCCAUX dynamic current is small: MMCM/PLL and I/O bias); max is the power-on "
         "and configuration current the supply must give, which bounds the running value; the Vivado power report replaces both")

# ---- U24 3V3A: ADF4158, LT6232 --------------------------------------------------------------------
row("R47", ["3V8", "U24"], "FB divider R47 18.7k + R48 3.3k", "computed", div(3.33, 22.0), div(3.33, 22.0),
    why="V/(R47+R48) = 3.33 V / 22.0 k")
row("U1", ["3V8", "U24"], "ADF4158 AVDD + DVDD + SDVDD (pins 6,7,8,18,19)", "datasheet", 23, 32,
    src=[("adi-adf4158-datasheet", 4, "Power supplies IDD 23 typ / 32 max mA")])
row("U45", ["3V8", "U24"], "LT6232 quad op amp, 4 x supply current per amplifier", "datasheet",
    round(4 * 3.15, 2), round(4 * 4.4, 2),
    src=[("adi-lt6232-datasheet", 4, "IS 3.15 typ / 3.5 max mA per amplifier at 25 C, VS 3.3 V and 5 V"),
         ("adi-lt6232-datasheet", 6, "IS 4.4 mA max per amplifier over -40 to 85 C")],
    note="LT6232 is the quad (p1); all four amplifiers draw supply current whether used or not. max uses the "
         "-40 to 85 C figure")

# ---- U25 3V3D --------------------------------------------------------------------------------------
row("J2", ["3V8", "U25"], "J2 2x8 header, pins 13 and 15 (3V3D out)", "bound", 0.0, 100.0,
    why="a header pin: the design does not say what is plugged in, and no datasheet of a connector gives a load. "
        "100 mA is a stated allowance (about 5 % of the LD39200 2 A rating); anything above is the user's to set. "
        "open item for the report")
for ref, r in (("R14", 4.7), ("R112", 4.7), ("R117", 4.7), ("R118", 4.7), ("R72", 1.0), ("R73", 10.0)):
    t, m = pull(3.3, r)
    row(ref, ["3V8", "U25"], f"{ref} {r:g}k pull-up to 3V3D", "computed", t, m,
        why=f"idle high draws 0; held low draws 3.3 V / {r:g} k")
t, m = led(3.3)
row("R111", ["3V8", "U25"], "R111 1k + LED D2", "computed", t, m, src=LED_SRC,
    why="(3.3 V - Vf) / 1 k; Vf 2.1 V typ, 1.8 V for the max (colour not chosen)")
row("U6", ["3V8", "U25"], "PL133-37 clock buffer, 3 outputs at 40 MHz", "datasheet",
    round(1.2 * F_ADC / 25, 2), round(1.2 * F_ADC / 25 + cvf(3.3, 3, F_ADC, 15e-12), 2),
    src=[("microchip-pl133-37-datasheet", 3, "IDD dynamic 1.2 mA at VDD 3.3 V, 25 MHz, no load; test load 15 pF")],
    note="typ scales the no-load current to 40 MHz (Y2 frequency); max adds 3 outputs x 15 pF x 3.3 V x 40 MHz. "
         "The sheet gives no maximum")
row("Y2", ["3V8", "U25"], "ECS-TXO-32CSMV-400 TCXO, 40 MHz", "datasheet", 2.5, 2.5,
    src=[("ecs-txo-32csmv-datasheet", 1, "Current consumption 2.5 mA for 26.1 to 52 MHz")],
    note="one figure, in the maximum column; typ is taken equal to it")
row("U8", ["3V8", "U25"], "LTC2292 OVDD (pins 32, 49), 24 outputs", "datasheet", ltc2292_ovdd_typ,
    cvf(3.3, 24, F_ADC), boards="2rx",
    src=[("adi-ltc2293-2292-2291-datasheet", 9, "LTC2292 IOVDD vs sample rate: 4.9 mA at 40 Msps, OVDD 1.8 V (plot read)"),
         ("adi-ad9237-datasheet", 19, "IDRVDD = V x CLOAD x fCLK x N (the CV f bound used for the max)")],
    note="typ is the plot value scaled by 3.3/1.8; max is 24 pins x 10 pF x 3.3 V x 40 MHz (every pin toggling "
         "every cycle); the LTC2292 sheet gives no maximum for IOVDD")
row("U8", ["3V8", "U25"], "AD9237BCPZ-40 DRVDD (pin 16), 12 outputs", "datasheet", ad9237_drv_typ,
    cvf(3.3, 12, F_ADC), boards="1rx",
    src=[("adi-ad9237-datasheet", 3, "IDRVDD 4.5 mA typ at DRVDD 2.5 V, 40 MHz grade, ~5 pF per bit"),
         ("adi-ad9237-datasheet", 19, "IDRVDD = V x CLOAD x fCLK x N, N = 12")],
    note="typ scales 4.5 mA by 3.3/2.5; max is 12 x 10 pF x 3.3 V x 40 MHz")
row("U30", ["3V8", "U25"], "XC7A100T VCCO, 5 banks (0, 14, 15, 34, 35) all on 3V3D", "datasheet",
    round(4 + cvf(3.3, 8, 30.0), 2), 4 + 40 * 5,
    src=[("amd-ds181-artix7-datasheet", 5, "ICCOQ 4 mA quiescent, XC7A100T"),
         ("amd-ds181-artix7-datasheet", 8, "Table 6: ICCOMIN = ICCOQ + 40 mA per bank; 5 banks = 204 mA"),
         ("amd-xc7a100t-ftg256-pinout", 1, "VCCO pins of banks 0, 14, 15, 34, 35 are the 3V3D pins of U30")],
    note="typ adds 8 output pins x 10 pF x 3.3 V x 30 MHz (the FT2232H FIFO bus) to ICCOQ; max is the per-bank "
         "power-on current, which bounds the running value")
row("U32", ["3V8", "U25"], "93LC46B EEPROM", "datasheet", 0.001, 2.0,
    src=[("microchip-93lc46b-datasheet", 3, "ICC write 2 mA max, read 1 mA max (VCC 5.5 V, 3 MHz); standby 1 uA max")],
    note="the EEPROM is read at USB enumeration; typ is the standby current")
row("U33", ["3V8", "U25"], "FT2232H: core 1.8 V from VREGIN 3.3 V, plus VCCIO", "datasheet",
    round(70 + cvf(3.3, 8, 30.0), 2), round(150 + cvf(3.3, 8, 30.0), 2),
    src=[("ftdi-ft2232h-datasheet", 47, "Icc1 70 mA normal operation (VCORE, from the internal regulator); "
                                       "Ireg 150 mA regulator current (the most it can supply)")],
    note="the core current comes through the internal regulator from the 3.3 V pin, so it loads 3V3D one for one; "
         "I/O adds 8 pins x 10 pF x 3.3 V x 30 MHz; max replaces Icc1 with Ireg (the sheet gives no maximum for Icc1)")
row("U40", ["3V8", "U25"], "W25Q128JV flash", "datasheet", 0.01, 25.0,
    src=[("winbond-w25q128jv-datasheet", 63, "ICC1 standby 10 uA typ; ICC3 read 8 / 15 mA at 50 MHz; "
                                             "ICC4-7 program and erase 20 / 25 mA")],
    note="typ is standby after FPGA configuration; max is a program or erase cycle, which a running radar does not issue")

# ---- U39 3V0 (ADC analog) -----------------------------------------------------------------------
row("R91", ["3V8", "U39"], "R91 4.7k + R92 10k MODE divider", "computed", div(3.0, 14.7), div(3.0, 14.7),
    why="V/(R91+R92) = 3.0 V / 14.7 k, a standing divider (sets MODE to 2/3 VDD)")
row("U8", ["3V8", "U39"], "LTC2292 VDD (pins 7, 10, 18, 63) + SENSE/MODE leakage", "datasheet", 78, 95, boards="2rx",
    src=[("adi-ltc2293-2292-2291-datasheet", 5, "IVDD supply current, both ADCs at fS(MAX) 40 MHz: 78 typ / 95 max mA"),
         ("adi-ltc2293-2292-2291-datasheet", 3, "input leakage 1 to 3 uA (MODE, analog inputs)")],
    note="pin leakage is microamps and not added")
row("U8", ["3V8", "U39"], "AD9237BCPZ-40 AVDD (pins 27, 32)", "power/V", 45.5, round(180 / 3.0, 1), boards="1rx",
    src=[("adi-ad9237-datasheet", 3, "IAVDD 45.5 mA typ (BCP-40 column); power 150 typ / 180 max mW at "
                                     "AVDD 3 V, DRVDD 2.5 V, 40 MSPS")],
    note="the sheet gives IAVDD typ only; max is 180 mW / 3.0 V, which counts the DRVDD share too, so it is high")
row("R990", ["3V8", "U39"], "R990 1.0k (new, rx1-005) to ADC_VCMB", "computed", div(3.0, 2.0), div(3.0, 2.0),
    boards="1rx", why="3.0 V / (R990 + R991) = 3.0 V / 2 k, a standing divider (rx1-005, rx1-006)")
row("R991", ["3V8", "U39"], "R991 1.0k (new, rx1-006) to GND", "computed", 0.0, 0.0, boards="1rx",
    why="in series with R990; the 1.5 mA is counted once, on R990")

# ---- U22 5V ---------------------------------------------------------------------------------------
row("R27", ["5V6"], "R27 1k + LED D7", "computed", *led(5.6), src=LED_SRC,
    why="(5.6 V - Vf) / 1 k; Vf 2.1 V typ, 1.8 V for the max (colour not chosen)")
row("R36", ["5V6"], "FB divider R36 100k + R37 12k", "computed", div(5.6, 112), div(5.6, 112),
    why="V/(R36+R37) = 5.6 V / 112 k")
row("R43", ["5V6", "U22"], "FB divider R43 18k + R44 2k", "computed", div(5.0, 20.0), div(5.0, 20.0),
    why="V/(R43+R44) = 5.0 V / 20 k")
row("R49", ["5V6", "U22"], "R49 2k from 5VF to U29 VSET", "bound", 0.0, 2.5,
    why="the ADL5802 sheet gives no VSET pin current (VSET is a bias control node, p6). Bound: 5 V / 2 k = 2.5 mA, "
        "the current if the pin sat at ground; typ 0")
for ref in ("R51", "R52", "R53", "R54"):
    row(ref, ["5V6", "U22"], "49.9 ohm IF output pull-up to 5VF", "datasheet", 0.0, 0.0,
        src=[("adi-adl5802-datasheet", 4, "note 2: supply is applied through the IF pull-ups; the 220/300 mA "
                                          "quiescent current of U29 includes the output pull-up current")],
        note="counted in U29, not again here")
row("U1", ["5V6", "U22"], "ADF4158 VP, charge-pump supply (pin 22)", "bound", 0.0, 5.0,
    src=[("adi-adf4158-datasheet", 4, "charge pump ICP high value 5 mA with RSET 5.1 kohm; no VP supply current is given")],
    why="the sheet lists no VP current; the pump sources at most ICP, 5 mA, only while correcting phase error "
        "(about 0 mA locked). typ 0, max 5 mA")
row("U14", ["5V6", "U22"], "TQP5525 PA, VCC1+VCC2+VCC3, 25.5 dBm at the PA output", "datasheet", 664.3, 850,
    src=[("qorvo-tqp5525-datasheet", 3, "operating current: 600 typ / 675 max mA at +24 dBm; 750 / 850 mA at +27.5 dBm; "
                                        "quiescent 350 / 400 mA RF off")],
    note="par-07 requires 25.5 dBm at the PA output; typ interpolates 600 -> 750 mA between +24 and +27.5 dBm "
         "(664.3 mA); max is the +27.5 dBm row, the highest the sheet gives (PA is at P1dB 30 dBm there)")
row("U29", ["5V6", "U22"], "ADL5802 mixer, VPOS pins 6, 13, 24", "datasheet", 220, 300,
    src=[("adi-adl5802-datasheet", 3, "power interface: quiescent current 220 typ / 300 max mA, 5 V")],
    note="the row shows two values (220 and 300); read as typ and max")


# -----------------------------------------------------------------------------------------------------------
def key(c):
    return (c["ref"], tuple(c["path"][:-1]))


def flat(consumers):
    for c in consumers:
        yield c
        yield from flat(c.get("children", []))


def table(board, data):
    """Consumer rows of one board with their currents; fitted only; returns (rows, problems)."""
    rows, problems = [], []
    byk = {}
    for r in CURRENTS:
        if r["boards"] in ("both", board):
            byk.setdefault((r["ref"], tuple(r["path"])), []).append(r)
    used = set()
    for rail, rd in data["boards"][board]["rails"].items():
        for c in flat(rd["consumers"]):
            k = key(c)   # an LDO's row is its ground current, filed under the rail that feeds it
            hit = byk.get(k, [])
            if not c["fitted"]:
                used.update(id(h) for h in hit)   # a not-fitted part keeps its row, off the board's table
                continue
            if len(hit) != 1:
                problems.append(f"{board} {rail} {c['ref']} path {k[1]}: {len(hit)} rows")
                continue
            used.add(id(hit[0]))
            rows.append(dict(rail=rail, **{kk: hit[0][kk] for kk in
                                           ("ref", "path", "part", "how", "typ", "max", "src", "why", "note")},
                             role=c["role"], children=bool(c.get("children"))))
    for k, hits in byk.items():
        for h in hits:
            if id(h) not in used:
                problems.append(f"{board}: row {h['ref']} {h['path']} matches no fitted consumer")
    return rows, problems


def manifest_ids():
    m = yaml.safe_load(open(ROOT / "datasheets" / "manifest.yaml"))
    return {e["id"] for e in m["entries"]}


def check(data):
    ids = manifest_ids()
    for board in ("2rx", "1rx"):
        rows, problems = table(board, data)
        assert not problems, problems
        for r in rows:
            where = f"{board} {r['ref']} {r['path']}"
            assert r["how"] in ("datasheet", "power/V", "computed", "bound", "step3"), where
            if r["how"] == "step3":
                assert r["typ"] is None and r["max"] is None and r["ref"] == "U30" and r["src"], where
                continue
            assert r["typ"] is not None and r["max"] is not None and 0 <= r["typ"] <= r["max"], where
            if r["how"] in ("datasheet", "power/V"):
                assert r["src"], f"{where}: a datasheet current needs a manifest id and page"
            else:
                assert r["why"], f"{where}: a {r['how']} current states its reason"
            for sid, page, what in r["src"]:
                assert sid in ids, f"{where}: {sid} is not in datasheets/manifest.yaml"
                assert isinstance(page, int) and page >= 1 and what, where
    # the rows the 1-RX board changes
    t1 = {(r["ref"], tuple(r["path"])): r for r in table("1rx", data)[0]}
    t2 = {(r["ref"], tuple(r["path"])): r for r in table("2rx", data)[0]}
    assert not any(r["ref"] in ("U13", "U16") for r in table("1rx", data)[0])
    assert any(r["ref"] == "U13" for r in table("2rx", data)[0])
    assert {"R990", "R991"} <= {r["ref"] for r in table("1rx", data)[0]}
    assert not ({"R990", "R991"} & {r["ref"] for r in table("2rx", data)[0]})
    assert t1 and t2
    return True


def total(rows, rail, which):
    """Rough sum on the buck rail: every consumer row once (LDO children included), mA. Step 4 redoes this."""
    return round(sum(r[which] or 0 for r in rows if r["rail"] == rail), 1)


def show(data):
    for board in ("2rx", "1rx"):
        rows, _ = table(board, data)
        print(f"== {board}")
        for rail in ("1V0", "3V8", "5V6"):
            print(f"  {rail}: typ {total(rows, rail, 'typ')} mA  max {total(rows, rail, 'max')} mA "
                  f"(without the VCCINT estimate of step 3)" if rail == "1V0" else
                  f"  {rail}: typ {total(rows, rail, 'typ')} mA  max {total(rows, rail, 'max')} mA")
            for r in rows:
                if r["rail"] == rail:
                    p = "/".join(r["path"][1:]) or "-"
                    t = "step3" if r["typ"] is None else f"{r['typ']:8.3f}"
                    m = "" if r["max"] is None else f"{r['max']:8.3f}"
                    print(f"    {r['ref']:5} {p:7} {r['how']:9} {t:>8} {m:>8}  {r['part'][:60]}")


def build():
    data = json.load(open(CONSUMERS))
    out = {"source": "analysis/12_rail_loads/currents.py; consumers from sim/consumers.json; mA", "boards": {}}
    for board in ("2rx", "1rx"):
        rows, problems = table(board, data)
        out["boards"][board] = dict(rows=rows, problems=problems)
    return data, out


if __name__ == "__main__":
    cons, out = build()
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    if "--show" in sys.argv:
        show(cons)
    if "--check" in sys.argv:
        check(cons)
        print("currents: check ok")
