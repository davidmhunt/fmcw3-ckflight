"""rx1-05 step 3: LTspice transient of the 1-RX power-up and power-down, and the CLK/PDWN steady state.

Runs in the fmcw3-sim image (LTspice under Wine, through spicelib), from the repo root:
    ./run --sim sh -c "xvfb-run -a python3 -u analysis/15_rx1_powerup/powerup_sim.py"
(xvfb-run must not be the container's PID 1, hence the `sh -c`, as in adc_input_sim.py.)
Options: --quick runs two cases only (debugging); --no-sweep skips the sweeps.
Writes analysis/15_rx1_powerup/sim/powerup.json (the report figures read it, so the report
rebuilds without the sim image) and prints a summary. It exits non-zero only when a sanity
check against a hand calculation fails; the design result (a pin above AVDD + 0.3 V, a rail out
of order) is reported, not asserted.

What is simulated (kicad-1rx netlist with the rx1-02 changes, runs/rx1-05/notes.md step 1):
  12 V source -> 51 uF -> U17 (1V0), U18 (3V8), U19 (5V6): LMR51420 behavioural bucks (the TI model is
     encrypted, tests/test_sim_smoke.py): start when 12 V passes the UVLO (3.89 typ / 4.5 V max
     rising, 3.58 / 3.35 falling, ti-lmr51420-datasheet p.5), reference ramp over tSS (3.2 to
     5.4 ms, p.5), 3.5 A high-side current limit (p.5), efficiency 0.9 (Figures 7-1, 7-2: assumption)
  U39 (3V0): the TI LP5907-3.0 PSpice model on file (ti-lp5907-3p0-pspice, snvmap8.zip), EN and VIN on
     3V8; its start-up time parameter ttrn is 80 or 150 us (ti-lp5907-datasheet p.6)
  U24 (3V3A), U23 (1V8), U25 (3V3D): LD39200 behavioural (ST publishes no model, parts/models_needed.csv):
     EN rising threshold 0.5 to 1.2 V and falling 0.5 V (st-ld39200-datasheet p.7), start-up
     td + tau exponential fitted to Figure 23 (p.13) by fit_ld39200(), scaled to the 0.1 / 0.3 ms
     fast / slow times of sequence.py, never above VIN - 0.25 V (dropout p.7), 3.5 A limit, no
     reverse current (p.9 section 6.5), PG open drain: low below 0.8 x VOUT, released above
     0.92 x VOUT (p.7), pulling low only while VIN >= VPGMIN. U24 EN and U23 EN on 3V0 through R993/
     R996 10k; U25 EN on the U23 PG, which R104 10k pulls up to 3V8.
  U45 (op amp stage C and D): LTspice LT6231 subcircuit (LTC2.lib) on 3V3A, bias /ADC_VCMB from
     R990/R991 1k/1k on 3V0 (C30 100n, C31 2.2u, C41 100n), the IF network of adc_input_sim.py,
     R97/R99 49.9 ohm, C163-C165 100 pF.
  U6 CLK: 3.3 V CMOS source on 3V3D with output resistance RO (20 ohm typ, microchip-pl133-37-datasheet
     p.2) through R15 33 ohm; PDWN: 3V3D pull-up of 90 to 330 uA (amd-ds181-artix7-datasheet p.3) through R992.
  AD9237 pins: capacitance (7 pF VIN, 2 pF CLK and PDWN, adi-ad9237-datasheet p.3, p.4) with clamp
     diodes to AVDD and AGND (Figures 4 and 7, p.10); AVDD's own load 45.5 mA (p.3, typ at 40 MSPS).
Assumptions (stated again in the writeup; each is swept below or is a datasheet corner):
  A1 clamp diode: Is and Rs (the sheet gives none): weak, typ, strong
  A2 LD39200: single exponential after a delay fitted to Figure 23; the sheet gives no min or max
  A3 U6 output resistance and its high level (the sheet gives no rail-to-rail figure)
  A4 Y2 start-up: the output is high from the first volt U6 can run on (worst case) or after the
     2 ms start-up time of ecs-txo-32csmv-datasheet p.1
  A5 constant-resistance loads at nominal voltage from analysis/12_rail_loads/sim/currents.json
  A6 PG pulls low once VIN is VPGMIN (the sheet states no PG behaviour below VIN 1.25 V)
  A7 the 12 V source rises in TR12 (not on file) and, at removal, is disconnected at once
  A8 the clock is held at its high level during the slow transients (the worst case for the pin
     voltage); the toggling clock is run only in the steady-state cases
  A9 U39 at 12 V removal: the TI model sinks current (its output is a voltage source that follows its
     reference to 0 V once VIN is below its 2.2 V threshold), a real LDO cannot. Case "ti" is the model
     as supplied; case "nosink" puts an ideal one-way element after it and the pass device's body
     diode (Is 1e-11, Rs 0.3 ohm, assumed) from OUT to IN. Both are run; the truth lies between.
Loads and caps are lumped per rail (CAP_UF, load_table()); the LD39200 and the bucks are one-way
current sources (no sinking), as their sheets state for reverse current (st-ld39200-datasheet p.9).
Each LTspice run is rerun when it stalls or diverges (run()), and uses method=gear.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = Path(os.environ.get("RX1_PU_WORK", "/tmp/rx1_powerup_sim"))
OUT = HERE / "sim" / "powerup.json"
PREFIX_BAKED = Path(os.environ.get("LTSPICE_PREFIX", "/opt/wineprefix"))
LT_DIR = PREFIX_BAKED / "drive_c/Program Files/ADI/LTspice"
FIG23 = HERE / "ld39200_fig23.csv"
LP5907_ZIP = ROOT / "datasheets/files/ti/snvmap8.zip"
CURRENTS = ROOT / "analysis/12_rail_loads/sim/currents.json"
ADC_IN = ROOT / "analysis/11_board_1rx/sim/adc_input.json"

# ---- datasheet numbers (manifest id, PDF page) ------------------------------------------------
TSS_MS = (3.2, 5.4)                  # LMR51420 soft start min / max (ti-lmr51420-datasheet p.5)
UVLO_RISE = (3.89, 4.5)              # typ, max (p.5)
UVLO_FALL = (3.58, 3.35)             # typ, min (p.5)
TON_US = (80.0, 150.0)               # LP5907 turn-on typ / max (ti-lp5907-datasheet p.6)
T90_LD_MS = (0.1, 0.3)               # LD39200 EN to 90 %, fast / slow (sequence.py; Figure 23 gives 0.18)
EN_VIL, EN_VIH = 0.5, 1.2            # LD39200 EN thresholds (st-ld39200-datasheet p.7)
PG_RISE, PG_FALL = 0.92, 0.80        # of VOUT (st-ld39200-datasheet p.7)
PG_RON = 0.4 / 6e-3                  # PG low 0.4 V max at 6 mA (p.7)
VDO = 0.25                           # LD39200 dropout max (p.7)
ILIM_BUCK = 3.5                      # LMR51420 high-side peak current limit typ (p.5)
ILIM_LDO = 3.5                       # LD39200 short-circuit current typ (p.7)
TOL_LD = 0.02                        # LD39200 output accuracy over temperature (st-ld39200-datasheet p.7)
TOL_LP = 0.02                        # LP5907 output voltage tolerance (ti-lp5907-datasheet p.5)
AVDD_NOM = 3.0                       # AD9237 AVDD (adi-ad9237-datasheet p.3)
IAVDD_RUN = 45.5e-3                  # IAVDD typ at 40 MSPS (p.3)
P_PDWN = 1e-3                        # power-down dissipation 1 mW (p.3)
C_VIN, C_LOGIC = 7e-12, 2e-12        # p.3 Table 1, p.4 Table 2
ABS_OVER = 0.3                       # abs max AVDD + 0.3 V, AGND - 0.3 V (p.7)
I_LOGIC_MAX = 10e-6                  # logic input current +/-10 uA (p.4): the reference for "clamp current"
IRPU = (90e-6, 330e-6)               # FPGA pad pull-up at VIN 0, VCCO 3.3 V (amd-ds181-artix7-datasheet p.3)
T_Y2_MS = 2.0                        # Y2 start-up (ecs-txo-32csmv-datasheet p.1)
U6_VDD_MIN = 1.62                    # PL133-37 minimum VDD (microchip-pl133-37-datasheet p.3)
RO_U6 = 20.0                         # typical CMOS output buffer impedance (p.2)
VCCO_VCCAUX_MAX = 2.625              # DS181 p.8
T_VCCO2VCCAUX_MS = 300.0             # at TJ 125 C (p.9)
RAMP_MS = (0.2, 50.0)                # TVCC* GND to 90 % limits (p.9 Table 7)
RS_IF = 1 / (1 / 49.9 + 1 / 120.0)   # mixer source per side (adc_input_sim.py)
F_IF = 200e3                         # top of the beat band
# lumped capacitance per rail, uF (runs/rx1-05/notes.md step 1, with C993-C995 of rx1-02)
CAP_UF = {"12V": 51.0, "3V8": 80.0, "5V6": 50.0, "1V0": 178.28, "3V0": 12.4, "3V3A": 10.87,
          "1V8": 68.75, "3V3D": 82.57}
NOM = {"12V": 12.0, "3V8": 3.809, "5V6": 5.6, "1V0": 1.008, "3V0": 3.0, "3V3A": 3.3, "1V8": 1.8, "3V3D": 3.3}
NODE = {"12V": "v12", "3V8": "v3v8", "5V6": "v5v6", "1V0": "v1v0", "3V0": "v3v0", "3V3A": "v3v3a",
        "1V8": "v1v8", "3V3D": "v3v3d"}
DIODES = {"weak": (1e-15, 10.0), "typ": (1e-14, 5.0), "strong": (1e-12, 2.0)}   # Is, Rs: A1
PINS = {"vinp": ("pinp", C_VIN), "vinn": ("pinn", C_VIN), "clk": ("clk", C_LOGIC), "pdwn": ("pdwn", C_LOGIC)}

T_OFF_MS = 14.0
T_STOP_MS = 44.0


# ---- the LD39200 start-up fit (step 5 tests it against the plot points) -----------------------
def read_fig23(path: Path = FIG23):
    rows = list(csv.DictReader(open(path)))
    return np.array([float(r["t_us"]) for r in rows]), np.array([float(r["vout_v"]) for r in rows])


def ramp_model(t_us, td_us, tau_us, vf=3.3):
    t = np.asarray(t_us, float)
    return np.where(t > td_us, vf * (1 - np.exp(-(t - td_us) / tau_us)), 0.0)


def fit_ld39200(t_us=None, v=None, vf=3.3):
    """Delay td and time constant tau of V = vf (1 - exp(-(t - td)/tau)) fitted to the points read from
    Figure 23 (st-ld39200-datasheet p.13; 3.7 V in, 3.3 V out, 100 mA, 10 uF, 200 us/div).
    Returns dict(td_us, tau_us, t90_us, rms_v, max_err_v)."""
    if t_us is None:
        t_us, v = read_fig23()
    best = None
    for td in np.arange(0.0, 60.0, 0.5):
        for tau in np.arange(10.0, 150.0, 0.5):
            e = ramp_model(t_us, td, tau, vf) - v
            r = float(np.sqrt(np.mean(e ** 2)))
            if best is None or r < best[0]:
                best = (r, td, tau, float(np.max(np.abs(e))))
    r, td, tau, mx = best
    return {"td_us": float(td), "tau_us": float(tau), "t90_us": float(td + tau * math.log(10)),
            "rms_v": r, "max_err_v": mx}


# ---- loads ------------------------------------------------------------------------------------
def load_table() -> dict:
    """Typical load current per rail, A (analysis/12_rail_loads/sim/currents.json, 1-RX rows)."""
    d = json.loads(CURRENTS.read_text())["boards"]["1rx"]["rows"]
    # U30 ICCINTQ 155 mA + ICCBRAMQ 4 mA (currents.json src, DS181 p.5, p.7) and the R32/R33 divider 6 uA
    out = {"1V0": 155e-3 + 4e-3 + 6e-6}

    def tot(pred):
        return sum(r["typ"] for r in d if r["typ"] is not None and pred(r)) * 1e-3

    out["1V8"] = tot(lambda r: r["path"][-1] == "U23")
    out["3V3A"] = tot(lambda r: r["path"][-1] == "U24" and r["ref"] != "U45")
    out["3V3D"] = tot(lambda r: r["path"][-1] == "U25")
    out["3V8"] = tot(lambda r: r["rail"] == "3V8" and r["path"][-1] in ("3V8", "U20") and r["ref"] != "R104")
    out["5V6"] = tot(lambda r: r["rail"] == "5V6")
    return out


# ---- netlist ----------------------------------------------------------------------------------
BUCK = """.subckt BUCK in out params: vset=3.81 tss=4m uvr=3.89 uvf=3.58 ilim=3.5 eff=0.9
Vone one 0 1
Suv one ena in 0 SWUV
Rg ena 0 1k
.model SWUV SW(Ron=1 Roff=1G Vt={(uvr+uvf)/2} Vh={(uvr-uvf)/2})
Cr r 0 1u
Rr r 0 100Meg
Bq 0 r I=limit((V(ena)-0.4)*10,0,1)*limit((1-V(r))*1000,0,1)*1u/{tss}-limit((0.6-V(ena))*10,0,1)*V(r)/1
Etgt tgt 0 VALUE={vset*min(V(r),1)}
Bo 0 so I=limit((V(tgt)-V(so))/50m,0,{ilim})
Vsn so out 0
Bin in 0 I=limit((V(ena)-0.4)*10,0,1)*V(out)*I(Vsn)/{eff}/max(V(in),1)
.ends
"""

LD39 = """.subckt LD39 in en out pg params: vnom=3.3 td=30u tau=55u von=1.2 voff=0.5 vdo=0.25 ilim=3.5 vpgmin=1.25 vinmin=1.25
Vone one 0 1
Sen one enb en 0 SWEN
Ren enb 0 1k
.model SWEN SW(Ron=1 Roff=1G Vt={(von+voff)/2} Vh={(von-voff)/2})
Bd d 0 V=delay(V(enb)*limit((V(in)-vinmin)*20,0,1),{td})
Rt d r {tau/1u}
Cr r 0 1u
Etgt tgt 0 VALUE={limit((V(in)-vinmin)*20,0,1)*min(vnom*V(r),max(V(in)-vdo,0))}
Bo in out I=limit((V(tgt)-V(out))/100m,0,{ilim})
Spg pg x 0 out SWPG
Spg2 x 0 in 0 SWV
.model SWPG SW(Ron=%g Roff=1G Vt={-0.86*vnom} Vh={0.06*vnom})
.model SWV SW(Ron=0.1 Roff=1G Vt={vpgmin} Vh=0.01)
.ends
""" % PG_RON


def lp5907_text(ton_us: float) -> str:
    """The TI model with its turn-on time parameter set (ttrn 80 us as shipped)."""
    with zipfile.ZipFile(LP5907_ZIP) as z:
        name = [n for n in z.namelist() if n.upper().endswith(".LIB")][0]
        txt = z.read(name).decode("latin1").replace("\r", "")
    txt = "".join(ch if ord(ch) < 128 else " " for ch in txt)
    assert "ttrn=80u" in txt
    return txt.replace("ttrn=80u", "ttrn=%gu" % ton_us)


def base_params(**kw) -> dict:
    p = dict(tss17=3.2, tss18=3.2, tss19=3.2, uvr=UVLO_RISE[0], uvf=UVLO_FALL[0], tr12=1.0, ton=80.0,
             ld_t90=T90_LD_MS[0], von=EN_VIL, vpgmin=1.25, if_amp=0.0, diode="typ", ro=RO_U6,
             ipu=IRPU[1], avdd_r=AVDD_NOM / IAVDD_RUN, ty2=0.0, y2_vstart=U6_VDD_MIN, load3d=1.0,
             t_off=T_OFF_MS, tstop=T_STOP_MS, maxstep_us=5.0, r15=33.0, rsh=0.0,
             c3v0_extra_uf=0.0, rbleed=0.0, c_en23_uf=0.0, sup1v0=False, rvin=49.9, u39="ti",
             opts="method=gear")      # gear: the default trapezoidal rule stalls on some corners (switch events)
    p.update(kw)
    return p


def pin_block(L, name, node, cpf, d):
    L += ["C%s %s 0 %gp" % (name, node, cpf * 1e12),
          "D%su %s v3v0 DCL" % (name, node), "D%sd 0 %s DCL" % (name, node)]


def netlist_transient(p: dict, loads: dict, fit: dict) -> tuple[str, list[str]]:
    k = p["ld_t90"] * 1e3 / fit["t90_us"]                     # scale the fitted ramp to the case time
    td, tau = fit["td_us"] * k, fit["tau_us"] * k
    is_, rs_ = DIODES[p["diode"]]
    cap = CAP_UF
    ld = lambda v, extra="": "PARAMS: vnom=%g td=%gu tau=%gu von=%g voff=%g vdo=%g ilim=%g vpgmin=%g %s" % (
        v, td, tau, p["von"], EN_VIL, VDO, ILIM_LDO, p["vpgmin"], extra)
    L = ["* rx1-05 step 3 power-up / power-down transient",
         BUCK, LD39, ".include lp5907.lib", ".lib LTC2.lib",
         "* 12 V: source, hot-plug ramp, disconnect at t_off, 51 uF",
         "Vs v12s 0 PWL(0 0 %gm 12)" % p["tr12"],
         "Rs12 v12s v12x 50m",
         "S12 v12x v12 toff 0 SW12",
         "Vtoff toff 0 PWL(0 1 %gm 1 %gm 0)" % (p["t_off"], p["t_off"] + 0.001),
         ".model SW12 SW(Ron=1m Roff=1G Vt=0.5 Vh=0.1)",
         "C12 v12 0 %gu" % cap["12V"], "Rl12 v12 0 1G",
         "XU17 v12 v1v0 BUCK PARAMS: vset=%g tss=%gm uvr=%g uvf=%g ilim=%g" % (NOM["1V0"], p["tss17"], p["uvr"], p["uvf"], ILIM_BUCK),
         "XU18 v12 v3v8 BUCK PARAMS: vset=%g tss=%gm uvr=%g uvf=%g ilim=%g" % (NOM["3V8"], p["tss18"], p["uvr"], p["uvf"], ILIM_BUCK),
         "XU19 v12 v5v6 BUCK PARAMS: vset=%g tss=%gm uvr=%g uvf=%g ilim=%g" % (NOM["5V6"], p["tss19"], p["uvr"], p["uvf"], ILIM_BUCK),
         "C1v0 v1v0 0 %gu" % cap["1V0"], "C3v8 v3v8 0 %gu" % cap["3V8"], "C5v6 v5v6 0 %gu" % cap["5V6"],
         "R1v0 v1v0 0 %g" % (NOM["1V0"] / loads["1V0"]),
         "R3v8 v3v8 0 %g" % (NOM["3V8"] / loads["3V8"]),
         "R5v6 v5v6 0 %g" % (NOM["5V6"] / loads["5V6"]),
         "* U39 (3V0): TI model, EN and VIN on 3V8",
         ] + (["XU39 v3v8 v3v8 v3v0 nc39 0 LP5907_3P0_TRANS"] if p["u39"] == "ti" else
              ["* U39 'nosink': the TI model drives v39i; a real LDO cannot sink current, and its pass device's",
               "* body diode takes the output down to 3V8 + Vf (BODY diode: Is, Rs assumed, A9)",
               "XU39 v3v8 v3v8 v39i nc39 0 LP5907_3P0_TRANS", "C39i v39i 0 1n",
               "Bidl v39i v3v0 I=max(0,V(v39i)-V(v3v0))/50m", "Dbody v3v0 v3v8 DBODY",
               ".model DBODY D(Is=1e-11 N=1 Rs=0.3 Cjo=0)"]) + [
         "C3v0 v3v0 0 %gu" % (cap["3V0"] + p["c3v0_extra_uf"]),
         "* U24 3V3A, U23 1V8: EN from 3V0 through R993 / R996; U25 3V3D: EN from the U23 PG, R104 to 3V8",
         "R993 v3v0 en24 10k", "R996 v3v0 en23 10k", "R104 v3v8 pg23 10k",
         "XU24 v3v8 en24 v3v3a pg24 LD39 " + ld(3.3 * 1.0),
         "XU23 v3v8 en23 v1v8 pg23 LD39 " + ld(1.8),
         "XU25 v3v8 pg23 v3v3d pg25 LD39 " + ld(3.3),
         "C3v3a v3v3a 0 %gu" % cap["3V3A"], "C1v8 v1v8 0 %gu" % cap["1V8"], "C3v3d v3v3d 0 %gu" % cap["3V3D"],
         "R3v3a v3v3a 0 %g" % (3.3 / loads["3V3A"]),
         "R1v8 v1v8 0 %g" % (1.8 / loads["1V8"]),
         "R3v3d v3v3d 0 %g" % (3.3 / (loads["3V3D"] * p["load3d"])),
         ] + (["* F2b: bleeder on 3V3D", "Rbleed v3v3d 0 %g" % p["rbleed"]] if p["rbleed"] else []) + \
        (["* F1b: capacitor on the U23 EN node", "Cen23 en23 0 %gu" % p["c_en23_uf"]] if p["c_en23_uf"] else []) + \
        (["* F1c: supervisor on 1V0, open drain pulls the U23 EN node low below 0.9 x 1V0 while its VDD (3V8) >= 1 V",
          "Ssup en23 sx 0 v1v0 SWSUP", "Ssup2 sx 0 v3v8 0 SWSV",
          ".model SWSUP SW(Ron=100 Roff=1G Vt=%g Vh=0.01)" % (-0.9 * NOM["1V0"]),
          ".model SWSV SW(Ron=0.1 Roff=1G Vt=1.0 Vh=0.01)"] if p["sup1v0"] else []) + \
        ["* AVDD (3V0) loads: AD9237 AVDD, MODE divider R91/R92, bias divider R990/R991",
         "Ravdd v3v0 0 %g" % p["avdd_r"],
         "R91 v3v0 mode 5.1k", "R92 mode 0 12k",
         "R990 v3v0 vcm 1k", "R991 vcm 0 1k", "C30 vcm 0 100n", "C31 vcm 0 2.2u", "C41 vcm 0 100n",
         "* 5V pull-up rail of the mixer IF outputs: U22 LD39200 from 5V6 (assumed instant, 0.25 V dropout)",
         "Bv5f v5f 0 V=min(max(V(v5v6)-%g,0),5)" % VDO,
         "* mixer IF source, network, U45 C and D, R97 / R99, C163-C165",
         "Bctl ctl 0 V=%g*sin(2*pi*%g*time)*min(V(v5f)/5,1)" % (p["if_amp"], F_IF),
         "Esp sp v5f ctl 0 0.5", "Esn sn v5f ctl 0 -0.5",
         "Rsp sp mp %.4f" % RS_IF, "Rsn sn mn %.4f" % RS_IF,
         "L14 mn fn 2.2u", "L15 mp fp 2.2u", "C36 fn fp 2.2n", "C37 fn an 10n", "C38 fp ap 10n",
         "R31 an invc 1k", "R38 ap invd 1k",
         "R39 invc outc 10k", "C39 invc outc 5p", "R40 invd outd 10k", "C40 invd outd 5p",
         "XU45C vcm invc outc v3v3a 0 LT6231", "XU45D vcm invd outd v3v3a 0 LT6231",
         "R97 outc pinn %g" % p["rvin"], "R99 outd pinp %g" % p["rvin"],
         "C163 pinn 0 100p", "C165 pinp 0 100p", "C164 pinn pinp 100p",
         "* AD9237 pins: capacitance and clamp diodes to AVDD (3V0) and AGND",
         ".model DCL D(Is=%g N=1 Rs=%g Cjo=0)" % (is_, rs_)]
    for nm, (node, cpf) in PINS.items():
        pin_block(L, nm, node, cpf, p["diode"])
    L += ["* CLK: U6 on 3V3D (held high while Y2 runs: A8), RO, R15 (+ optional shunt)",
          "Bf3d f3d 0 V=limit((V(v3v3d)-%g)*50,0,1)" % p["y2_vstart"],
          "Bosc osc 0 V=delay(V(f3d),%gm)*limit((V(v3v3d)-%g)*50,0,1)" % (p["ty2"], U6_VDD_MIN),
          "Bclks clks 0 V=V(v3v3d)*V(osc)",
          "Rou clks u6o %g" % p["ro"], "R15 u6o clk %g" % p["r15"]]
    if p["rsh"]:
        L.append("Rsh clk 0 %g" % p["rsh"])
    L += ["* PDWN: FPGA pad pull-up to 3V3D (3.3 V / I at VIN 0), then R992 10k",
          "Rpu v3v3d pds %g" % (3.3 / p["ipu"]), "R992 pds pdwn 10k"]
    save = (".save V(v12) V(v3v8) V(v5v6) V(v1v0) V(v3v0) V(v3v3a) V(v1v8) V(v3v3d) V(pg23) V(pinp) V(pinn) "
            "V(clk) V(pdwn) V(outc) V(outd) V(vcm) V(en23) V(en24) "
            + " ".join("I(D%s%s)" % (n, s) for n in PINS for s in ("u", "d")))
    L += [".options plotwinsize=0 gmin=1e-12 abstol=1e-10 " + p["opts"], save,
          ".tran 0 %gm 0 %gus" % (p["tstop"], p["maxstep_us"]), ".end", ""]
    return "\n".join(L), []


def netlist_steady(v3d: float, v3v0: float, kind: str, r15: float = 33.0, rsh: float = 0.0, ro: float = RO_U6,
                   diode: str = "typ", avdd_r: float = AVDD_NOM / IAVDD_RUN, ipu: float = IRPU[1]) -> str:
    """CLK toggling or PDWN high, every supply at a DC value."""
    is_, rs_ = DIODES[diode]
    L = ["* rx1-05 step 3 steady state, %s" % kind,
         "V3V0 v3v0 0 %g" % v3v0, "Ravdd v3v0 0 %g" % avdd_r, "V3D v3d 0 %g" % v3d,
         ".model DCL D(Is=%g N=1 Rs=%g Cjo=0)" % (is_, rs_)]
    pin_block(L, "clk", "clk", C_LOGIC, diode)
    pin_block(L, "pdwn", "pdwn", C_LOGIC, diode)
    if kind == "clk":
        L += ["Vpls pls 0 PULSE(0 1 0 1n 1n 11.5n 25n)", "Bclks clks 0 V=V(v3d)*V(pls)",
              "Rou clks u6o %g" % ro, "R15 u6o clk %g" % r15]
        if rsh:
            L.append("Rsh clk 0 %g" % rsh)
        L += ["Rp pdsrc 0 1G", "R992 pdsrc pdwn 10k"]
    else:   # PDWN high from the FPGA pad (3V3D) through R992 or the pull-up (3.3 V / IRPU) through R992
        L += ["Rpu v3d pds %g" % (3.3 / ipu), "R992 pds pdwn 10k", "Rc clk 0 1G"]
    L += [".save V(clk) V(pdwn) I(Dclku) I(Dclkd) I(Dpdwnu) I(Dpdwnd) V(v3v0)",
          ".options plotwinsize=0 gmin=1e-12", ".tran 0 1.2u 0.2u 0.05n", ".end", ""]
    return "\n".join(L)


# ---- running ----------------------------------------------------------------------------------
def setup_wine():
    pre = WORK / "wineprefix"
    pre.mkdir(parents=True, exist_ok=True)
    for q in list(PREFIX_BAKED.iterdir()):
        link = pre / q.name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(q)
    os.environ.update(WINEPREFIX=str(pre), WINEDEBUG="-all", USER="root",
                      LTSPICEFOLDER=str(LT_DIR), LTSPICEEXECUTABLE="LTspice.exe")


_RUN = {"n": 0}


def run(text: str, tag: str, ton_us: float = 80.0):
    from spicelib import RawRead, SimRunner
    from spicelib.simulators.ltspice_simulator import LTspice
    _RUN["n"] += 1
    d = WORK / tag
    d.mkdir(parents=True, exist_ok=True)
    (WORK / "src").mkdir(exist_ok=True)
    (d / "lp5907.lib").write_text(lp5907_text(ton_us))
    (WORK / "src" / "lp5907.lib").write_text(lp5907_text(ton_us))
    net = WORK / "src" / (tag + ".net")
    net.write_text(text)
    runner = SimRunner(output_folder=str(d), simulator=LTspice)
    # LTspice under Wine sometimes stalls or diverges on a corner, differently from run to run: a run that
    # does not finish (the log lacks "Total elapsed time") or whose voltages leave +/-100 V is rerun, the
    # later attempts with other tolerances.
    extra = ("", "", ".options reltol=0.003", ".options abstol=1e-9 vntol=1e-5")
    log = ""
    for attempt, opt in enumerate(extra):
        net.write_text(text.replace(".tran", opt + "\n.tran") if opt and text.count(".tran") == 1 else text)
        main = d / (tag + ".raw")
        if main.exists():
            main.unlink()
        rawf, logf = runner.run_now(str(net), run_filename=tag + ".net", timeout=150)   # a finished run takes 1 to 40 s
        log = Path(logf).read_text(errors="replace") if logf and Path(logf).exists() else ""
        if main.exists() and "Total elapsed time" in log:
            try:
                raw = RawRead(str(main))
                big = max(float(np.abs(np.real(np.asarray(raw.get_trace(n).get_wave(0)))).max())
                          for n in raw.get_trace_names() if n.upper().startswith("V(") and "(" in n)
            except Exception:           # noqa: BLE001 - unreadable raw file counts as a failed attempt
                continue
            if big < 100.0:
                _RUN["retries"] = _RUN.get("retries", 0) + attempt
                return raw, log
    raise RuntimeError("simulation %s did not finish; log: %s" % (tag, log[-1500:]))


def wave(raw, name):
    names = {n.lower(): n for n in raw.get_trace_names()}
    return np.real(np.asarray(raw.get_trace(names[name.lower()]).get_wave(0)))


def time_axis(raw):
    return np.abs(np.real(wave(raw, raw.get_trace_names()[0])))


# ---- measurements -----------------------------------------------------------------------------
def first_cross(t, y, thr, rising=True, t0=0.0):
    m = t >= t0
    tt, yy = t[m], y[m]
    idx = np.nonzero(yy >= thr)[0] if rising else np.nonzero(yy <= thr)[0]
    if not len(idx):
        return None
    i = idx[0]
    if i == 0:
        return float(tt[0])
    y0, y1 = yy[i - 1], yy[i]
    return float(tt[i - 1] + (tt[i] - tt[i - 1]) * (thr - y0) / (y1 - y0)) if y1 != y0 else float(tt[i])


def pin_metrics(t, v, avdd, iu, idn, t_off):
    out = {}
    for ph, m in (("up", t < t_off), ("down", t >= t_off), ("all", np.ones_like(t, bool))):
        tt, vv, aa = t[m], v[m], avdd[m]
        over = vv - (aa + ABS_OVER)
        i_pk_u, i_pk_d = float(iu[m].max()), float(idn[m].max())
        ia = np.maximum(iu[m], idn[m])
        dt = np.diff(tt, prepend=tt[0])
        k = int(np.argmax(over))
        out[ph] = {
            "peak_v": float(vv.max()), "min_v": float(vv.min()),
            "over_max_v": float(over.max()), "t_over_max_ms": float(tt[k] * 1e3),
            "v_at_over_max": float(vv[k]), "avdd_at_over_max": float(aa[k]),
            "t_over_us": float(dt[over > 0].sum() * 1e6),
            "under_min_v": float(vv.min() + ABS_OVER),         # AGND - 0.3 V is the floor; negative = violation
            "i_clamp_up_peak_ma": i_pk_u * 1e3, "i_clamp_dn_peak_ma": i_pk_d * 1e3,
            "t_above_10ua_us": float(dt[ia > I_LOGIC_MAX].sum() * 1e6),
            "q_clamp_nc": float((ia * dt).sum() * 1e9),
        }
    return out


def rail_times(t, w):
    """Start (10 %) and end (90 %) of each rail's rise, and its fall through 90 % and 10 % after t_off."""
    res = {}
    for r, node in NODE.items():
        y = w[node]
        v = NOM[r]
        res[r] = {"t_start_ms": _ms(first_cross(t, y, 0.1 * v)), "t_up90_ms": _ms(first_cross(t, y, 0.9 * v)),
                  "peak_v": float(y.max())}
    return res


def fall_times(t, w, t_off):
    res = {}
    for r, node in NODE.items():
        y = w[node]
        v = NOM[r]
        res[r] = {"t_fall90_ms": _ms(first_cross(t, y, 0.9 * v, False, t_off)),
                  "t_fall10_ms": _ms(first_cross(t, y, 0.1 * v, False, t_off))}
    return res


def _ms(x):
    return None if x is None else x * 1e3


def vcco_minus_vcco_aux(t, w, t_off):
    d = w["v3v3d"] - w["v1v8"]
    dt = np.diff(t, prepend=t[0])
    over = d > VCCO_VCCAUX_MAX
    up, dn = t < t_off, t >= t_off
    return {"max_v": float(d.max()), "t_over_up_ms": float(dt[over & up].sum() * 1e3),
            "t_over_down_ms": float(dt[over & dn].sum() * 1e3),
            "max_v_up": float(d[up].max()), "max_v_down": float(d[dn].max())}


def window(t, y, t0, t1, n=400):
    g = np.linspace(t0, t1, n)
    return np.interp(g, t, y)


def case_result(name, p, loads, fit, save_traces):
    text, _ = netlist_transient(p, loads, fit)
    raw, log = run(text, name, ton_us=p["ton"])
    t = time_axis(raw)
    w = {n: wave(raw, "V(%s)" % n) for n in ("v12", "v3v8", "v5v6", "v1v0", "v3v0", "v3v3a", "v1v8", "v3v3d",
                                           "pg23", "pinp", "pinn", "clk", "pdwn", "outc", "outd", "vcm", "en23", "en24")}
    cur = {}
    for n in PINS:
        cur[n] = (wave(raw, "I(D%su)" % n), wave(raw, "I(D%sd)" % n))
    t_off = p["t_off"] * 1e-3
    pins = {n: pin_metrics(t, w[{"vinp": "pinp", "vinn": "pinn", "clk": "clk", "pdwn": "pdwn"}[n]], w["v3v0"],
                           cur[n][0], cur[n][1], t_off) for n in PINS}
    rails = rail_times(t, w)
    falls = fall_times(t, w, t_off)
    en_t = first_cross(t, w["v3v0"], p["von"])
    start_ok = {r: (rails[r]["t_start_ms"] is not None and en_t is not None and rails[r]["t_start_ms"] >= en_t * 1e3 - 1e-3)
                for r in ("3V3A", "1V8", "3V3D")}
    res = {"params": p, "rails": rails, "falls": falls, "pins": pins, "t_3v0_en_ms": _ms(en_t),
           "start_after_3v0_en": start_ok, "vcco_minus_vccaux": vcco_minus_vcco_aux(t, w, t_off),
           "log_warn": bool(re.search(r"timestep too small|singular matrix", log, re.I))}
    if save_traces:
        res["traces"] = {
            "up_ms": np.linspace(0, p["t_off"] - 1, 500).round(4).tolist(),
            "down_ms": np.linspace(p["t_off"] - 0.5, p["tstop"], 500).round(4).tolist()}
        for ph, (t0, t1) in (("up", (0, p["t_off"] - 1)), ("down", (p["t_off"] - 0.5, p["tstop"]))):
            res["traces"][ph] = {n: window(t * 1e3, y, t0, t1).round(4).tolist() for n, y in w.items()
                                 if n in ("v12", "v3v8", "v5v6", "v1v0", "v3v0", "v3v3a", "v1v8", "v3v3d", "pinp", "pinn",
                                          "clk", "pdwn", "pg23")}
            for n in PINS:
                res["traces"][ph]["i_" + n] = window(t * 1e3, np.maximum(cur[n][0], cur[n][1]) * 1e3, t0, t1).round(5).tolist()
    return res


def steady_result(tag, v3d, v3v0, kind, **kw):
    raw, _ = run(netlist_steady(v3d, v3v0, kind, **kw), tag)
    t = time_axis(raw)
    res = {"v3d": v3d, "v3v0": v3v0, "kind": kind, **{k: v for k, v in kw.items()}}
    for pin in ("clk", "pdwn"):
        v = wave(raw, "V(%s)" % pin)
        iu = wave(raw, "I(D%su)" % pin)
        idn = wave(raw, "I(D%sd)" % pin)
        res[pin] = {"peak_v": float(v.max()), "min_v": float(v.min()), "limit_v": v3v0 + ABS_OVER,
                    "over_v": float(v.max() - (v3v0 + ABS_OVER)),
                    "i_clamp_up_peak_ma": float(iu.max() * 1e3), "i_clamp_up_mean_ua": float(iu.mean() * 1e6),
                    "i_clamp_dn_peak_ma": float(idn.max() * 1e3)}
        if pin == "clk" and kind == "clk":
            thr = 1.4                                  # mid of VIL 0.8 V and VIH 2.0 V (adi-ad9237-datasheet p.4)
            hi = v > thr
            rises = np.nonzero(~hi[:-1] & hi[1:])[0]
            falls_ = np.nonzero(hi[:-1] & ~hi[1:])[0]
            period = 25e-9
            res[pin]["duty"] = float(hi.mean())
            lo_v, hi_v = float(np.percentile(v, 5)), float(np.percentile(v, 95))
            tr = []
            for i in rises:
                a, b = lo_v + 0.1 * (hi_v - lo_v), lo_v + 0.9 * (hi_v - lo_v)
                j0 = max(i - 40, 0)
                ta, tb = first_cross(t[j0:i + 40], v[j0:i + 40], a), first_cross(t[j0:i + 40], v[j0:i + 40], b)
                if ta is not None and tb is not None:
                    tr.append(tb - ta)
            res[pin]["rise_10_90_ns"] = float(np.median(tr) * 1e9) if tr else None
            res[pin]["n_edges"] = int(len(rises))
            res[pin]["period_ns"] = period * 1e9
    return res


def order_checks(cases: dict) -> dict:
    """Each ordering of sequence.py (ORDERS) against the simulation: later rail's 90 % time minus the earlier
    rail's (power-up) or the earlier-off rail's 90 % fall time minus the later-off rail's (power-down), over
    the corners of `cases` (name -> result). Positive means the order holds. Also the ramp time of each FPGA rail
    (10 % to 90 % scaled to GND to 90 %) against 0.2 to 50 ms (amd-ds181-artix7-datasheet p.9 Table 7)."""
    sys.path.insert(0, str(HERE))
    import sequence as S
    seq = {r["id"]: r for r in csv.DictReader(open(HERE / "sequence.csv"))}
    out = {"rows": {}, "ramps": {}}
    for oid, d, e, l, why, src in S.ORDERS:
        ms = {}
        for k, c in cases.items():
            if d == "on":
                te, tl = c["rails"][e]["t_up90_ms"], c["rails"][l]["t_up90_ms"]
                if e == l:
                    continue
                ms[k] = None if te is None or tl is None else tl - te
            else:   # power-off: e must fall first, l later
                te, tl = c["falls"][e]["t_fall90_ms"], c["falls"][l]["t_fall90_ms"]
                ms[k] = None if te is None or tl is None else tl - te
                # a rail that never falls below 10 % within the run is "later"
        if not ms:
            out["rows"][oid] = {"direction": d, "same_rail": True}
            continue
        vals = [v for v in ms.values() if v is not None]
        worst = min(vals) if vals else None
        out["rows"][oid] = {"direction": d, "worst_ms": worst, "best_ms": max(vals) if vals else None,
                            "worst_case": min((k for k, v in ms.items() if v is not None), key=lambda k: ms[k]) if vals else None,
                            "holds_all_corners": bool(vals) and worst > 0,
                            "class_rx1": seq[oid]["class_rx1"], "csv_worst_ms": seq[oid]["margin_worst_ms"],
                            "csv_best_ms": seq[oid]["margin_best_ms"], "per_case_ms": ms}
    for r in ("1V0", "1V8", "3V3D"):
        ramps = []
        for c in cases.values():
            t = c["rails"][r]
            if t["t_start_ms"] is not None and t["t_up90_ms"] is not None:
                ramps.append((t["t_up90_ms"] - t["t_start_ms"]) / 0.8)
        out["ramps"][r] = {"min_ms": min(ramps), "max_ms": max(ramps),
                           "within": bool(min(ramps) >= RAMP_MS[0] and max(ramps) <= RAMP_MS[1])}
    return out


# ---- driver -----------------------------------------------------------------------------------
def power_cases():
    """Eight corners: U17 and U18 soft start fast / slow, the LDOs fast / slow. Fast = the earliest start
    of each stage (UVLO 3.89 V, EN 0.5 V, LP5907 80 us, LD39200 0.1 ms); slow = the latest."""
    cases = []
    for s17 in (0, 1):
        for s18 in (0, 1):
            for l in (0, 1):
                nm = "u17%s_u18%s_ldo%s" % ("fs"[s17], "fs"[s18], "fs"[l])
                cases.append((nm, dict(tss17=TSS_MS[s17], tss18=TSS_MS[s18], tss19=TSS_MS[s18],
                                       uvr=UVLO_RISE[l], uvf=UVLO_FALL[l], ton=TON_US[l], ld_t90=T90_LD_MS[l],
                                       von=(EN_VIL, EN_VIH)[l])))
    return cases


def summarise_case(c):
    pins = c["pins"]
    r = c["rails"]
    worst = max(("vinp", "vinn", "clk", "pdwn"), key=lambda n: pins[n]["all"]["over_max_v"])
    return worst, pins[worst]["all"]["over_max_v"]


def main() -> int:
    quick = "--quick" in sys.argv
    sweep = "--no-sweep" not in sys.argv
    setup_wine()
    WORK.mkdir(parents=True, exist_ok=True)
    fit = fit_ld39200()
    loads = load_table()
    adc = json.loads(ADC_IN.read_text())["cases"]["rx1"]
    amp_fs = 1.0 / 10 ** (adc["gain_db_at"]["200000"] / 20)         # 1 V peak differential at the pins (2 V p-p span)
    res = {"source": "analysis/15_rx1_powerup/powerup_sim.py", "fit": fit, "loads_a": loads, "if_amp_fs_v": amp_fs,
           "diodes": {k: {"Is": v[0], "Rs": v[1]} for k, v in DIODES.items()}, "cases": {}, "sweeps": {},
           "steady": {}, "checks": []}
    cases = power_cases()
    if quick:
        cases = [c for c in cases if c[0] in ("u17f_u18f_ldof", "u17s_u18s_ldos")]
    for nm, kw in cases:
        for ifn, amp in (("if0", 0.0), ("iffs", amp_fs)):
            tag = "%s_%s" % (nm, ifn)
            p = base_params(**kw, if_amp=amp, maxstep_us=(0.4 if amp else 5.0))
            c = case_result(tag, p, loads, fit, save_traces=True)
            res["cases"][tag] = c
            w, v = summarise_case(c)
            up = max(c["pins"][n]["up"]["over_max_v"] for n in PINS)
            dn = {n: c["pins"][n]["down"]["over_max_v"] for n in PINS}
            print("%-24s over AVDD+0.3: power-up %+.3f V, power-down vinp %+.3f clk %+.3f pdwn %+.3f | t90 ms 3V0 %.2f "
                  "3V3A %.2f 1V8 %.2f 3V3D %.2f 1V0 %.2f | start after 3V0 EN %s"
                  % (tag, up, dn["vinp"], dn["clk"], dn["pdwn"],
                     *(c["rails"][r]["t_up90_ms"] or float("nan") for r in ("3V0", "3V3A", "1V8", "3V3D", "1V0")),
                     c["start_after_3v0_en"]), flush=True)
    for ifn in ("if0", "iffs"):
        sub = {k: v for k, v in res["cases"].items() if k.endswith("_" + ifn)}
        res.setdefault("order", {})[ifn] = order_checks(sub)
    for oid, r in res["order"]["iffs"]["rows"].items():
        if r.get("same_rail"):
            continue
        print("order %-22s %-4s worst %+.2f ms best %+.2f ms in %s (sequence.csv %s .. %s, %s)" % (
            oid, r["direction"], r["worst_ms"], r["best_ms"], r["worst_case"], r["csv_worst_ms"], r["csv_best_ms"],
            r["class_rx1"]), flush=True)
    # the worst corner by pin over-limit, then the sweeps on it
    worst_tag = max((k for k in res["cases"] if k.endswith("_iffs")), key=lambda k: max(res["cases"][k]["pins"][n]["all"]["over_max_v"] for n in PINS))
    res["worst_case"] = worst_tag
    wk = res["cases"][worst_tag]["params"]
    print("worst corner: %s" % worst_tag, flush=True)
    if sweep and not quick:
        sw = {}
        variants = [("diode", d, dict(diode=d)) for d in DIODES] + \
                   [("ro", r, dict(ro=r)) for r in (10.0, 20.0, 40.0)] + \
                   [("pdwn_ipu_ua", i * 1e6, dict(ipu=i)) for i in IRPU] + \
                   [("vpgmin", v, dict(vpgmin=v)) for v in (1.25, 2.0, 2.8)] + \
                   [("y2", y, dict(ty2=T_Y2_MS if y else 0.0, y2_vstart=2.97 if y else U6_VDD_MIN)) for y in (0, 1)] + \
                   [("avdd_r", r, dict(avdd_r=r)) for r in (AVDD_NOM / IAVDD_RUN, AVDD_NOM ** 2 / P_PDWN)] + \
                   [("load3d", s, dict(load3d=s)) for s in (1.0, 0.25)] + \
                   [("tr12_ms", t, dict(tr12=t)) for t in (0.1, 1.0, 5.0)] + \
                   [("u39", m, dict(u39=m)) for m in ("ti", "nosink")]
        for key, val, kw in variants:
            p = dict(wk)
            p.update(kw)
            tag = "sw_%s_%s" % (key, str(val).replace(".", "p"))
            c = case_result(tag, p, loads, fit, save_traces=False)
            w, v = summarise_case(c)
            sw.setdefault(key, []).append({"value": val, "result": c})
            print("sweep %-12s %-8s worst pin %s over %+.3f V (power-up %+.3f); clk peak %.1f mA, vinp %.2f mA, pdwn %.2f mA; "
                  "3V3D starts %.2f ms, 3V0 EN at %.2f ms, start after 3V0 %s"
                  % (key, val, w, v, max(c["pins"][n]["up"]["over_max_v"] for n in PINS),
                     c["pins"]["clk"]["all"]["i_clamp_up_peak_ma"], c["pins"]["vinp"]["all"]["i_clamp_up_peak_ma"],
                     c["pins"]["pdwn"]["all"]["i_clamp_up_peak_ma"], c["rails"]["3V3D"]["t_start_ms"] or float("nan"),
                     c["t_3v0_en_ms"] or float("nan"), c["start_after_3v0_en"]), flush=True)
        res["sweeps"] = sw
    # the proposed fixes of fixes.csv that act on what this run measures, on every corner (IF at full scale)
    if sweep and not quick:
        fixes = {}
        two = [c for c in cases if c[0] in ("u17f_u18f_ldof", "u17s_u18s_ldos")]   # the power-down side hardly depends on the soft starts
        specs = [("no fix", dict(), two, ("ti", "nosink")),
                 ("F2a +10u on 3V0", dict(c3v0_extra_uf=10.0), two, ("ti", "nosink")),
                 ("F2a +47u on 3V0", dict(c3v0_extra_uf=47.0), two, ("ti", "nosink")),
                 ("F2a +100u on 3V0", dict(c3v0_extra_uf=100.0), two, ("ti", "nosink")),
                 ("F2a +220u on 3V0", dict(c3v0_extra_uf=220.0), two, ("ti", "nosink")),
                 ("F2b bleeder 330 on 3V3D", dict(rbleed=330.0), two, ("ti", "nosink")),
                 ("F2b bleeder 100 on 3V3D", dict(rbleed=100.0), two, ("ti", "nosink")),
                 ("F2a+F2b", dict(c3v0_extra_uf=10.0, rbleed=330.0), two, ("ti", "nosink")),
                 ("F3 R97/R99 200 ohm", dict(rvin=200.0), two, ("ti", "nosink")),
                 ("F3 R97/R99 499 ohm", dict(rvin=499.0), two, ("ti", "nosink")),
                 # R996 10k with C on the EN node: tau = 10 ms per uF, so the run is longer (IF at zero)
                 ("F1b 1u on U23 EN", dict(c_en23_uf=1.0, t_off=24.0, tstop=54.0), cases, ("ti",)),
                 ("F1b 2.2u on U23 EN", dict(c_en23_uf=2.2, t_off=40.0, tstop=70.0), cases, ("ti",)),
                 ("F1b 4.7u on U23 EN", dict(c_en23_uf=4.7, t_off=80.0, tstop=110.0), cases, ("ti",)),
                 ("F1c supervisor on 1V0", dict(sup1v0=True), cases, ("ti",))]
        for fname0, fkw, corners, modes in specs:
            for mode in modes:
                fname = "%s [U39 %s]" % (fname0, mode)
                fixes[fname] = {}
                for nm, kw in corners:
                    long_run = "t_off" in fkw
                    p = base_params(**kw, if_amp=0.0 if long_run else amp_fs, maxstep_us=5.0 if long_run else 0.4,
                                    u39=mode, **fkw)
                    c = case_result("fx_%s_%s_%s" % (re.sub(r"\W+", "_", fname0), mode, nm), p, loads, fit, save_traces=False)
                    fixes[fname][nm] = c
                worst_ = {ph: max(max(c["pins"][n][ph]["over_max_v"] for n in PINS) for c in fixes[fname].values())
                          for ph in ("up", "down")}
                pk = {n: max(c["pins"][n]["all"]["i_clamp_up_peak_ma"] for c in fixes[fname].values()) for n in PINS}
                res.setdefault("fix_order", {})[fname] = order_checks(fixes[fname])
                fo = res["fix_order"][fname]["rows"]
                print("fix %-38s over AVDD+0.3: power-up %+.3f V, power-down %+.3f V; peak clamp mA vinp %.1f clk %.1f | "
                      "worst margin ms 1V0<1V8 %+.2f, 1V0<3V3D %+.2f, 3V3D off<3V0 off %+.2f, 3V3A off<3V0 off %+.2f" % (
                          fname, worst_["up"], worst_["down"], pk["vinp"], pk["clk"], fo["on-VCCINT-VCCAUX"]["worst_ms"],
                          fo["on-VCCINT-VCCO"]["worst_ms"], fo["off-3V3D-3V0"]["worst_ms"], fo["off-3V3A-3V0"]["worst_ms"]), flush=True)
        res["fixes"] = fixes
    # steady state at the tolerance limits (LD39200 and LP5907 +/-2 %, and +/-5 % as a system margin)
    if not quick:
        st = {}
        for lab, tol in (("2pct", 0.02), ("5pct", 0.05)):
            for cn, (d, a) in {"nominal": (3.3, 3.0), "3V3D high, 3V0 low": (3.3 * (1 + tol), 3.0 * (1 - tol)),
                               "3V3D low, 3V0 high": (3.3 * (1 - tol), 3.0 * (1 + tol))}.items():
                st["%s %s clk" % (lab, cn)] = steady_result("ss_%s_%s_clk" % (lab, cn.split(",")[0].replace(" ", "")), d, a, "clk")
                st["%s %s pdwn" % (lab, cn)] = steady_result("ss_%s_%s_pdwn" % (lab, cn.split(",")[0].replace(" ", "")), d, a, "pdwn")
        # CLK fixes at the worst tolerance corner (rerun of edge and duty at 40 MHz)
        d, a = 3.3 * 1.02, 3.0 * 0.98
        fx = {}
        for nm, kw in {"today R15 33": dict(), "R15 100": dict(r15=100.0), "R15 68 + 680 shunt": dict(r15=68.0, rsh=680.0),
                       "R15 33 + 330 shunt": dict(r15=33.0, rsh=330.0)}.items():
            fx[nm] = steady_result("fix_" + nm.replace(" ", "_").replace("+", "p"), d, a, "clk", **kw)
        for nm, kw in {"R15 68 + 680 shunt": dict(r15=68.0, rsh=680.0)}.items():
            fx[nm + " @5pct"] = steady_result("fix5_" + nm.replace(" ", "_").replace("+", "p"), 3.3 * 1.05, 3.0 * 0.95, "clk", **kw)
        res["steady"] = st
        res["clk_fixes"] = fx
    # sanity checks against hand calculations
    chk = []
    f = res["fit"]
    chk.append(("LD39200 fit reproduces Figure 23 within 0.15 V rms (%.3f)" % f["rms_v"], f["rms_v"] < 0.15))
    for tag, c in res["cases"].items():
        r = c["rails"]
        chk.append(("%s: 3V8 settles at its set voltage (%.3f V)" % (tag, r["3V8"]["peak_v"]), abs(r["3V8"]["peak_v"] - NOM["3V8"]) < 0.25))
        chk.append(("%s: 3V0 within LP5907 +/-3 %% (%.3f V)" % (tag, r["3V0"]["peak_v"]), abs(r["3V0"]["peak_v"] - 3.0) < 0.2))
        chk.append(("%s: no simulator timestep or matrix warning" % tag, not c["log_warn"]))
    res["checks"] = [{"what": w_, "ok": bool(ok)} for w_, ok in chk]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=0, default=float))
    bad = [w_ for w_, ok in chk if not ok]
    for w_, ok in chk:
        print("CHECK %s %s" % ("PASS" if ok else "FAIL", w_))
    print("wrote %s (%d LTspice runs, %d reruns)" % (OUT.relative_to(ROOT), _RUN["n"], _RUN.get("retries", 0)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
