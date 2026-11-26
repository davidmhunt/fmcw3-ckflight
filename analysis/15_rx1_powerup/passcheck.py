"""rx1-05 step 4/5: the pass check on waveforms, apart from the simulator.

Each function takes time (s) and voltage (V) arrays, so tests/test_rx1_powerup.py can run it on fixture
waveforms and a report can run it on the traces of sim/powerup.json (time in ms there: scale first).
The limits come from the datasheets (manifest id and page in each docstring); none is set here.
"""
from __future__ import annotations

import numpy as np

ABS_OVER_V = 0.3                    # AGND - 0.3 V to AVDD + 0.3 V (adi-ad9237-datasheet p.7)
EN_VIH_V = 1.2                      # LD39200 EN high threshold (st-ld39200-datasheet p.7)
VCCO_VCCAUX_MAX_V = 2.625           # amd-ds181-artix7-datasheet p.8
T_VCCO2VCCAUX_S = 0.300             # at TJ 125 C, the shortest of 300/500/800 ms (p.9)
UP_FRACTION = 0.9                   # a rail is "up" at 90 % of nominal (p.9)


def first_cross(t, y, thr, rising=True, t0=0.0):
    """Time of the first crossing of thr at or after t0, linearly interpolated; None if there is none."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    m = t >= t0
    tt, yy = t[m], y[m]
    idx = np.nonzero(yy >= thr)[0] if rising else np.nonzero(yy <= thr)[0]
    if not len(idx):
        return None
    i = int(idx[0])
    if i == 0:
        return float(tt[0])
    y0, y1 = yy[i - 1], yy[i]
    return float(tt[i - 1] + (tt[i] - tt[i - 1]) * (thr - y0) / (y1 - y0)) if y1 != y0 else float(tt[i])


def pin_check(t, v_pin, v_avdd, over=ABS_OVER_V):
    """A pin passes when it stays within AGND - over and AVDD + over at every instant."""
    v, a = np.asarray(v_pin, float), np.asarray(v_avdd, float)
    over_max = float((v - (a + over)).max())
    under_min = float((v + over).min())          # negative: below AGND - 0.3 V
    return {"ok": bool(over_max <= 0.0 and under_min >= 0.0), "over_max_v": over_max, "under_min_v": under_min}


def start_check(t, v3v0, starts, en_thr=EN_VIH_V):
    """3V3A, 1V8 and 3V3D (`starts`: rail -> start time in s, None if never) start only after 3V0 passes the
    EN threshold. A rail that never starts passes (nothing is on)."""
    t_en = first_cross(t, v3v0, en_thr)
    res = {}
    for r, ts in starts.items():
        res[r] = ts is None or (t_en is not None and ts >= t_en)
    return {"ok": all(res.values()), "t_en_s": t_en, "per_rail": res}


def order_check(t, rails, nominal, order):
    """Power-up order: `order` lists rail names, each to reach 90 % of its nominal no earlier than the one
    before it. A rail that never reaches 90 % while a later one does is a failure."""
    t90 = {r: first_cross(t, rails[r], UP_FRACTION * nominal[r]) for r in order}
    bad = []
    for a, b in zip(order, order[1:]):
        if t90[b] is None:
            continue
        if t90[a] is None or t90[b] < t90[a]:
            bad.append((a, b))
    return {"ok": not bad, "t90_s": t90, "out_of_order": bad}


def vcco_vccaux_check(t, vcco, vccaux, limit_v=VCCO_VCCAUX_MAX_V, max_s=T_VCCO2VCCAUX_S):
    """VCCO - VCCAUX above limit_v for longer than max_s in total (per power cycle) fails."""
    t = np.asarray(t, float)
    d = np.asarray(vcco, float) - np.asarray(vccaux, float)
    dt = np.diff(t, prepend=t[0])
    above = float(dt[d > limit_v].sum())
    return {"ok": above <= max_s, "max_v": float(d.max()), "t_above_s": above}
