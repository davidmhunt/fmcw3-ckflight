"""rx1-02 step 3: LTspice model of the IF amplifier driving the ADC, today and 1-RX.

Runs in the fmcw3-sim image (LTspice under Wine, through spicelib), from the repo root:
    ./run --sim sh -c "xvfb-run -a python3 -u analysis/11_board_1rx/adc_input_sim.py"
(xvfb-run must not be the container's PID 1: it then waits forever for Xvfb's ready signal,
hence the `sh -c`, as in tests/test_sim_smoke.py.) It writes analysis/11_board_1rx/sim/adc_input.json (figures.py plots from it, so the report
rebuilds without the sim image) and prints a summary. It exits non-zero when a sanity check
against a hand calculation fails; design results are reported, not asserted.

The circuit is the kept receive chain from the kicad/ netlist (see runs/rx1-02/notes.md, step 2):
mixer U29 IF1 -> R55/R56 (0 ohm) -> L14/L15 2.2 uH -> C36 2.2 nF across -> C37/C38 10 nF ->
R31/R38 1 k -> U45 amps C/D (inverting, R39/R40 10 k || C39/C40 5 pF, + inputs on /ADC_VCMA)
-> R63/R64 (0 ohm) -> R98/R100 49.9 ohm -> C166/C168 100 pF to GND, C167 100 pF across -> U8.
U45 runs on 3V3A. The op-amp model is LTspice's LT6231 subcircuit (LTC2.lib); the LT6232
symbol uses it (fnd-05), so the same model covers the LT6232 (C or I grade) and the two-LT6231
option for U45 (par-09). A U45 replacement from another family needs this run repeated.

Two cases:
  today  LTC2292 load (adi-ltc2293-2292-2291-datasheet p.16: 15 ohm, 1 pF, 4 pF switched);
         bias from the LTC2292 VCMA pin (1.5 V, 4 ohm, p.4).
  rx1    AD9237 load (adi-ad9237-datasheet p.3: 7 pF per pin; p.16 Figure 35: 5 pF switched,
         so 2 pF fixed); bias from the step 2 divider, 1 k / 1 k from 3V0.
Assumptions (not in either datasheet): the sampling switch on-resistance (RON, swept), and what
the sample capacitor holds when a track phase starts: "keep" (the previous sample, best case)
or "reset" (discharged to 0 V, worst case). The mixer IF port is a Thevenin source of
49.9 ohm (R51/R52 pull-up) || 120 ohm (half the 240 ohm differential output impedance,
adi-adl5802-datasheet p.3) per side; its own noise is not modelled (rf-01).
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adc_numbers as N  # noqa: E402

WORK = Path(os.environ.get("RX1_SIM_WORK", "/tmp/rx1_adc_sim"))
OUT = HERE / "sim" / "adc_input.json"
PREFIX_BAKED = Path(os.environ.get("LTSPICE_PREFIX", "/opt/wineprefix"))
LT_DIR = PREFIX_BAKED / "drive_c/Program Files/ADI/LTspice"

FS = N.v(N.AD9237, "fs_hz")
TCLK = 1 / FS
SPAN = 2.0                       # V p-p differential, both ADCs (step 2 straps)
LSB = N.lsb_v(SPAN)
RS = 1 / (1 / 49.9 + 1 / 120.0)  # mixer source per side
RON = 10.0                       # assumed sampling-switch on-resistance (swept for rx1)
F_TONE = 1e6                     # top of the decimated band (2 MSPS / 2)
F_SWING = 200e3                  # overdrive test tone


def setup_wine():
    """Same as tests/sim/ltspice_smoke.py: a caller-owned prefix linking into the baked one."""
    pre = WORK / "wineprefix"
    pre.mkdir(parents=True, exist_ok=True)
    for p in list(PREFIX_BAKED.iterdir()):
        link = pre / p.name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(p)
    os.environ.update(WINEPREFIX=str(pre), WINEDEBUG="-all", USER="root",
                      LTSPICEFOLDER=str(LT_DIR), LTSPICEEXECUTABLE="LTspice.exe")


def netlist(case: str, analysis: str, src: str, load: str = "track", ron: float = RON,
            hold: str = "keep", save: str = "") -> str:
    """load: 'track' (switch always on: the static load), 'switched' (40 MHz clock)."""
    L = ["* rx1-02 step 3: %s, %s load, %s" % (case, load, analysis.split()[0]),
         ".lib LTC2.lib",
         "V3V3A va 0 3.3",
         "V5 v5 0 5",
         "Vin ctl 0 %s" % src,
         # differential Thevenin source, each side 0.5 * V(ctl) about the 5 V pull-up rail
         "Esp sp v5 ctl 0 0.5",
         "Esn sn v5 ctl 0 -0.5",
         "Rsp sp mp %.4f" % RS,
         "Rsn sn mn %.4f" % RS,
         "L14 mn fn 2.2u",
         "L15 mp fp 2.2u",
         "C36 fn fp 2.2n",
         "C37 fn an 10n",
         "C38 fp ap 10n",
         "R31 an invc 1k",
         "R38 ap invd 1k",
         "R39 invc outc 10k",
         "C39 invc outc 5p",
         "R40 invd outd 10k",
         "C40 invd outd 5p",
         "XU45C vcm invc outc va 0 LT6231",
         "XU45D vcm invd outd va 0 LT6231",
         "R98 outc pinn 49.9",
         "R100 outd pinp 49.9",
         "C166 pinn 0 100p",
         "C168 pinp 0 100p",
         "C167 pinn pinp 100p",
         "C216 vcm 0 2.2u",
         "C219 vcm 0 100n",
         "C63 vcm 0 100n"]
    if case == "today":
        L += ["Vvcm vcms 0 1.5", "Rvcm vcms vcm 4"]
        rin, cpar, cs = (N.v(N.LTC2292, "rin_ohm"), N.v(N.LTC2292, "cpar_pf"),
                         N.v(N.LTC2292, "csample_pf"))
    else:
        L += ["V3V0 v30 0 3.0", "Rb1 v30 vcm 1k", "Rb2 vcm 0 1k"]
        rin, cpar = 0.0, N.v(N.AD9237, "cin_pf") - N.v(N.AD9237, "csample_pf")
        cs = N.v(N.AD9237, "csample_pf")
    if load == "track":
        L += ["Vtrk trk 0 1", "Vhld hld 0 0"]
    else:
        # track while the clock is low, sample on its rising edge (ad9237 p.16; ltc2292 p.12)
        L += ["Vtrk trk 0 PULSE(0 1 0 0.1n 0.1n %gn %gn)" % (TCLK / 2 * 1e9 - 0.1, TCLK * 1e9),
              "Vhld hld 0 PULSE(1 0 0 0.1n 0.1n %gn %gn)" % (TCLK / 2 * 1e9 - 0.1, TCLK * 1e9)]
    for s in ("p", "n"):
        node = "pin" + s
        if rin:
            L.append("Rin%s pin%s x%s %g" % (s, s, s, rin))
            node = "x" + s
        L += ["Cpar%s %s 0 %gp" % (s, node, cpar),
              "Ssw%s %s q%s trk 0 SWT" % (s, node, s),
              "Cs%s q%s 0 %gp" % (s, s, cs)]
        if hold == "reset":
            L.append("Srst%s q%s 0 hld 0 SWT" % (s, s))
    L += [".model SWT SW(Ron=%g Roff=1G Vt=0.5 Vh=0)" % ron,
          ".options plotwinsize=0",
          save, analysis, ".end", ""]
    return "\n".join(x for x in L if x)


_RUN = {"n": 0}


def run(text: str, tag: str):
    from spicelib import RawRead, SimRunner
    from spicelib.simulators.ltspice_simulator import LTspice
    _RUN["n"] += 1
    d = WORK / tag
    d.mkdir(parents=True, exist_ok=True)
    (WORK / "src").mkdir(exist_ok=True)            # spicelib copies the netlist into d
    net = WORK / "src" / (tag + ".net")
    net.write_text(text)
    runner = SimRunner(output_folder=str(d), simulator=LTspice)
    rawf, logf = runner.run_now(str(net), run_filename=tag + ".net", timeout=900)
    main = d / (tag + ".raw")
    log = Path(logf).read_text(errors="replace") if logf and Path(logf).exists() else ""
    if not main.exists():
        raise RuntimeError("no raw file for %s; log: %s" % (tag, log[-1500:]))
    return RawRead(str(main)), log


def wave(raw, name):
    names = {n.lower(): n for n in raw.get_trace_names()}
    return np.asarray(raw.get_trace(names[name.lower()]).get_wave(0))


def axis(raw):
    return np.abs(np.real(wave(raw, raw.get_trace_names()[0])))


def db(x):
    return 20 * np.log10(np.abs(x))


# ---------------------------------------------------------------------------- analyses
def do_op(case):
    raw, _ = run(netlist(case, ".op", "0"), "op_" + case)
    g = lambda n: float(np.real(wave(raw, n))[0])  # noqa: E731
    return {"vcm": g("V(vcm)"), "pinp": g("V(pinp)"), "pinn": g("V(pinn)"),
            "outc": g("V(outc)"), "outd": g("V(outd)"),
            "pin_cm": (g("V(pinp)") + g("V(pinn)")) / 2,
            "pin_diff_mv": (g("V(pinp)") - g("V(pinn)")) * 1e3}


def do_ac(case):
    raw, _ = run(netlist(case, ".ac dec 40 1k 100Meg", "0 AC 1"), "ac_" + case)
    f = axis(raw)
    h = wave(raw, "V(pinp)") - wave(raw, "V(pinn)")
    return f, h


def do_noise(case):
    raw, _ = run(netlist(case, ".noise V(pinp,pinn) Vin dec 40 1k 100Meg", "0 AC 1"), "noise_" + case)
    f = axis(raw)
    on = np.abs(wave(raw, "V(onoise)"))
    return f, on


def integ(f, y2, f1, f2):
    m = (f >= f1) & (f <= f2)
    return float(np.sqrt(np.trapezoid(y2[m], f[m]) if hasattr(np, "trapezoid") else np.trapz(y2[m], f[m])))


def tran(case, amp, freq, load, hold="keep", ron=RON, tstop=6e-6, maxstep=0.05e-9, tag=None):
    src = "SINE(0 %g %g)" % (amp, freq)
    save = ".save V(pinp) V(pinn) V(qp) V(qn) V(outc) V(outd) V(vcm)"
    text = netlist(case, ".tran 0 %g 0 %g" % (tstop, maxstep), src, load, ron, hold, save)
    raw, _ = run(text, tag or "tr_%s_%s_%s_%g" % (case, load, hold, ron))
    t = axis(raw)
    return t, {k: np.real(wave(raw, "V(%s)" % k)) for k in
               ("pinp", "pinn", "qp", "qn", "outc", "outd", "vcm")}


def settling(case, amp, hold, ron, ref, freq=F_TONE):
    """Sampled-value error and pin kickback with the switched load against the static load.

    The error is split into a linear part (a gain and a phase error, fitted as
    a * v + b * dv/dt + c over the samples) and what is left; the linear part does not
    reduce the dynamic range. This model's switches are linear, so the residual is small by
    construction: signal-dependent charge injection is not in either datasheet."""
    t, w = tran(case, amp, freq, "switched", hold, ron,
                tag="tr_%s_%s_%g_%gk" % (case, hold, ron, freq / 1e3))
    tr, wr = ref
    t0 = 4e-6                                      # analyse the last 2 us (80 samples)
    k = np.arange(math.ceil(t0 / TCLK), math.floor(t[-1] / TCLK))
    ts = k * TCLK + TCLK / 2 - 0.15e-9             # just before the track phase ends
    held = np.interp(ts, t, w["qp"] - w["qn"])
    href = np.interp(ts, tr, wr["qp"] - wr["qn"])
    err_lsb = (held - href) / LSB
    A = np.column_stack([href, np.gradient(href, ts), np.ones_like(ts)])
    coef, *_ = np.linalg.lstsq(A, held - href, rcond=None)
    resid_lsb = (held - href - A @ coef) / LSB
    # pin glitch: differential and common mode, against the static run, over the window
    m = t >= t0
    pd = (w["pinp"] - w["pinn"])[m] - np.interp(t[m], tr, wr["pinp"] - wr["pinn"])
    pc = ((w["pinp"] + w["pinn"]) / 2)[m] - np.interp(t[m], tr, (wr["pinp"] + wr["pinn"]) / 2)
    # residual at the end of each track phase (the settling within half a clock)
    res_d = np.interp(ts, t[m], pd)
    res_c = np.interp(ts, t[m], pc)
    # a two-clock window for the figure, at the largest-slope sample
    w0 = ts[len(ts) // 2] - TCLK * 1.5
    mw = (t >= w0) & (t <= w0 + 3 * TCLK)
    if ron != RON or freq != F_TONE:               # keep the file small: one window per case
        mw = np.zeros_like(mw)
    return {
        "hold": hold, "ron_ohm": ron, "f_hz": freq,
        "err_lsb_max": float(np.max(np.abs(err_lsb))),
        "err_lsb_rms": float(np.sqrt(np.mean(err_lsb ** 2))),
        "lin_gain_err_db": float(20 * math.log10(abs(1 + coef[0]))),
        "lin_delay_ps": float(-coef[1] * 1e12),
        "nonlin_resid_lsb_max": float(np.max(np.abs(resid_lsb))),
        "kick_diff_mv_max": float(np.max(np.abs(pd)) * 1e3),
        "kick_cm_mv_max": float(np.max(np.abs(pc)) * 1e3),
        "resid_diff_lsb_max": float(np.max(np.abs(res_d)) / LSB),
        "resid_cm_mv_max": float(np.max(np.abs(res_c)) * 1e3),
        "cm_mean_v": float(np.mean(((w["pinp"] + w["pinn"]) / 2)[m])),
        "window": {"t_ns": ((t[mw] - w0) * 1e9).round(4).tolist(),
                   "pin_diff_v": (w["pinp"] - w["pinn"])[mw].round(6).tolist(),
                   "pin_cm_v": ((w["pinp"] + w["pinn"]) / 2)[mw].round(6).tolist(),
                   "ref_diff_v": np.interp(t[mw], tr, wr["pinp"] - wr["pinn"]).round(6).tolist(),
                   "track_edges_ns": [float((x - w0) * 1e9) for x in ts if w0 <= x <= w0 + 3 * TCLK]},
    }


def swing(case, amp_fs):
    """Overdrive at 3x full scale: where the chain clips, against the span."""
    t, w = tran(case, 3 * amp_fs, F_SWING, "track", tstop=40e-6, maxstep=2e-9,
                tag="swing_" + case)
    m = t >= 30e-6
    d = (w["pinp"] - w["pinn"])[m]
    t2, w2 = tran(case, amp_fs, F_SWING, "track", tstop=40e-6, maxstep=2e-9, tag="fs_" + case)
    m2 = t2 >= 30e-6
    outs = np.concatenate([w2["outc"][m2], w2["outd"][m2]])
    pins = np.concatenate([w2["pinp"][m2], w2["pinn"][m2]])
    return {
        "clip_diff_peak_v": float(np.max(np.abs(d))),
        "clip_pin_max_v": float(max(w["pinp"][m].max(), w["pinn"][m].max())),
        "clip_pin_min_v": float(min(w["pinp"][m].min(), w["pinn"][m].min())),
        "fs_diff_peak_v": float(np.max(np.abs((w2["pinp"] - w2["pinn"])[m2]))),
        "fs_out_min_v": float(outs.min()), "fs_out_max_v": float(outs.max()),
        "fs_pin_min_v": float(pins.min()), "fs_pin_max_v": float(pins.max()),
    }


def main() -> int:
    setup_wine()
    WORK.mkdir(parents=True, exist_ok=True)
    res = {"source": "analysis/11_board_1rx/adc_input_sim.py", "ron_ohm": RON,
           "rs_ohm": RS, "f_tone_hz": F_TONE, "fs_hz": FS, "lsb_uv": LSB * 1e6,
           "numbers": N.summary(), "cases": {}}
    checks = []
    for case in ("today", "rx1"):
        c = res["cases"][case] = {}
        c["op"] = do_op(case)
        f, h = do_ac(case)
        g = db(h)
        c["ac"] = {"f_hz": f.round(3).tolist(), "gain_db": g.round(4).tolist(),
                   "phase_deg": np.degrees(np.angle(h)).round(3).tolist()}
        pick = lambda x: float(np.interp(math.log10(x), np.log10(f), g))  # noqa: E731
        c["gain_db_at"] = {str(int(x)): pick(x) for x in (1e4, 1e5, 2e5, 1e6, 2e6, 2e7)}
        gmax = float(g.max())
        above = f[g >= gmax - 3]
        c["f3db_low_hz"], c["f3db_high_hz"] = float(above.min()), float(above.max())
        c["gain_max_db"] = gmax
        fn, on = do_noise(case)
        c["noise"] = {"f_hz": fn.round(3).tolist(), "onoise_nv": (on * 1e9).round(4).tolist(),
                      "rms_to_20MHz_uv": integ(fn, on ** 2, 1e3, 20e6) * 1e6,
                      "rms_to_100MHz_uv": integ(fn, on ** 2, 1e3, 100e6) * 1e6,
                      "rms_in_1MHz_uv": integ(fn, on ** 2, 1e3, 1e6) * 1e6}
        # transient: -1 dBFS at the pins at F_TONE
        hf = abs(np.interp(math.log10(F_TONE), np.log10(f), np.abs(h)))
        amp = (SPAN / 2) * 10 ** (-1 / 20) / hf
        c["tone_src_amp_v"] = amp
        ref = tran(case, amp, F_TONE, "track", tag="ref_" + case)
        c["settling"] = [settling(case, amp, "keep", RON, ref),
                         settling(case, amp, "reset", RON, ref)]
        if case == "rx1":
            for ron in (50.0, 200.0):
                c["settling"].append(settling(case, amp, "reset", ron, ref))
        # the same at the top of the beat band (200 kHz: 100 m, 300 MHz in 1 ms, targets)
        amp2 = (SPAN / 2) * 10 ** (-1 / 20) / 10 ** (pick(F_SWING) / 20)
        ref2 = tran(case, amp2, F_SWING, "track", tag="ref200k_" + case)
        c["settling"].append(settling(case, amp2, "keep", RON, ref2, F_SWING))
        c["swing"] = swing(case, (SPAN / 2) / (10 ** (pick(F_SWING) / 20)))
        # sanity checks against hand calculations
        hand_mid = 20 * math.log10(10 * 1000 / (1000 + RS))
        checks.append(("%s midband gain %.2f dB vs hand %.2f dB" % (case, c["gain_db_at"]["200000"], hand_mid),
                       abs(c["gain_db_at"]["200000"] - hand_mid) < 0.5))
        # DC: the inverting input's bias current flows through R39/R40 (10 k), so the output
        # sits IB x 10 k above the + input; IB 5 uA typ (adi-lt6232-datasheet p.3)
        hand_cm = c["op"]["vcm"] + 5e-6 * 10e3
        checks.append(("%s DC pin common mode %.4f V vs hand %.4f V (bias %.4f V + 5 uA x 10 k)"
                       % (case, c["op"]["pin_cm"], hand_cm, c["op"]["vcm"]),
                       abs(c["op"]["pin_cm"] - hand_cm) < 0.01))
        hand_vcm = 1.5 if case == "today" else 1.5 - 2 * 5e-6 * 500
        checks.append(("%s bias node %.4f V vs hand %.4f V" % (case, c["op"]["vcm"], hand_vcm),
                       abs(c["op"]["vcm"] - hand_vcm) < 0.003))
        fhp = 1 / (2 * math.pi * (1000 + RS) * 10e-9)
        checks.append(("%s low -3 dB %.0f Hz vs R31-C37 corner %.0f Hz" % (case, c["f3db_low_hz"], fhp),
                       0.7 < c["f3db_low_hz"] / fhp < 1.4))
    t, r = res["cases"]["today"], res["cases"]["rx1"]
    res["delta_gain_db"] = {k: r["gain_db_at"][k] - t["gain_db_at"][k] for k in t["gain_db_at"]}
    res["checks"] = [{"what": w, "ok": ok} for w, ok in checks]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=0))
    report(res)
    bad = [w for w, ok in checks if not ok]
    for w, ok in checks:
        print("CHECK %s %s" % ("PASS" if ok else "FAIL", w))
    print("wrote %s (%d LTspice runs)" % (OUT.relative_to(HERE.parent.parent), _RUN["n"]))
    return 1 if bad else 0


def report(res):
    lim = res["numbers"]["input_limits"]
    for case, c in res["cases"].items():
        print("== %s" % case)
        print("  op: vcm %.4f V, pin CM %.4f V, pin diff offset %.2f mV, out %.4f/%.4f V"
              % (c["op"]["vcm"], c["op"]["pin_cm"], c["op"]["pin_diff_mv"], c["op"]["outc"], c["op"]["outd"]))
        print("  gain: " + ", ".join("%s Hz %.2f dB" % (k, v) for k, v in c["gain_db_at"].items()))
        print("  -3 dB band %.0f Hz to %.0f Hz, peak %.2f dB" % (c["f3db_low_hz"], c["f3db_high_hz"], c["gain_max_db"]))
        n = c["noise"]
        print("  front-end noise at pins: %.1f uV rms to 20 MHz, %.1f to 100 MHz, %.1f in 1 MHz"
              % (n["rms_to_20MHz_uv"], n["rms_to_100MHz_uv"], n["rms_in_1MHz_uv"]))
        for s in c["settling"]:
            print("  settle %-5s Ron %5.0f f %4.0f kHz: err max %.3f LSB rms %.3f (linear: gain %+.4f dB, "
                  "delay %.1f ps; nonlinear rest %.4f LSB); kick diff %.2f mV cm %.1f mV; "
                  "residual at sample diff %.3f LSB cm %.2f mV; mean CM %.4f V"
                  % (s["hold"], s["ron_ohm"], s["f_hz"] / 1e3, s["err_lsb_max"], s["err_lsb_rms"],
                     s["lin_gain_err_db"], s["lin_delay_ps"], s["nonlin_resid_lsb_max"],
                     s["kick_diff_mv_max"], s["kick_cm_mv_max"], s["resid_diff_lsb_max"],
                     s["resid_cm_mv_max"], s["cm_mean_v"]))
        sw = c["swing"]
        print("  swing: full scale peak %.3f V diff, op-amp out %.3f..%.3f V, pins %.3f..%.3f V"
              % (sw["fs_diff_peak_v"], sw["fs_out_min_v"], sw["fs_out_max_v"], sw["fs_pin_min_v"], sw["fs_pin_max_v"]))
        print("  3x overdrive clips at %.3f V diff peak (%.2f dB above the 1 V span peak); pins %.3f..%.3f V "
              "(abs max %.2f V)" % (sw["clip_diff_peak_v"], 20 * math.log10(sw["clip_diff_peak_v"] / 1.0),
                                    sw["clip_pin_min_v"], sw["clip_pin_max_v"], lim["pin_absmax_v"]))
    print("== rx1 minus today, gain dB: " + ", ".join("%s Hz %+.3f" % kv for kv in res["delta_gain_db"].items()))


if __name__ == "__main__":
    sys.exit(main())
