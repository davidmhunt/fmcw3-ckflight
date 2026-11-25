"""rx1-05 step 2: the order map. Which rail must come before which, and what forces it.

Run: ./run --native python3 analysis/15_rx1_powerup/sequence.py   (writes sequence.csv, fixes.csv)

The kicad-1rx/ schematic netlist is read headless (kicad-cli, nothing is written under kicad-1rx/)
and the decided rx1-02 changes of parts/rx1_changes.csv are applied to it: U24 EN and U23 EN move
from /3V8 to /fpga/adc/3V0 through R993 and R996 (rx1-094..097, choice rx1-seq A).

For each ordering the ADC (AD9237, AVDD 3V0) and the FPGA (XC7A100T) need, one row of sequence.csv:
- class `design`: an EN or PG chain, or a feed (a regulator's input is the earlier rail), forces
  it: walking back from the later rail's regulator through its input and its enable reaches the
  earlier rail's regulator;
- class `timing`: nothing forces it; it holds only because one regulator is faster. For the
  power-up rows `margin_*_ms` is the later rail's 90 % time minus the earlier rail's, from the
  datasheet times below (negative: the order does not hold). Power-off rows: no chain forces a
  power-off order (an EN or PG chain acts after the source rail has already fallen), and the
  datasheets give no discharge time, so the margin comes from the step 3 simulation.
Every `timing` row names its fixes (fixes.csv): the cost, the check against the EN thresholds,
and whether today's board has room (route_space.csv and place_fix.csv from analysis/11_board_1rx/
route_space.py and fix_space.py).

The timing model (assumptions A1-A4 are stated in the writeup):
- A1 all three bucks start together when 12 V passes their UVLO and EN (same net), each output
  ramps linearly over its soft-start time to its set voltage;
- A2 LP5907 3V0 follows 3V8 (no dropout) delayed by its turn-on time;
- A3 an LD39200 output reaches 90 % of nominal TLD after its EN passes its threshold, and never
  above 3V8; PG rises at 0.92 of nominal;
- A4 the EN threshold lies between VIL max and VIH min (the sheets give no single value).
"""
import collections
import csv
import itertools
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'analysis' / '11_board_1rx'))

# ---- datasheet numbers (manifest id, page) -------------------------------------------------
TSS_MS = (3.2, 4.0, 5.4)          # LMR51420 soft start min/typ/max (ti-lmr51420-datasheet p.5)
TON_MS = (0.080, 0.150)           # LP5907 turn-on typ/max (ti-lp5907-datasheet p.6)
TLD_MS = (0.1, 0.3)               # LD39200 EN to 90 % of 3.3 V, read from Figure 23 (st-ld39200-datasheet p.13):
                                  # about 0.8 of a 200 us division; the step 5 fit replaces this reading
EN_VIH = {'LP5907': 1.2, 'LD39200': 1.2}   # st-ld39200-datasheet p.7; ti-lp5907-datasheet p.6
EN_VIL = {'LP5907': 0.4, 'LD39200': 0.5}
LMR_EN_RISE = (1.1, 1.227, 1.36)  # ti-lmr51420-datasheet p.5
LMR_UVLO_RISE = (3.89, 4.5)       # typ, max (p.5)
PG_RISE, PG_FALL = 0.92, 0.80     # of VOUT (st-ld39200-datasheet p.7)
UP = 0.9                          # a rail is "up" at 90 % of nominal (amd-ds181-artix7-datasheet p.9 ramp definition)
VCCO_VCCAUX_MAX = 2.625           # V (amd-ds181-artix7-datasheet p.8)
T_VCCO2VCCAUX_MS = (300, 500, 800)  # at TJ 125, 100, 85 C (amd-ds181-artix7-datasheet p.9)
R_EN = 10e3                       # R993 / R996 (rx1_changes.csv rx1-096, rx1-097)
RAILS = {  # label: (net, nominal volts)
    '12V': ('/power/12V', 12.0), '3V8': ('/3V8', 3.81), '3V0': ('/fpga/adc/3V0', 3.0),
    '3V3A': ('/3V3A', 3.3), '1V8': ('/1V8', 1.8), '3V3D': ('/3V3D', 3.3), '1V0': ('/1V0', 1.008),
}
NET2RAIL = {v[0]: k for k, v in RAILS.items()}
# U17 FB divider R32 68k / R33 100k with 0.6 V (ti-lmr51420-datasheet p.5): 1.008 V; U18 100k/18.7k: 3.81 V

# regulator pin maps: value -> (family, in pins, en pin, out pin, pg pin)
FAMILY = {
    'LMR51420': ('LMR51420', ('3',), '5', None, None),
    'LP5907-3.0': ('LP5907', ('1',), '3', '5', None),
    'LD3920': ('LD39200', ('7', '8'), '6', '1', '5'),
    'LD3920_33': ('LD39200', ('6',), '5', '1', '4'),
}


# ---- netlist -------------------------------------------------------------------------------
def load(sch):
    import rx2_dnp
    return rx2_dnp.netlist(sch)


def apply_rx1(comps, nets, rows):
    """The decided rx1-seq A change: U24 and U23 EN from 3V0 through R993 / R996."""
    ids = {r['id']: r for r in rows}
    for i in ('rx1-094', 'rx1-095', 'rx1-096', 'rx1-097'):
        if ids.get(i, {}).get('status') != 'decided':
            raise SystemExit(f'{i} is not decided in parts/rx1_changes.csv; the rx1-seq A change is not applied')
    comps, nets = dict(comps), {k: list(v) for k, v in nets.items()}
    for u, r in (('U24', 'R993'), ('U23', 'R996')):
        nets['/3V8'] = [n for n in nets['/3V8'] if n != (u, '6')]
        en = f'Net-({u}-EN)'
        nets[en] = [(u, '6'), (r, '2')]
        nets['/fpga/adc/3V0'].append((r, '1'))
        comps[r] = dict(value='10k', fp='SMD_0402', sheet='/power/')
    return comps, nets


# ---- regulators and what enables them ------------------------------------------------------
def regulators(comps, nets):
    by = collections.defaultdict(dict)
    for n, nodes in nets.items():
        for r, p in nodes:
            by[r][p] = n
    regs = {}
    for ref, c in comps.items():
        if c['value'] not in FAMILY:
            continue
        fam, inp, en, out, pg = FAMILY[c['value']]
        d = dict(ref=ref, family=fam, vin=by[ref][inp[0]], en=by[ref][en], pg=by[ref].get(pg) if pg else None)
        if out:
            d['out'] = by[ref][out]
        else:   # buck: output rail is the far end of the FB divider's top resistor
            fb = by[ref]['4']
            top = [by[r]['1'] if by[r]['2'] == fb else by[r]['2'] for r, _ in nets[fb]
                   if r.startswith('R') and 'GND' not in (by[r].get('1'), by[r].get('2'))]
            d['out'] = top[0] if top else None
        regs[ref] = d
    return regs


def en_source(reg, regs, comps, nets):
    """What drives the EN net: ('pg', ref), ('rail', ref, net) or ('input', net) for a rail no
    regulator makes (12 V). Series resistors are followed; a PG pull-up is not a driver."""
    outs = {r['out']: k for k, r in regs.items() if r.get('out')}
    pgs = {r['pg']: k for k, r in regs.items() if r.get('pg')}
    pin = collections.defaultdict(dict)
    for n, nodes in nets.items():
        for r, p in nodes:
            pin[r][p] = n
    n, seen, via = reg['en'], set(), []
    while True:
        if n in pgs and pgs[n] != reg['ref']:
            return ('pg', pgs[n], n, via)
        if n in outs and outs[n] != reg['ref']:
            return ('rail', outs[n], n, via)
        seen.add(n)
        nxt = None
        if len(nets[n]) <= 3:
            for r, _ in nets[n]:
                if r.startswith('R') and len(pin[r]) == 2:
                    other = [m for m in pin[r].values() if m != n]
                    if other and other[0] not in seen and other[0] != 'GND':
                        nxt = (r, other[0])
        if nxt is None:
            return ('input', n, n, via)
        via.append(nxt[0])
        n = nxt[1]


def parents(ref, regs, comps, nets):
    """The regulators that must be on before `ref` is: the one making its input rail (feed) and the
    one driving its EN (enable)."""
    outs = {r['out']: k for k, r in regs.items() if r.get('out')}
    reg = regs[ref]
    feed = outs.get(reg['vin'])
    src = en_source(reg, regs, comps, nets)
    en = src[1] if src[0] in ('pg', 'rail') else None
    if src[0] == 'input' and src[1] in outs:
        en = outs[src[1]]
    return feed, en, src


def ancestors(ref, regs, comps, nets, feed_only=False):
    out, q = {}, [(ref, [ref])]
    while q:
        r, path = q.pop()
        feed, en, _ = parents(r, regs, comps, nets)
        for kind, p in (('feed', feed), ('enable', en)):
            if p and p not in out and not (feed_only and kind == 'enable'):
                out[p] = path + [f'{kind}:{p}']
                q.append((p, path + [f'{kind}:{p}']))
    return out


def root_net(ref, regs, comps, nets):
    """The net a regulator's start finally traces back to (12 V for the bucks)."""
    seen = set()
    while ref and ref not in seen:
        seen.add(ref)
        feed, en, src = parents(ref, regs, comps, nets)
        if feed is None:
            return regs[ref]['vin']
        ref = feed
    return None


def rail_reg(label, regs):
    net = RAILS[label][0]
    for k, r in regs.items():
        if r.get('out') == net:
            return k
    return None


# ---- orderings the ADC and the FPGA need ---------------------------------------------------
# (id, direction, earlier, later, who needs it, source)
ORDERS = [
    ('on-3V0-3V3A', 'on', '3V0', '3V3A', 'AD9237 AVDD before the U45 input stage, U1', 'adi-ad9237-datasheet p.7 (VIN abs max AVDD + 0.3 V)'),
    ('on-3V0-1V8', 'on', '3V0', '1V8', 'AD9237 AVDD before the FPGA that drives PDWN and OE', 'adi-ad9237-datasheet p.7 (PDWN abs max AVDD + 0.3 V)'),
    ('on-3V0-3V3D', 'on', '3V0', '3V3D', 'AD9237 AVDD before U6 (CLK), the FPGA outputs and DRVDD', 'adi-ad9237-datasheet p.7 (CLK abs max AVDD + 0.3 V); p.10 Figure 7'),
    ('on-VCCINT-VCCBRAM', 'on', '1V0', '1V0', 'FPGA VCCINT before VCCBRAM', 'amd-ds181-artix7-datasheet p.8'),
    ('on-VCCINT-VCCAUX', 'on', '1V0', '1V8', 'FPGA VCCINT before VCCAUX', 'amd-ds181-artix7-datasheet p.8'),
    ('on-VCCINT-VCCO', 'on', '1V0', '3V3D', 'FPGA VCCINT before VCCO', 'amd-ds181-artix7-datasheet p.8'),
    ('on-VCCAUX-VCCO', 'on', '1V8', '3V3D', 'FPGA VCCAUX before VCCO', 'amd-ds181-artix7-datasheet p.8'),
    ('off-3V3A-3V0', 'off', '3V3A', '3V0', 'U45 and U1 supply off before AD9237 AVDD', 'adi-ad9237-datasheet p.7 (VIN abs max AVDD + 0.3 V)'),
    ('off-1V8-3V0', 'off', '1V8', '3V0', 'FPGA VCCAUX off before AD9237 AVDD (PDWN, OE drivers)', 'adi-ad9237-datasheet p.7'),
    ('off-3V3D-3V0', 'off', '3V3D', '3V0', 'U6 and FPGA outputs off before AD9237 AVDD (CLK)', 'adi-ad9237-datasheet p.7; p.10 Figure 7'),
    ('off-VCCO-VCCAUX', 'off', '3V3D', '1V8', 'FPGA VCCO off before VCCAUX (power-off in reverse)', 'amd-ds181-artix7-datasheet p.8'),
    ('off-VCCAUX-VCCINT', 'off', '1V8', '1V0', 'FPGA VCCAUX off before VCCINT', 'amd-ds181-artix7-datasheet p.8'),
    ('off-VCCO-VCCINT', 'off', '3V3D', '1V0', 'FPGA VCCO off before VCCINT', 'amd-ds181-artix7-datasheet p.8'),
]


def classify(order, regs, comps, nets):
    """('design'|'timing', chain text, enabling text) for one ordering on a given netlist."""
    _, d, e, l, _, _ = order
    re_, rl = rail_reg(e, regs), rail_reg(l, regs)
    if d == 'on':
        if re_ == rl:
            return 'design', f'one rail ({RAILS[e][0]}), {re_}', ''
        anc = ancestors(rl, regs, comps, nets)
        if re_ in anc:
            return 'design', _chain(rl, re_, anc), ''
        ra, rb = root_net(rl, regs, comps, nets), root_net(re_, regs, comps, nets)
        both = f'both trace back to {ra}' if ra == rb else f'they trace back to {ra} and {rb}'
        return 'timing', f'{rl} does not depend on {re_}; {both} (EN and input), nothing orders them', ''
    # power-off: the later-named rail is the one that must outlast; it can be forced only by a
    # feed (the earlier-off rail's regulator takes its input from it)
    anc = ancestors(re_, regs, comps, nets, feed_only=True)
    if rl in anc:
        return 'design', f'{re_} is fed from {RAILS[l][0]}', ''
    return 'timing', (f'no feed from {l} to {e}; an EN or PG chain from {l} acts only after {l} has fallen below '
                       f'its EN low threshold, so it cannot make {e} fall first'), ''


def _chain(rl, re_, anc):
    """Readable chain: later rail <- how <- earlier regulator."""
    parts, cur = [], rl
    path = anc[re_]
    for step in path[1:]:
        kind, p = step.split(':')
        parts.append(f'{cur} {kind} <- {p}')
        cur = p
    return parts


def describe_enable(ref, regs, comps, nets):
    reg = regs[ref]
    feed, en, src = parents(ref, regs, comps, nets)
    via = f' via {"+".join(src[3])}' if src[3] else ''
    if src[0] == 'pg':
        e = f'EN on the PG of {src[1]} ({src[2]}){via}'
    elif src[0] == 'rail':
        e = f'EN on {src[2]} (output of {src[1]}){via}'
    else:
        e = f'EN on {src[1]}{via}'
    f = f'input {reg["vin"]}' + (f' (output of {feed})' if feed else '')
    return f'{ref}: {e}; {f}'


# ---- the timing model ----------------------------------------------------------------------
def t38(v, tss18):
    return tss18 * v / RAILS['3V8'][1]


def v3v0(t, tss18, ton):
    return max(0.0, min(RAILS['3V0'][1], RAILS['3V8'][1] * min((t - ton) / tss18, 1.0)))


def en_cross(vth, tss18, ton, tau):
    """Time the U23 EN node, driven from 3V0 through R and C to GND (time constant tau, ms), crosses vth."""
    if tau <= 0:
        return t38(vth, tss18) + ton
    t, v, dt = 0.0, 0.0, 0.002
    while v < vth and t < 200:
        v += (v3v0(t, tss18, ton) - v) * dt / tau
        t += dt
    return t


def t_up(rail, tss17, tss18, edge, tau=0.0):
    """Time (ms) the rail passes 90 % of nominal; edge 'early' or 'late' takes each device's own
    extreme (A1-A4)."""
    e = edge == 'early'
    ton = TON_MS[0] if e else TON_MS[1]
    tld = TLD_MS[0] if e else TLD_MS[1]
    vth_lo, vth_hi = EN_VIL['LD39200'], EN_VIH['LD39200']
    vth = vth_lo if e else vth_hi
    # tau tolerance: R 1 %, C +-20 % (assumption)
    tau_e = tau * (0.99 * 0.8 if e else 1.01 * 1.2)
    if rail == '1V0':
        return UP / RAILS['1V0'][1] * tss17
    if rail == '3V8':
        return t38(UP * RAILS['3V8'][1], tss18)
    if rail == '3V0':
        return t38(UP * RAILS['3V0'][1], tss18) + ton
    if rail == '3V3A':
        t_en = en_cross(vth, tss18, ton, 0.0)
        return max(t_en + tld, t38(UP * RAILS['3V3A'][1], tss18))
    t_en = en_cross(vth, tss18, ton, tau_e)
    if rail == '1V8':
        return max(t_en + tld, t38(UP * RAILS['1V8'][1], tss18))
    if rail == '3V3D':
        t_pg = t_en + tld * PG_RISE / UP
        return max(t_pg + tld, t38(UP * RAILS['3V3D'][1], tss18))
    raise KeyError(rail)


def margin(earlier, later, tau=0.0):
    """Later rail's 90 % time minus the earlier rail's, over every soft-start corner: worst, typical, best."""
    worst, best = 1e9, -1e9
    for a, b in itertools.product(TSS_MS, TSS_MS):
        w = t_up(later, a, b, 'early', tau) - t_up(earlier, a, b, 'late')
        s = t_up(later, a, b, 'late', tau) - t_up(earlier, a, b, 'early')
        worst, best = min(worst, w), max(best, s)
    typ = t_up(later, 4.0, 4.0, 'late', tau) - t_up(earlier, 4.0, 4.0, 'early')
    typ2 = t_up(later, 4.0, 4.0, 'early', tau) - t_up(earlier, 4.0, 4.0, 'late')
    return dict(worst=round(worst, 2), typ=round((typ + typ2) / 2, 2), best=round(best, 2))


def tau_ms(c_uf):
    return R_EN * c_uf * 1e-6 * 1e3


# ---- fixes ---------------------------------------------------------------------------------
def space(prefix, route_rows, place_rows):
    """Text on today's board room for a fix: the routes of route_space.csv and the placement."""
    out = []
    for r in route_rows:
        if r['change'].startswith(prefix + ' '):
            if r['found'] == 'True':
                out.append(f"{r['change'][len(prefix) + 1:]}: {r['length_mm']} mm, {r['vias']} via(s), {r['layers']}")
            else:
                out.append(f"{r['change'][len(prefix) + 1:]}: no route ({r['note']})")
    return '; '.join(out)


def place_text(part, place_rows):
    rows = [r for r in place_rows if r['part'] == part]
    if not rows:
        return ''
    if rows[0]['found'] != 'True':
        return f'{part}: no free spot within 12 mm of the anchor'
    r = rows[0]
    return (f"{part}: {'top' if r['side'] == 'F' else 'bottom'} side at {r['part_x']}, {r['part_y']} mm, "
            f"{r['dist_from_anchor_mm']} mm from {r['anchor']}")


def read_csv(path):
    return list(csv.DictReader(open(path))) if os.path.exists(path) else []


def build_fixes(m_none, route_rows, place_rows):
    c_opts = [1.0, 2.2, 4.7]
    rc = {c: margin('1V0', '1V8', tau_ms(c)) for c in c_opts}
    rc_pick = next((c for c in c_opts if rc[c]['worst'] > 0), None)
    rc3 = {c: margin('1V0', '3V3D', tau_ms(c)) for c in c_opts}
    rc_txt = '; '.join(f'{c:g} uF: 1V0 before 1V8 worst {rc[c]["worst"]} typ {rc[c]["typ"]} best {rc[c]["best"]} ms, '
                       f'1V0 before 3V3D worst {rc3[c]["worst"]} typ {rc3[c]["typ"]} best {rc3[c]["best"]} ms' for c in c_opts)
    pick = f'{rc_pick:g}' if rc_pick else 'none of the values tried'
    rows = []
    rows.append(dict(
        fix='F1a', for_rows='on-VCCINT-VCCAUX;on-VCCINT-VCCO', kind='rejected',
        what='U23 EN straight from 1V0 (1.008 V), or from a 1V0 divider',
        parts='none', nets='1V0 to U23 EN', margin_ms='',
        en_check='fails: 1.008 V is below the LD39200 EN high threshold of 1.2 V min (st-ld39200-datasheet p.7) and a divider only lowers it',
        side_effects='1V8 would never be enabled', space='not routed: the fix does not work'))
    rows.append(dict(
        fix='F1b', for_rows='on-VCCINT-VCCAUX;on-VCCINT-VCCO', kind='timing',
        what=(f'RC delay on U23 EN: with R996 10k, a capacitor from the U23 EN node to GND next to U23 (time constant '
              f'{tau_ms(1.0):g} ms per uF); the smallest of 1u, 2.2u, 4.7u that keeps the worst-case margin positive is {pick} uF'),
        parts='1 x capacitor (4.7u is 0603/0805 class, 1u and 2.2u 0402/0603; the footprint used for the space check is 0402); stock checked at order time',
        nets='0 new nets (one pad on the U23 EN node, one on GND)', margin_ms=rc_txt,
        en_check='EN node settles at 3V0 (2.85 V min) > 1.2 V VIH; it crosses 1.2 V (VIH min) about 0.5 x R x C after 3V0 has settled, and falls through 0.5 V (VIL max) about 1.8 x R x C after 3V0 falls (power-off tail)',
        side_effects=(f'still `timing`: the margin is the datasheet spread of two bucks and one RC; at power-off the EN node holds U23 on '
                      f'about {1.79 * tau_ms(1.0):.0f} ms per uF after 3V0 falls (1V8 and 3V3D outlast 3V0, which the CLK case of step 3 must cover); '
                      f'it also delays 1V8 and 3V3D by up to {rc[rc_pick]["best"] if rc_pick else rc[c_opts[-1]]["best"]} ms later than 1V0 at start'),
        space=space('F1b', route_rows, place_rows) + '; ' + place_text('C_DLY', place_rows)))
    rows.append(dict(
        fix='F1c', for_rows='on-VCCINT-VCCAUX;on-VCCINT-VCCO', kind='design',
        what='supervisor on 1V0: open-drain output pulls the U23 EN node to GND until 1V0 is above 0.9 x 1V0; R996 stays as the pull-up to 3V0; VDD from 3V8 beside U23',
        parts='1 x supervisor / voltage detector (SOT-23-5 class, open-drain, defined output from VDD about 1 V, threshold 0.9 V or an adjustable SENSE; part and JLC stock to be chosen, no sheet on file)',
        nets='1V0 tap to SENSE; OUT joins the U23 EN node; VDD to 3V8; GND (4 pad connections, 0 new net names)',
        margin_ms=f'1V8 cannot start before 1V0 is at 0.9 V: at least {TLD_MS[0]} ms (LD39200 EN to 90 %) after it, in every corner',
        en_check='OUT low holds EN below 0.5 V VIL max; released it lets R996 pull the node to 3V0 above 1.2 V VIH min; 3V3D follows through the U23 PG chain',
        side_effects='acts at power-on only: at power-off the supervisor lowers EN after 1V0 has fallen, so it does not force VCCAUX off before VCCINT; adds 1V0 loading by the sense input; 1V0 and 1V8 start-up are visible as one more node for the bring-up scope',
        space='; '.join(x for x in (space('F1c', route_rows, place_rows), place_text('SUP1', place_rows)) if x)))
    rows.append(dict(
        fix='F1d', for_rows='on-VCCINT-VCCAUX;on-VCCINT-VCCO', kind='rejected',
        what='EN divider on U18 (3V8) from 12 V so 3V8 starts after U17 (1V0)',
        parts='2 resistors (e.g. 100k / 20k puts the 12 V start at 6.6 to 8.2 V with the 1.1 to 1.36 V EN threshold)',
        nets='U18 EN split from 12 V, 1 new net', margin_ms='none: set by the 12 V ramp rate, which is not on file; U17 starts at the 3.9 to 4.5 V UVLO and needs 3.2 to 5.4 ms, so the 12 V ramp from 4.5 V to 6.6 V would have to last longer than that',
        en_check='LMR51420 EN rising threshold 1.1 to 1.36 V (ti-lmr51420-datasheet p.5): the divider works as a 12 V threshold, but it still ties 3V8 to the 12 V ramp, not to 1V0',
        side_effects='a 12 V plugged in within about 1 ms defeats it; delays 3V0, 3V3A, 1V8 and 3V3D together',
        space='not routed: the fix gives no margin'))
    rows.append(dict(
        fix='F1e', for_rows='on-VCCINT-VCCAUX;on-VCCINT-VCCO', kind='rejected',
        what='PG chain from U17 (1V0) to U23 EN',
        parts='none', nets='', margin_ms='',
        en_check='the LMR51420 has no power-good output: its six pins are GND, SW, VIN, FB, EN, CB (ti-lmr51420-datasheet p.3)',
        side_effects='', space='not routed: no PG pin to connect'))
    off = ('off-3V3A-3V0;off-1V8-3V0;off-3V3D-3V0;off-VCCO-VCCAUX;off-VCCAUX-VCCINT;off-VCCO-VCCINT')
    rows.append(dict(
        fix='F2a', for_rows='off-3V3A-3V0;off-1V8-3V0;off-3V3D-3V0', kind='timing',
        what='hold-up on 3V0: one more 10u 0805 from 3V0 to GND next to U39, so AVDD outlasts 3V3A, 1V8 and 3V3D at 12 V removal',
        parts='1 x 10u 0805 (C15850, the board\'s 10u part; stock at order time)',
        nets='0 new nets (3V0, GND)', margin_ms='from the step 3 power-down case (12 V removal): the 3V0 decay with and without it',
        en_check='no EN is touched',
        side_effects='3V0 rise at start: 12.4 uF becomes 22.4 uF behind the U39 (more in-rush from 3V8; U39 current limit and the 3V0 start time are in step 3)',
        space='; '.join(x for x in (space('F2a', route_rows, place_rows), place_text('C_HOLD', place_rows)) if x)))
    rows.append(dict(
        fix='F2b', for_rows='off-3V3D-3V0;off-VCCO-VCCAUX;off-VCCO-VCCINT', kind='timing',
        what='bleeder on 3V3D: one resistor 3V3D to GND next to U25, so 3V3D (72.57 uF) falls faster at 12 V removal',
        parts='1 x 0402 resistor (value from the step 3 sweep; 3.3 V over 1k is 3.3 mA continuous); stock at order time',
        nets='0 new nets (3V3D, GND)', margin_ms='from the step 3 power-down case',
        en_check='no EN is touched',
        side_effects='continuous load on 3V3D; speeds the fall of VCCO and DRVDD, so VCCO falls before VCCAUX and VCCINT more often',
        space='; '.join(x for x in (space('F2b', route_rows, place_rows), place_text('R_BLEED', place_rows)) if x)))
    rows.append(dict(
        fix='F2c', for_rows=off, kind='none',
        what='a circuit that forces the power-off order at sudden 12 V removal',
        parts='n/a', nets='n/a', margin_ms='',
        en_check='an EN or PG chain acts after its source rail has fallen below the EN low threshold (0.5 V LD39200, 0.4 V LP5907), so it makes the dependent rail fall second; only a feed (input from the earlier rail) forces the order, and the LDOs are all fed from 3V8',
        side_effects='the order is set by each rail\'s stored charge against its load: 3V0 12.4 uF, 1V8 68.75 uF, 3V3D 82.57 uF with C995, 1V0 178.28 uF; the simulation of step 3 measures it',
        space='n/a'))
    return rows


# ---- main ----------------------------------------------------------------------------------
def main():
    comps0, nets0 = load(ROOT / 'kicad-1rx' / 'fmcw3_1rx.kicad_sch')
    changes = list(csv.DictReader(open(ROOT / 'parts' / 'rx1_changes.csv')))
    comps1, nets1 = apply_rx1(comps0, nets0, changes)
    regs0, regs1 = regulators(comps0, nets0), regulators(comps1, nets1)
    route_rows = read_csv(ROOT / 'analysis' / '11_board_1rx' / 'route_space.csv')
    place_rows = read_csv(HERE / 'place_fix.csv')
    fixes = build_fixes(None, route_rows, place_rows)
    fix_for = collections.defaultdict(list)
    for f in fixes:
        for r in f['for_rows'].split(';'):
            fix_for[r].append(f['fix'])

    rows = []
    for o in ORDERS:
        oid, d, e, l, why, src = o
        cls0, chain0, _ = classify(o, regs0, comps0, nets0)
        cls1, chain1, _ = classify(o, regs1, comps1, nets1)
        rl = rail_reg(l, regs1)
        row = dict(id=oid, direction=d, requirement=f'{e} {"before" if d == "on" else "off before"} {l}' if d == 'on'
                   else f'{e} off before {l} off',
                   needed_by=why, source=src, enable_of_later=describe_enable(rl, regs1, comps1, nets1) if d == 'on' else
                   describe_enable(rail_reg(e, regs1), regs1, comps1, nets1),
                   class_today=cls0, class_rx1=cls1,
                   chain='; '.join(chain1) if isinstance(chain1, list) else chain1)
        if d == 'on' and e != l:
            m = margin(e, l)
            row.update(margin_worst_ms=m['worst'], margin_typ_ms=m['typ'], margin_best_ms=m['best'],
                       margin_basis='later rail 90 % time minus earlier rail 90 % time; soft start 3.2/4.0/5.4 ms, LP5907 80-150 us, LD39200 0.1-0.3 ms')
            if cls1 == 'design' and e == '3V0':
                row['margin_basis'] += (f'; design forces only the START: the EN fires when 3V0 is {EN_VIL["LD39200"]} to '
                                        f'{EN_VIH["LD39200"]} V ({EN_VIL["LD39200"] / 3.0:.0%} to {EN_VIH["LD39200"] / 3.0:.0%} of 3.0 V, '
                                        'st-ld39200-datasheet p.7), so a negative margin means the later rail passes 90 % first '
                                        'and the step 3 simulation checks the pins')
        elif d == 'on':
            row.update(margin_worst_ms='', margin_typ_ms='', margin_best_ms='', margin_basis='VCCINT and VCCBRAM are one rail (/1V0)')
        else:
            row.update(margin_worst_ms='', margin_typ_ms='', margin_best_ms='',
                       margin_basis='no datasheet gives the discharge; step 3 simulation (12 V removal case)')
        row['fixes'] = ';'.join(fix_for.get(oid, []))
        rows.append(row)

    by_id_today = {r['id']: r['class_today'] for r in rows}
    # The VCCO - VCCAUX limit: on the ramp, VCCO starts at the U23 PG rising threshold
    vcco_max, vcco_aux_min = 3.3 * 1.05, PG_RISE * 1.8
    rows.insert(7, dict(
        id='on-VCCO-minus-VCCAUX', direction='on', requirement=f'VCCO - VCCAUX not above {VCCO_VCCAUX_MAX} V for longer than TVCCO2VCCAUX',
        needed_by='FPGA reliability (HR bank VCCO 3.3 V)', source='amd-ds181-artix7-datasheet p.8, p.9 (300 ms at 125 C, 500 ms at 100 C, 800 ms at 85 C)',
        enable_of_later=describe_enable('U25', regs1, comps1, nets1), class_today='', class_rx1='design',
        chain=f'U25 EN on the U23 PG: 3V3D starts only when 1V8 is above {PG_RISE} x 1.8 V = {vcco_aux_min:.3f} V, so VCCO - VCCAUX is at most '
              f'{vcco_max:.3f} - {vcco_aux_min:.3f} = {vcco_max - vcco_aux_min:.2f} V on the ramp',
        margin_worst_ms='', margin_typ_ms='', margin_best_ms='',
        margin_basis=f'{VCCO_VCCAUX_MAX - (vcco_max - vcco_aux_min):.2f} V under the limit on the ramp, for any time',
        fixes=''))
    rows.insert(len(rows), dict(
        id='off-VCCO-minus-VCCAUX', direction='off', requirement=f'VCCO - VCCAUX not above {VCCO_VCCAUX_MAX} V for longer than TVCCO2VCCAUX',
        needed_by='FPGA reliability (HR bank VCCO 3.3 V)', source='amd-ds181-artix7-datasheet p.8, p.9',
        enable_of_later=describe_enable('U25', regs1, comps1, nets1), class_today='timing', class_rx1='timing',
        chain=f'U25 turns off when the U23 PG falls ({PG_FALL} x 1.8 V = {PG_FALL * 1.8:.2f} V); 3V3D then decays on its own load',
        margin_worst_ms='', margin_typ_ms='', margin_best_ms='',
        margin_basis=f'the time limit is 300 ms at 125 C; the decay of 3V3D from 3.3 V to 1V8 + {VCCO_VCCAUX_MAX} V is in the step 3 power-down case',
        fixes='F2b'))
    # the ramp limit holds by the same chain as VCCAUX before VCCO, today and with rx1-02
    for r in rows:
        if r['id'] == 'on-VCCO-minus-VCCAUX':
            r['class_today'] = by_id_today['on-VCCAUX-VCCO']

    keys = ['id', 'direction', 'requirement', 'needed_by', 'source', 'enable_of_later', 'class_today', 'class_rx1',
            'chain', 'margin_worst_ms', 'margin_typ_ms', 'margin_best_ms', 'margin_basis', 'fixes']
    with open(HERE / 'sequence.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    fk = ['fix', 'for_rows', 'kind', 'what', 'parts', 'nets', 'margin_ms', 'en_check', 'side_effects', 'space']
    with open(HERE / 'fixes.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fk)
        w.writeheader()
        w.writerows(fixes)
    for r in rows:
        print(f"{r['id']:24s} today={r['class_today']:7s} rx1={r['class_rx1']:7s} worst={r['margin_worst_ms']!s:7s} typ={r['margin_typ_ms']!s:7s} fixes={r['fixes']}")
    # self-checks the step is proved by
    by = {r['id']: r for r in rows}
    assert by['on-3V0-3V3A']['class_rx1'] == 'design' and by['on-3V0-3V3A']['class_today'] == 'timing'
    assert by['on-3V0-1V8']['class_rx1'] == 'design' and by['on-3V0-3V3D']['class_rx1'] == 'design'
    assert by['on-VCCAUX-VCCO']['class_rx1'] == 'design'
    assert by['on-VCCINT-VCCAUX']['class_rx1'] == 'timing' and by['on-VCCINT-VCCAUX']['class_today'] == 'timing'
    assert all(r['fixes'] for r in rows if r['class_rx1'] == 'timing'), 'a timing row has no fix'


if __name__ == '__main__':
    main()
