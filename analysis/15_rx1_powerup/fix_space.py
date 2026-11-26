"""Is there board room for the parts of the proposed rail-order fixes? (1-RX board, read only)

Run: ./run --native python3 analysis/15_rx1_powerup/fix_space.py [--board PCB]
then ./run --native python3 analysis/11_board_1rx/route_space.py (routes each placed pad).

For each new part it searches the 0.1 mm grid within RADIUS of an anchor pad, on the top and
bottom sides and four orientations, for the part's pads plus 0.15 mm clearance, clear of every
existing pad, track and via, keepouts that forbid tracks and filled zones of nets other than GND
(the search of analysis/11_board_1rx/place_space.py, which it imports), and for its courtyard
(the part body: KiCad's library courtyard, or the pads plus 0.25 mm for a chip part) clear of
every other courtyard on that side. Parts are placed one after another and each blocks the next
with its pads and its courtyard; the R993 and R996 spots of place_space.csv are blocked too. Writes place_fix.csv (one row per pad: the part, the pad's role, side and x, y).

Pad geometry: this board's 0402 (0.4 x 0.6 mm, 0.9 mm pitch) and 0805 (0.8 x 1.4 mm, 1.7 mm
pitch) from place_space.py and cap_space.py, and KiCad's SOT-23-5 library footprint for the
supervisor (pin roles are the part's own, so the roles here are the connections needed, not a pinout).
"""
import argparse
import csv
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '11_board_1rx'))
import place_space as ps  # noqa: E402

mm = pcbnew.ToMM
RADIUS = 12.0
OUT = 'analysis/15_rx1_powerup/place_fix.csv'


COURT_MARGIN = 0.25   # courtyard beyond the pads of a two-pad chip part (KiCad's 0402/0805 library courtyards)


def two_pad(pl, pw, pitch, roles):
    return [(roles[0], '1', -pitch / 2, 0.0, pl, pw), (roles[1], '2', pitch / 2, 0.0, pl, pw)]


def two_pad_court(pl, pw, pitch):
    """Courtyard of a two-pad chip part at rotation 0, relative to its centre: (x0, y0, x1, y1)."""
    hx, hy = (pitch + pl) / 2 + COURT_MARGIN, pw / 2 + COURT_MARGIN
    return (-hx, -hy, hx, hy)


def lib_fp(lib, name):
    return pcbnew.FootprintLoad('/usr/share/kicad/footprints/%s.pretty' % lib, name)


def sot23_5(roles, lib='Package_TO_SOT_SMD', name='SOT-23-5'):
    """Pads of a KiCad library footprint (role by pad number)."""
    fp = lib_fp(lib, name)
    out = []
    for p in fp.Pads():
        n = p.GetNumber()
        out.append((roles.get(n, 'NC'), n, mm(p.GetPosition().x), mm(p.GetPosition().y),
                    mm(p.GetSize().x), mm(p.GetSize().y)))
    return out


def court_bbox(fp, layer):
    """Bounding box (mm) of a footprint's courtyard drawing on one layer, or None if it has none."""
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == layer:
            k = g.GetBoundingBox()
            xs += [mm(k.GetLeft()), mm(k.GetRight())]
            ys += [mm(k.GetTop()), mm(k.GetBottom())]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def lib_court(lib, name):
    """Courtyard of a KiCad library footprint at rotation 0, relative to its origin."""
    return court_bbox(lib_fp(lib, name), pcbnew.F_CrtYd)


def courtyards(b):
    """Courtyard rectangles of every footprint on the board, per side (pad envelope where none is drawn)."""
    out = {'F': [], 'B': []}
    for fp in b.GetFootprints():
        side = 'B' if fp.IsFlipped() else 'F'
        r = court_bbox(fp, pcbnew.B_CrtYd if side == 'B' else pcbnew.F_CrtYd)
        if r is None:
            pads = [p.GetBoundingBox() for p in fp.Pads()]
            if not pads:
                continue
            r = (min(mm(k.GetLeft()) for k in pads), min(mm(k.GetTop()) for k in pads),
                 max(mm(k.GetRight()) for k in pads), max(mm(k.GetBottom()) for k in pads))
        out[side].append(r)
    return out


# part: anchor pad, pads (role, number, dx, dy, size x, size y) for rotation 0
def parts():
    return [
        # the recommended 4.7u is 0603/0805 class: searched as an 0805 (the larger; where it fits an 0603 fits)
        dict(part='C_DLY', what='4.7u 0805 (largest footprint of the class), EN node to GND (RC delay on U23 EN)',
             anchor=('U23', '6'), pads=two_pad(0.8, 1.4, 1.7, ('EN', 'GND')), court=two_pad_court(0.8, 1.4, 1.7)),
        dict(part='SUP1', what='SOT-23-5 supervisor on 1V0, open-drain OUT on the U23 EN node', anchor=('U23', '6'),
             pads=sot23_5({'1': 'OUT', '2': 'GND', '3': 'SENSE', '5': 'VDD'}),
             court=lib_court('Package_TO_SOT_SMD', 'SOT-23-5')),
        dict(part='C_HOLD', what='10u 0805 on 3V0 to GND (hold-up)', anchor=('U39', '5'),
             pads=two_pad(0.8, 1.4, 1.7, ('3V0', 'GND')), court=two_pad_court(0.8, 1.4, 1.7)),
        dict(part='R_BLEED', what='0402 bleeder 3V3D to GND', anchor=('U25', '1'),
             pads=two_pad(0.4, 0.6, 0.9, ('3V3D', 'GND')), court=two_pad_court(0.4, 0.6, 0.9)),
        # step 6: the CLK divider (R15 33 -> 68 ohm in place, plus 680 ohm from the CLK node to GND).
        # Anchored at R15 pad 1 (/ADC_CLK): the AD9237 CLK pin is not on kicad-1rx/ until rx1-03.
        dict(part='R_CLK', what='680 ohm 0402 shunt, CLK node to GND (divider with R15 68 ohm)', anchor=('R15', '1'),
             pads=two_pad(0.4, 0.6, 0.9, ('CLK', 'GND')), court=two_pad_court(0.4, 0.6, 0.9)),
        # step 6 F4b: a Schottky clamp from each VIN pin to 3V0 (KiCad D_SOD-323: pad 1 cathode, pad 2 anode).
        # Anchored at R97 pad 1 / R99 pad 1 (the nets Net-(U8-AINA+) / Net-(U8-AINA-), the AD9237 pin side).
        dict(part='D_VINP', what='Schottky SOD-323, VIN+ anode, 3V0 cathode', anchor=('R97', '1'),
             pads=sot23_5({'1': '3V0', '2': 'VIN'}, 'Diode_SMD', 'D_SOD-323'),
             court=lib_court('Diode_SMD', 'D_SOD-323')),
        dict(part='D_VINN', what='Schottky SOD-323, VIN- anode, 3V0 cathode', anchor=('R99', '1'),
             pads=sot23_5({'1': '3V0', '2': 'VIN'}, 'Diode_SMD', 'D_SOD-323'),
             court=lib_court('Diode_SMD', 'D_SOD-323')),
    ]


def place(pads, x, y, rot, side):
    out = []
    for role, num, dx, dy, sx, sy in pads:
        if side == 'B':
            dx = -dx
        a = math.radians(rot)
        px = x + dx * math.cos(a) - dy * math.sin(a)
        py = y + dx * math.sin(a) + dy * math.cos(a)
        w, h = (sx, sy) if rot % 180 == 0 else (sy, sx)
        out.append((role, num, px, py, w, h))
    return out


def place_court(court, x, y, rot, side):
    """The courtyard rectangle of a part placed at x, y (bounding box of its rotated corners)."""
    x0, y0, x1, y1 = court
    pts = []
    for dx, dy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        if side == 'B':
            dx = -dx
        a = math.radians(rot)
        pts.append((x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a)))
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='kicad-1rx/fmcw3_1rx.kicad_pcb')
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    obs, zones = ps.obstacles(b)
    # part bodies: a new part's courtyard may touch but not overlap any other courtyard on its side
    courts = courtyards(b)
    # planned R993 (top) and R996 (bottom) from place_space.csv: 0402 pads
    with open('analysis/11_board_1rx/place_space.csv') as fh:
        for r in csv.DictReader(fh):
            if r['found'] != 'True':
                continue
            s = 'F' if r['side'] == 'top' else 'B'
            x, y, rot = float(r['x']), float(r['y']), int(r['rot'])
            hx, hy = ((0.9 + 0.4) / 2, 0.3) if rot == 0 else (0.3, (0.9 + 0.4) / 2)
            obs[s].append((x - hx - ps.CL, y - hy - ps.CL, x + hx + ps.CL, y + hy + ps.CL))
            courts[s].append(place_court(two_pad_court(0.4, 0.6, 0.9), x, y, rot, s))
    rows = []
    for g in parts():
        fp = b.FindFootprintByReference(g['anchor'][0])
        pad = [p for p in fp.Pads() if p.GetNumber() == g['anchor'][1]][0]
        ax, ay = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        best = None
        n = int(RADIUS * 10)
        for side in 'FB':
            for ix in range(-n, n + 1):
                for iy in range(-n, n + 1):
                    d = math.hypot(ix, iy) * 0.1
                    if d > RADIUS or (best and d >= best[0]):
                        continue
                    x, y = ax + ix * 0.1, ay + iy * 0.1
                    for rot in (0, 90, 180, 270):
                        pp = place(g['pads'], x, y, rot, side)
                        rects = [(px - w / 2 - ps.CL, py - h / 2 - ps.CL, px + w / 2 + ps.CL, py + h / 2 + ps.CL)
                                 for _, _, px, py, w, h in pp]
                        body = (min(r[0] for r in rects), min(r[1] for r in rects),
                                max(r[2] for r in rects), max(r[3] for r in rects))
                        cy = place_court(g['court'], x, y, rot, side)
                        if any(ps.hit(cy, c) for c in courts[side]):
                            continue
                        if ps.free(body, side, obs, zones) and all(ps.free(r, side, obs, zones) for r in rects):
                            best = (d, side, round(x, 1), round(y, 1), rot, body, pp, cy)
                            break
        if best is None:
            rows.append(dict(part=g['part'], what=g['what'], role='', pad='', found=False,
                             anchor='.'.join(g['anchor'])))
            print('no room', g['part'])
            continue
        d, side, x, y, rot, body, pp, cy = best
        obs[side].append(body)
        courts[side].append(cy)
        for role, num, px, py, w, h in pp:
            if role == 'NC':
                continue
            rows.append(dict(part=g['part'], what=g['what'], role=role, pad=num, found=True,
                             anchor='.'.join(g['anchor']), side=side, x=round(px, 2), y=round(py, 2),
                             part_x=x, part_y=y, rot=rot, dist_from_anchor_mm=round(d, 1)))
        print(g['part'], side, x, y, rot, 'at', round(d, 1), 'mm from', '.'.join(g['anchor']))
    keys = ['part', 'what', 'role', 'pad', 'found', 'anchor', 'side', 'x', 'y', 'part_x', 'part_y', 'rot',
            'dist_from_anchor_mm']
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
