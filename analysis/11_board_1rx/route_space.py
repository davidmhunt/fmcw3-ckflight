"""Is there board space for a new trace? A grid router over the real 1-RX board (read only).

Run: ./run --native python3 analysis/11_board_1rx/route_space.py [--board PCB] [--out DIR]

For each new connection (a pad to an existing net) it searches the cheapest path on the board as
it is today, so a result means "a route exists without moving anything"; the routing itself stays
the user's. Rules, on a 0.1 mm grid:
- trace 0.15 mm, clearance 0.15 mm (the board minimum is 0.1 / 0.1016 mm);
- obstacles on each layer: pads, tracks and vias of other nets, filled zones of other nets except
  GND pours on L1, L4 and L6 (a pour re-flows around a new trace), keepouts that forbid tracks;
- L2_GND and L5_GND are reference planes: no traces there; L3_PWR only inside a zone of the
  target net (a trace never splits another power plane);
- a via (0.46 / 0.254 mm, the board default) needs 0.38 mm free of other-net pads, tracks and
  vias on every layer; it may pass through planes (they get an antipad);
- the existing copper that joins the pad to its old net is ignored (it is cut by the change);
- the target is any copper of the new net: pads, tracks, vias and zone fill.
The cost is length plus 2 mm per via. Output: route_space.csv and one PNG per connection.
"""
import argparse
import csv
import heapq
import math
import os

import numpy as np
import pcbnew

STEP = 0.1
TW, CL = 0.15, 0.15
VIA_R = 0.23 + CL
VIA_COST = 2.0
LAYERS = ['L1_SIG', 'L3_PWR', 'L4_PWR_SIG', 'L6_SIG']
POUR_OK = {'L1_SIG', 'L4_PWR_SIG', 'L6_SIG'}

# The decided rail-order changes (rx1-seq A): the pad that moves to a new net.
CHANGES = [
    dict(name='U24 EN to 3V0', ref='U24', pad='6', old='/3V8', new='/fpga/adc/3V0'),
    dict(name='U23 EN to 3V0', ref='U23', pad='6', old='/3V8', new='/fpga/adc/3V0'),
    # rx1-05 step 2: the proposed fixes for the timing-only orderings. Each pad of a new part is
    # placed by analysis/15_rx1_powerup/fix_space.py (place_fix.csv), then routed here. U23 pin 6
    # (EN) is the target for the fixes that act on the 1V8 enable; the 3V0 route from the
    # rx1-seq change above is not on the board yet, so it does not block these routes.
    # F1b: RC delay, 1u from the U23 EN node to GND.
    dict(name='F1b cap to U23 EN', part='C_DLY', role='EN', to_pad=('U23', '6'), cut=('U23', '6', '/3V8'),
         png='route_f1b_en.png'),
    dict(name='F1b cap to GND', part='C_DLY', role='GND', new='GND', reach=10.0, png='route_f1b_gnd.png'),
    # F1c: supervisor on 1V0 that pulls the U23 EN node low (VDD from 3V8 beside U23).
    dict(name='F1c supervisor OUT to U23 EN', part='SUP1', role='OUT', to_pad=('U23', '6'),
         cut=('U23', '6', '/3V8'), png='route_f1c_out.png'),
    dict(name='F1c supervisor SENSE to 1V0', part='SUP1', role='SENSE', new='/1V0', reach=40.0,
         png='route_f1c_sense.png'),
    dict(name='F1c supervisor VDD to 3V8', part='SUP1', role='VDD', new='/3V8', reach=10.0,
         png='route_f1c_vdd.png'),
    dict(name='F1c supervisor GND', part='SUP1', role='GND', new='GND', reach=10.0, png='route_f1c_gnd.png'),
    # F2a: hold-up capacitor on 3V0 (AVDD outlasts 3V3D at power-off).
    dict(name='F2a hold-up cap to 3V0', part='C_HOLD', role='3V0', new='/fpga/adc/3V0', reach=15.0,
         png='route_f2a_3v0.png'),
    dict(name='F2a hold-up cap to GND', part='C_HOLD', role='GND', new='GND', reach=10.0, png='route_f2a_gnd.png'),
    # F2b: bleeder resistor from 3V3D to GND (3V3D falls first at power-off).
    dict(name='F2b bleeder to 3V3D', part='R_BLEED', role='3V3D', new='/3V3D', reach=15.0, png='route_f2b_3v3d.png'),
    dict(name='F2b bleeder to GND', part='R_BLEED', role='GND', new='GND', reach=10.0, png='route_f2b_gnd.png'),
    # F3a (step 6): CLK divider, a 680 ohm shunt from the /ADC_CLK node (R15 pad 1) to GND.
    dict(name='F3a CLK shunt to ADC_CLK', part='R_CLK', role='CLK', new='/ADC_CLK', reach=10.0,
         png='route_f3a_clk.png'),
    dict(name='F3a CLK shunt to GND', part='R_CLK', role='GND', new='GND', reach=10.0, png='route_f3a_gnd.png'),
]
PLACE_FIX = 'analysis/15_rx1_powerup/place_fix.csv'

mm, MM = pcbnew.ToMM, pcbnew.FromMM


def seg_mask(xs, ys, x0, y0, x1, y1, r):
    """Grid points within r of the segment (x0,y0)-(x1,y1)."""
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    X, Y = np.meshgrid(xs, ys)
    if L2 == 0:
        t = np.zeros_like(X)
    else:
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
    return (X - x0 - t * dx) ** 2 + (Y - y0 - t * dy) ** 2 <= r * r


def route(b, ch, margin=12.0):
    """ch: ref/pad/old/new (a pad that moves to net `new`), or at=(x, y, 'F'|'B') for a pad of a new
    part, a target net `new` or a target pad to_pad=(ref, pad), cut=(ref, pad, oldnet) for copper
    that the change cuts, and reach=mm to look only at target copper that close to the start."""
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    at = ch.get('at')
    if at:
        pad = None
        sx, sy = at[0], at[1]
        src_l = 'L1_SIG' if at[2] == 'F' else 'L6_SIG'
    else:
        fp = b.FindFootprintByReference(ch['ref'])
        pad = [p for p in fp.Pads() if p.GetNumber() == ch['pad']][0]
        sx, sy = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        src_l = 'L1_SIG' if pad.IsOnLayer(lid['L1_SIG']) else 'L6_SIG'
    new = ch.get('new')
    to_pad = tuple(ch['to_pad']) if ch.get('to_pad') else None
    reach = ch.get('reach')
    near = (lambda x, y: True) if not reach else (lambda x, y: math.hypot(x - sx, y - sy) <= reach)
    # target copper of the new net: nearest point bounds the window
    tgt_pts = [(mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in b.GetPads() if new and p.GetNetname() == new]
    tgt_pts += [(mm(t.GetStart().x), mm(t.GetStart().y)) for t in b.GetTracks() if new and t.GetNetname() == new]
    if to_pad:
        tp = [p for p in b.FindFootprintByReference(to_pad[0]).Pads() if p.GetNumber() == to_pad[1]][0]
        tgt_pts.append((mm(tp.GetPosition().x), mm(tp.GetPosition().y)))
    tgt_pts = [q for q in tgt_pts if near(*q)]
    for z in b.Zones():
        if new and z.GetNetname() == new and not z.GetIsRuleArea() and not reach:
            k = z.GetBoundingBox()
            tgt_pts += [(mm(k.GetLeft()), mm(k.GetTop())), (mm(k.GetRight()), mm(k.GetBottom()))]
    if reach:
        margin = min(margin, reach / 2)
    x0 = min([sx] + [p[0] for p in tgt_pts]) - margin
    x1 = max([sx] + [p[0] for p in tgt_pts]) + margin
    y0 = min([sy] + [p[1] for p in tgt_pts]) - margin
    y1 = max([sy] + [p[1] for p in tgt_pts]) + margin
    eb = b.GetBoardEdgesBoundingBox()
    x0, y0 = max(x0, mm(eb.GetLeft()) + 0.5), max(y0, mm(eb.GetTop()) + 0.5)
    x1, y1 = min(x1, mm(eb.GetRight()) - 0.5), min(y1, mm(eb.GetBottom()) - 0.5)
    xs = np.arange(x0, x1, STEP)
    ys = np.arange(y0, y1, STEP)
    nx, ny = len(xs), len(ys)
    nl = len(LAYERS)
    blocked = np.zeros((nl, ny, nx), bool)
    target = np.zeros((nl, ny, nx), bool)
    via_block = np.zeros((ny, nx), bool)
    r_tr = TW / 2 + CL

    def idx_box(ax0, ay0, ax1, ay1):
        i0 = max(0, int((ax0 - x0) / STEP)); i1 = min(nx, int((ax1 - x0) / STEP) + 2)
        j0 = max(0, int((ay0 - y0) / STEP)); j1 = min(ny, int((ay1 - y0) / STEP) + 2)
        return i0, i1, j0, j1

    # copper joining the pad to its old net, which the change cuts: tracks touching the pad
    cut_pad, old = pad, ch.get('old')
    if ch.get('cut'):
        cut_pad = [p for p in b.FindFootprintByReference(ch['cut'][0]).Pads() if p.GetNumber() == ch['cut'][1]][0]
        old = ch['cut'][2]
    cut = set()
    pbb = cut_pad.GetBoundingBox() if cut_pad else None
    for t in b.GetTracks():
        if pbb is None or t.GetNetname() != old or t.Type() == pcbnew.PCB_VIA_T:
            continue
        for e in (t.GetStart(), t.GetEnd()):
            if pbb.Contains(e):
                cut.add(t.m_Uuid.AsString())

    # pads
    for p in b.GetPads():
        k = p.GetBoundingBox()
        ax0, ay0, ax1, ay1 = mm(k.GetLeft()), mm(k.GetTop()), mm(k.GetRight()), mm(k.GetBottom())
        if ax1 < x0 or ax0 > x1 or ay1 < y0 or ay0 > y1:
            continue
        same = bool(new) and p.GetNetname() == new
        if to_pad and (p.GetParentFootprint().GetReference(), p.GetNumber()) == to_pad:
            same = True
        is_src = (pad is not None and p.GetParentFootprint().GetReference() == ch['ref']
                  and p.GetNumber() == ch['pad'])
        if cut_pad is not None and p.m_Uuid == cut_pad.m_Uuid and not same:
            is_src = True  # the pad whose net the change moves
        i0, i1, j0, j1 = idx_box(ax0 - VIA_R, ay0 - VIA_R, ax1 + VIA_R, ay1 + VIA_R)
        X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
        dx = np.maximum(np.maximum(ax0 - X, X - ax1), 0)
        dy = np.maximum(np.maximum(ay0 - Y, Y - ay1), 0)
        d = np.hypot(dx, dy)
        for li, ln in enumerate(LAYERS):
            if not p.IsOnLayer(lid[ln]):
                continue
            if same:
                target[li, j0:j1, i0:i1] |= d == 0
            elif not is_src:
                blocked[li, j0:j1, i0:i1] |= d < r_tr
        if not same and not is_src and (p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH or
                                         any(p.IsOnLayer(lid[l]) for l in ('L1_SIG', 'L6_SIG'))):
            via_block[j0:j1, i0:i1] |= d < VIA_R

    # tracks and vias
    for t in b.GetTracks():
        k = t.GetBoundingBox()
        if mm(k.GetRight()) < x0 or mm(k.GetLeft()) > x1 or mm(k.GetBottom()) < y0 or mm(k.GetTop()) > y1:
            continue
        if t.m_Uuid.AsString() in cut:
            continue
        same = bool(new) and t.GetNetname() == new
        ax, ay, bx, by = mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y)
        w = mm(t.GetWidth()) / 2
        i0, i1, j0, j1 = idx_box(min(ax, bx) - w - VIA_R, min(ay, by) - w - VIA_R,
                                 max(ax, bx) + w + VIA_R, max(ay, by) + w + VIA_R)
        sub_x, sub_y = xs[i0:i1], ys[j0:j1]
        if t.Type() == pcbnew.PCB_VIA_T:
            on = list(range(nl))
        else:
            ln = b.GetLayerName(t.GetLayer())
            on = [LAYERS.index(ln)] if ln in LAYERS else []
        m_in = seg_mask(sub_x, sub_y, ax, ay, bx, by, w)
        m_tr = seg_mask(sub_x, sub_y, ax, ay, bx, by, w + r_tr)
        m_via = seg_mask(sub_x, sub_y, ax, ay, bx, by, w + VIA_R)
        for li in on:
            if same:
                target[li, j0:j1, i0:i1] |= m_in
            else:
                blocked[li, j0:j1, i0:i1] |= m_tr
        if not same:
            via_block[j0:j1, i0:i1] |= m_via

    # zones
    for z in b.Zones():
        k = z.GetBoundingBox()
        if mm(k.GetRight()) < x0 or mm(k.GetLeft()) > x1 or mm(k.GetBottom()) < y0 or mm(k.GetTop()) > y1:
            continue
        for li, ln in enumerate(LAYERS):
            if not z.IsOnLayer(lid[ln]):
                continue
            if z.GetIsRuleArea():
                if not z.GetDoNotAllowTracks():
                    continue
                poly = z.Outline()
            else:
                if not z.IsFilled():
                    continue
                poly = z.GetFilledPolysList(lid[ln])
            same = bool(new) and z.GetNetname() == new and not z.GetIsRuleArea()
            if not same and not z.GetIsRuleArea() and z.GetNetname() == 'GND' and ln in POUR_OK:
                continue
            i0, i1, j0, j1 = idx_box(mm(k.GetLeft()), mm(k.GetTop()), mm(k.GetRight()), mm(k.GetBottom()))
            for j in range(j0, j1):
                for i in range(i0, i1):
                    if poly.Contains(pcbnew.VECTOR2I(MM(float(xs[i])), MM(float(ys[j])))):
                        if same:
                            target[li, j, i] = True
                        else:
                            blocked[li, j, i] = True
                            if z.GetIsRuleArea() and z.GetDoNotAllowVias():
                                via_block[j, i] = True
    # L3 only inside the target net's own plane
    l3 = LAYERS.index('L3_PWR')
    blocked[l3] |= ~target[l3]

    si, sj = int(round((sx - x0) / STEP)), int(round((sy - y0) / STEP))
    sl = LAYERS.index(src_l)
    blocked[sl, max(0, sj - 3):sj + 4, max(0, si - 3):si + 4] = False  # leave the pad
    if to_pad:  # reach the target pad: open the clearance ring of its neighbours around it
        k = tp.GetBoundingBox()
        i0, i1, j0, j1 = idx_box(mm(k.GetLeft()) - 0.25, mm(k.GetTop()) - 0.25,
                                 mm(k.GetRight()) + 0.25, mm(k.GetBottom()) + 0.25)
        for li, ln in enumerate(LAYERS):
            if tp.IsOnLayer(lid[ln]) and ln != 'L3_PWR':
                blocked[li, j0:j1, i0:i1] = False
    # A*
    goal = target & ~blocked | target
    tj, ti = np.nonzero(goal.any(axis=0))
    if len(ti) == 0:
        return dict(found=False, why='no target copper in the window')
    tx, ty = xs[ti], ys[tj]

    def h(i, j):
        return float(np.min(np.hypot(tx - xs[i], ty - ys[j])))

    start = (sl, sj, si)
    dist = {start: 0.0}
    prev = {}
    pq = [(h(si, sj), 0.0, start)]
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
             (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]
    found = None
    hcache = {}
    while pq:
        f, g, node = heapq.heappop(pq)
        if g > dist.get(node, 1e18):
            continue
        l, j, i = node
        if goal[l, j, i]:
            found = node
            break
        nbrs = []
        for di, dj, c in moves:
            ii, jj = i + di, j + dj
            if 0 <= ii < nx and 0 <= jj < ny and not blocked[l, jj, ii]:
                nbrs.append(((l, jj, ii), c * STEP))
        if not via_block[j, i]:
            for l2 in range(nl):
                if l2 != l and not blocked[l2, j, i]:
                    nbrs.append(((l2, j, i), VIA_COST))
        for nb, c in nbrs:
            ng = g + c
            if ng < dist.get(nb, 1e18):
                dist[nb] = ng
                prev[nb] = node
                key = (nb[1], nb[2])
                if key not in hcache:
                    hcache[key] = h(nb[2], nb[1])
                heapq.heappush(pq, (ng + hcache[key], ng, nb))
    if not found:
        return dict(found=False, why='no path with today\'s copper', sx=sx, sy=sy)
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    length = 0.0
    vias = 0
    for a, c in zip(path, path[1:]):
        if a[0] != c[0]:
            vias += 1
        else:
            length += math.hypot(c[1] - a[1], c[2] - a[2]) * STEP
    layers_used = sorted({LAYERS[p[0]] for p in path}, key=LAYERS.index)
    return dict(found=True, length_mm=round(length, 1), vias=vias, layers=';'.join(layers_used),
                straight_mm=round(math.hypot(xs[found[2]] - sx, ys[found[1]] - sy), 1),
                sx=sx, sy=sy, path=[(xs[p[2]], ys[p[1]], LAYERS[p[0]]) for p in path],
                window=(x0, y0, x1, y1), blocked=blocked, target=target)


def plot(res, name, png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    x0, y0, x1, y1 = res['window']
    fig, axs = plt.subplots(1, len(LAYERS), figsize=(4 * len(LAYERS), 4.2))
    colors = {'L1_SIG': 'tab:red', 'L3_PWR': 'tab:purple', 'L4_PWR_SIG': 'tab:green', 'L6_SIG': 'tab:blue'}
    for li, (ax, ln) in enumerate(zip(axs, LAYERS)):
        img = np.zeros(res['blocked'][li].shape + (3,))
        img[:] = 1.0
        img[res['blocked'][li]] = (0.75, 0.75, 0.75)
        img[res['target'][li]] = (1.0, 0.85, 0.4)
        ax.imshow(img, extent=(x0, x0 + img.shape[1] * STEP, y0 + img.shape[0] * STEP, y0), interpolation='nearest')
        seg = [(x, y) for x, y, l in res['path'] if l == ln]
        if seg:
            ax.plot([p[0] for p in seg], [p[1] for p in seg], '.', ms=1.5, color=colors[ln])
        ax.plot(res['sx'], res['sy'], 'k*', ms=8)
        ax.set_title(ln, fontsize=9)
        ax.tick_params(labelsize=7)
    fig.suptitle(f'{name}: {res["length_mm"]} mm, {res["vias"]} via(s); grey = blocked, gold = target net', fontsize=10)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='kicad-1rx/fmcw3_1rx.kicad_pcb')
    ap.add_argument('--out', default='analysis/11_board_1rx/build')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    b = pcbnew.LoadBoard(a.board)
    rows = []
    placed = {}
    if os.path.exists(PLACE_FIX):
        with open(PLACE_FIX) as fh:
            placed = {(r['part'], r['role']): r for r in csv.DictReader(fh) if r['found'] == 'True'}
    for ch in CHANGES:
        ch = dict(ch)
        if 'part' in ch:  # a pad of a new part, placed by analysis/15_rx1_powerup/fix_space.py
            pl = placed.get((ch['part'], ch['role']))
            if pl is None:
                print('skipped (no placement):', ch['name'])
                continue
            ch['at'] = (float(pl['x']), float(pl['y']), pl['side'])
            ch['ref'], ch['pad'] = ch['part'], ch['role']
            ch.setdefault('old', '')
        r = route(b, ch)
        row = dict(change=ch['name'], pad=f"{ch['ref']}.{ch['pad']}", old_net=ch['old'],
                   new_net=ch.get('new') or '.'.join(ch['to_pad']),
                   found=r['found'], length_mm=r.get('length_mm', ''), straight_mm=r.get('straight_mm', ''),
                   vias=r.get('vias', ''), layers=r.get('layers', ''), note=r.get('why', ''))
        rows.append(row)
        print(row)
        if r['found']:
            png = ch.get('png') or 'route_' + ch['ref'].lower() + '_en.png'
            plot(r, ch['name'], os.path.join(a.out, png))
    with open('analysis/11_board_1rx/route_space.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
