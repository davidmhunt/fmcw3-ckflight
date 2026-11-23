"""par-11 step 4: per buck rail and board, the DC load, the inductor ripple and peak, and the pass marks
for the APS0650M330A (Coilank, L5-L7).

DC load per rail: the sum of every consumer row of the rail (currents.py), each once. An LDO's own row is
its ground current and its children are its loads, so the sum is the current the buck delivers (an LDO
passes its load plus its ground current back to the buck). The 1V0 rail adds the FPGA core of step 3
(vccint.py). Typical and maximum are summed separately.

Ripple, ti-lmr51420 equation 10 (PDF page 18, section 9.2.2.4):
    dIL = Vout * (VIN - Vout) / (VIN * L * fsw)
with VIN = 12 V (the net /power/12V on pin 3 of U17-U19, checked in consumers.py), Vout from the feedback
dividers (0.6 V reference, ti-lmr51420 p5 Vfb), L = 33 uH less 20 % (26.4 uH), fsw 500 kHz and 1.1 MHz.
The suffix of U17-U19 is unresolved (parts/decisions.csv: user-choice, X/XF 500 kHz, Y/YF 1.1 MHz), so
both are reported and the worst case (the larger ripple, 500 kHz) is the one the pass mark uses.
The ripple does not depend on the load in continuous conduction. The peak is DC + ripple / 2.

Pass marks (APS0650M330A, manifest coilank-aps1040m330a-datasheet, PDF page 6 row APS0650M330A:
33 uH, DCR 178 mohm max, Irms 2.32 A, Isat 3.53 A; page 1: Isat is the current at which L drops about
40 %, Irms the current for about a 40 C rise):
    peak     <= 0.60 * Isat  (2.118 A)
    DC load  <= 2/3 * Irms   (1.547 A), and <= 2 A (the LMR51420 rating, ti-lmr51420 p1)
Copper loss at the typical load: I_typ^2 * DCR (the DCR is the maximum, so the loss is an upper figure).

Fault case (no pass mark): the high-side peak current limit 2.7 / 3.5 / 5.1 A min / typ / max
(ti-lmr51420 p5, IHS_PK(OC)) against Isat, the maximum output current of equation 8 (p14), and hiccup (p14).

Run: ./run python3 analysis/12_rail_loads/loads.py [--check] [--show]   (writes sim/loads.json)
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import currents  # noqa: E402

OUT = HERE / "sim" / "loads.json"
VCCINT = HERE / "sim" / "vccint.json"

VIN = 12.0                     # V, /power/12V
VREF = 0.6                     # V, ti-lmr51420 p5 Vfb typ
# feedback dividers (top, bottom) in kohm: R32/R33, R34/R35, R36/R37 (currents.py header)
DIVIDERS = {"1V0": (68.0, 100.0), "3V8": (100.0, 18.7), "5V6": (100.0, 12.0)}
# 1V0: the divider R32 (top, 68k) to R33 (bottom, 100k) gives Vout = 0.6 * (1 + 68/100)
L_NOM_UH = 33.0
L_DROP = 0.20                  # inductance 20 % low
FSW = {"500 kHz": 500e3, "1.1 MHz": 1.1e6}

# APS0650M330A, coilank-aps1040m330a-datasheet PDF page 6
INDUCTOR = dict(part="APS0650M330A", manifest_id="coilank-aps1040m330a-datasheet", page=6,
                L_uH=33.0, dcr_ohm=0.178, irms_a=2.32, isat_a=3.53)
PEAK_FRAC, DC_FRAC = 0.60, 2.0 / 3.0
LMR_RATING_A = 2.0             # ti-lmr51420 p1: 2 A converter
LMR_ILIM = dict(min=2.7, typ=3.5, max=5.1)       # IHS_PK(OC), p5
LMR_ILS_VALLEY = dict(min=1.7, typ=2.5, max=3.4)  # ILS_V(OC), p5/6
PEAK_LIMIT_A = PEAK_FRAC * INDUCTOR["isat_a"]
DC_LIMIT_A = min(DC_FRAC * INDUCTOR["irms_a"], LMR_RATING_A)


def vout(rail):
    top, bot = DIVIDERS[rail]
    return VREF * (1 + top / bot)


def ripple(v_out, l_uh, fsw, vin=VIN):
    """ti-lmr51420 equation 10, amperes peak to peak."""
    return v_out * (vin - v_out) / (vin * l_uh * 1e-6 * fsw)


def rail_dc(rows, rail, which, step3):
    """DC load of one buck rail, amperes."""
    ma = sum(r[which] or 0 for r in rows if r["rail"] == rail)
    if rail == "1V0":
        ma += step3[which]
    return ma / 1000.0


def build():
    cons = json.load(open(currents.CONSUMERS))
    v3 = json.load(open(VCCINT))["estimate"]
    step3 = {"typ": v3["typ_mA"], "max": v3["max_mA"]}
    l_low = L_NOM_UH * (1 - L_DROP)
    out = {"source": "analysis/12_rail_loads/loads.py; currents from currents.py, FPGA core from vccint.py; A",
           "vin_v": VIN, "l_nom_uh": L_NOM_UH, "l_low_uh": l_low, "inductor": INDUCTOR,
           "limits": dict(peak_a=PEAK_LIMIT_A, dc_a=DC_LIMIT_A, peak_frac=PEAK_FRAC, dc_frac=DC_FRAC,
                          lmr_rating_a=LMR_RATING_A),
           "boards": {}}
    worst_peak = worst_dc = 0.0
    for board in ("2rx", "1rx"):
        rows, problems = currents.table(board, cons)
        assert not problems, problems
        rails = {}
        for rail in ("1V0", "3V8", "5V6"):
            v = vout(rail)
            typ, mx = rail_dc(rows, rail, "typ", step3), rail_dc(rows, rail, "max", step3)
            rip = {name: ripple(v, l_low, f) for name, f in FSW.items()}
            rip_nom = {name: ripple(v, L_NOM_UH, f) for name, f in FSW.items()}
            rip_worst = max(rip.values())
            peak_typ = {n: typ + r / 2 for n, r in rip.items()}
            peak_max = {n: mx + r / 2 for n, r in rip.items()}
            pk = max(peak_max.values())
            rails[rail] = dict(
                vout_v=v, dc_typ_a=typ, dc_max_a=mx,
                ripple_pp_a=rip, ripple_nominal_L_pp_a=rip_nom,
                peak_typ_a=peak_typ, peak_max_a=peak_max, peak_worst_a=pk,
                copper_loss_typ_w=typ ** 2 * INDUCTOR["dcr_ohm"],
                copper_loss_max_w=mx ** 2 * INDUCTOR["dcr_ohm"],
                peak_ok=pk <= PEAK_LIMIT_A, dc_ok=mx <= DC_LIMIT_A,
                peak_margin_a=PEAK_LIMIT_A - pk, dc_margin_a=DC_LIMIT_A - mx,
                ripple_worst_a=rip_worst)
            worst_peak, worst_dc = max(worst_peak, pk), max(worst_dc, mx)
        out["boards"][board] = rails
    out["peak_max_a"], out["dc_max_a"] = worst_peak, worst_dc
    out["aps0650_ok"] = int(all(r["peak_ok"] and r["dc_ok"] for b in out["boards"].values() for r in b.values()))
    isat = INDUCTOR["isat_a"]
    out["fault"] = dict(
        ihs_pk_oc_a=LMR_ILIM, ils_valley_a=LMR_ILS_VALLEY,
        iout_max_eq8_a={k: (LMR_ILS_VALLEY[k] + LMR_ILIM[k]) / 2 for k in ("min", "typ", "max")},
        isat_a=isat,
        peak_limit_over_isat={k: v / isat for k, v in LMR_ILIM.items()},
        saturates_at={k: v > isat for k, v in LMR_ILIM.items()},
        hiccup=dict(trigger="FB below 40 % of VREF and the low-side switch at ILS_LIMIT for 256 consecutive cycles",
                    action="the converter shuts down and stays off for tHICCUP, 135 ms typ, then restarts; "
                           "it repeats while the fault remains",
                    blanking="tOCP_BLK 33 ms at power-up, so the soft-start inrush does not trigger it",
                    page=14, note="the directive names p.18; hiccup is on PDF page 14 (section 8.3.6), p.18 "
                                  "holds the inductor equation 10"),
        overload="an overload that keeps FB above 40 % of VREF is limited cycle by cycle at the peak limit, "
                 "not hiccup; the inductor then carries up to the peak limit")
    return out


def check(d):
    for board, rails in d["boards"].items():
        for rail, r in rails.items():
            assert r["dc_typ_a"] <= r["dc_max_a"], (board, rail)
            assert r["peak_worst_a"] >= r["dc_max_a"], (board, rail)
    assert abs(d["limits"]["peak_a"] - 2.118) < 1e-3 and abs(d["limits"]["dc_a"] - 1.5467) < 1e-3
    assert d["peak_max_a"] == max(r["peak_worst_a"] for b in d["boards"].values() for r in b.values())
    return True


def show(d):
    lim = d["limits"]
    print(f"VIN {d['vin_v']} V, L {d['l_nom_uh']} uH -20 % = {d['l_low_uh']:.1f} uH; "
          f"peak limit {lim['peak_a']:.3f} A, DC limit {lim['dc_a']:.3f} A")
    for board, rails in d["boards"].items():
        print(f"== {board}")
        for rail, r in rails.items():
            rp = r["ripple_pp_a"]
            print(f"  {rail} Vout {r['vout_v']:.3f}: DC typ {r['dc_typ_a']:.3f} max {r['dc_max_a']:.3f} A | "
                  f"ripple 500k {rp['500 kHz']:.3f} 1.1M {rp['1.1 MHz']:.3f} A | "
                  f"peak max 500k {r['peak_max_a']['500 kHz']:.3f} 1.1M {r['peak_max_a']['1.1 MHz']:.3f} A | "
                  f"Pcu typ {r['copper_loss_typ_w'] * 1e3:.0f} mW | "
                  f"peak {'ok' if r['peak_ok'] else 'FAIL'} dc {'ok' if r['dc_ok'] else 'FAIL'}")
    f = d["fault"]
    print("fault: IHS_PK(OC) min/typ/max", f["ihs_pk_oc_a"], "vs Isat", f["isat_a"],
          "-> ratio", {k: round(v, 2) for k, v in f["peak_limit_over_isat"].items()})
    print("  eq 8 max output current", f["iout_max_eq8_a"])
    print("  hiccup:", f["hiccup"]["trigger"], "->", f["hiccup"]["action"])
    print(f"aps0650_ok = {d['aps0650_ok']}  peak_max_a = {d['peak_max_a']:.3f}  dc_max_a = {d['dc_max_a']:.3f}")


if __name__ == "__main__":
    d = build()
    OUT.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    if "--show" in sys.argv:
        show(d)
    if "--check" in sys.argv:
        check(d)
        print("loads: check ok")
