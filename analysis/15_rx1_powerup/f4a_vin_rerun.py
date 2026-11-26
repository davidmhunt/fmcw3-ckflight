"""rx1-05 step 4: the settling and IF response of rx1-02 rerun with a larger VIN series resistance (fix F4a).

Runs in the fmcw3-sim image, from the repo root:
    ./run --sim sh -c "xvfb-run -a python3 -u analysis/15_rx1_powerup/f4a_vin_rerun.py"
It reuses analysis/11_board_1rx/adc_input_sim.py (the 1-RX case: AD9237 load, bias from 3V0 1k/1k) with the
series resistor between each U45 output and its AD9237 pin (R98/R100 in that script's netlist, the R97/R99
of the power-up report: the resistor in the same place, kicad-1rx/ refdes differ between the two notes)
at 49.9 ohm (today), 200 and 499 ohm, and writes sim/f4a_vin.json for figures.py. Same assumptions as
rx1-02 (sampling switch Ron 10 / 200 ohm, held sample "reset" the worst case); the rx1-02 sheet pages apply.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "11_board_1rx"))
import adc_input_sim as A  # noqa: E402

OUT = HERE / "sim" / "f4a_vin.json"
VALUES = (49.9, 200.0, 499.0)
_orig = A.netlist
_state = {"r": 49.9}


def patched(*a, **k):
    t = _orig(*a, **k)
    r = _state["r"]
    return t.replace("R98 outc pinn 49.9", "R98 outc pinn %g" % r).replace("R100 outd pinp 49.9", "R100 outd pinp %g" % r)


A.netlist = patched


def one(r):
    _state["r"] = r
    case = "rx1"
    tagp = "f4a_%g" % r
    f, h = A.do_ac(case)
    g = A.db(h)
    pick = lambda x: float(np.interp(math.log10(x), np.log10(f), g))  # noqa: E731
    gmax = float(g.max())
    above = f[g >= gmax - 3]
    out = {"r_ohm": r, "gain_db_200k": pick(A.F_SWING), "gain_db_1M": pick(A.F_TONE), "gain_db_2M": pick(2e6),
           "gain_db_20M": pick(2e7), "f3db_low_hz": float(above.min()), "f3db_high_hz": float(above.max()),
           "gain_max_db": gmax}
    fn, on = A.do_noise(case)
    out["noise_rms_to_20MHz_uv"] = A.integ(fn, on ** 2, 1e3, 20e6) * 1e6
    hf = abs(np.interp(math.log10(A.F_TONE), np.log10(f), np.abs(h)))
    amp = (A.SPAN / 2) * 10 ** (-1 / 20) / hf
    ref = A.tran(case, amp, A.F_TONE, "track", tag="ref_" + tagp)
    out["settling"] = []
    for hold, ron in (("keep", A.RON), ("reset", A.RON), ("reset", 50.0), ("reset", 200.0)):
        s = A.settling(case, amp, hold, ron, ref)
        s.pop("window", None)
        out["settling"].append(s)
    return out


def main() -> int:
    A.setup_wine()
    A.WORK.mkdir(parents=True, exist_ok=True)
    res = {"source": "analysis/15_rx1_powerup/f4a_vin_rerun.py", "lsb_uv": A.LSB * 1e6, "f_tone_hz": A.F_TONE,
           "values": {}}
    for r in VALUES:
        o = one(r)
        res["values"]["%g" % r] = o
        keep, reset = o["settling"][0], o["settling"][1]
        print("R %5.1f ohm: gain 200 kHz %.2f dB, 1 MHz %.2f dB, 2 MHz %.2f dB; -3 dB %.0f Hz to %.2f MHz; noise %.1f uV rms to 20 MHz; "
              "settle err max %.3f LSB (keep) %.3f LSB (reset Ron 10), residual at sample %.3f LSB"
              % (r, o["gain_db_200k"], o["gain_db_1M"], o["gain_db_2M"], o["f3db_low_hz"], o["f3db_high_hz"] / 1e6,
                 o["noise_rms_to_20MHz_uv"], keep["err_lsb_max"], reset["err_lsb_max"], reset["resid_diff_lsb_max"]), flush=True)
        for s in o["settling"]:
            print("   hold %-5s Ron %4.0f: err max %.3f rms %.3f LSB; lin gain %+.4f dB delay %.1f ps; nonlin %.4f LSB; "
                  "resid diff %.3f LSB; kick diff %.2f mV" % (s["hold"], s["ron_ohm"], s["err_lsb_max"], s["err_lsb_rms"],
                  s["lin_gain_err_db"], s["lin_delay_ps"], s["nonlin_resid_lsb_max"], s["resid_diff_lsb_max"],
                  s["kick_diff_mv_max"]), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=0))
    print("wrote %s" % OUT.relative_to(HERE.parents[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
