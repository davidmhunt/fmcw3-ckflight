"""Is there board room for the parts of the proposed rail-order fixes? (1-RX board, read only)

Run: ./run --native python3 analysis/15_rx1_powerup/fix_space.py [--board PCB]
then ./run --native python3 analysis/11_board_1rx/route_space.py (routes each placed pad).

For each new part it searches the 0.1 mm grid within RADIUS of an anchor pad, on the top and
bottom sides and four orientations, for the part's pads plus 0.15 mm clearance, clear of every
existing pad, track and via, keepouts that forbid tracks and filled zones of nets other than GND
(the search of analysis/11_board_1rx/place_space.py, which it imports). Parts are placed one
after another and each blocks the next; the R993 and R996 spots of place_space.csv are blocked
too. Writes place_fix.csv (one row per pad: the part, the pad's role, side and x, y).

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


def two_pad(pl, pw, pitch, roles):
    return [(roles[0], '1', -pitch / 2, 0.0, pl, pw), (roles[1], '2', pitch / 2, 0.0, pl, pw)]


def sot23_5(roles):
    fp = pcbnew.FootprintLoad('/usr/share/kicad/footprints/Package_TO_SOT_SMD.pretty', 'SOT-23-5')
    out = []
    for p in fp.Pads():
        n = p.GetNumber()
        out.append((roles.get(n, 'NC'), n, mm(p.GetPosition().x), mm(p.GetPosition().y),
                    mm(p.GetSize().x), mm(p.GetSize().y)))
    return out


# part: anchor pad, pads (role, number, dx, dy, size x, size y) for rotation 0
def parts():
    return [
        dict(part='C_DLY', what='1u 0402, EN node to GND (RC delay on U23 EN)', anchor=('U23', '6'),
             pads=two_pad(0.4, 0.6, 0.9, ('EN', 'GND'))),
        dict(part='SUP1', what='SOT-23-5 supervisor on 1V0, open-drain OUT on the U23 EN node', anchor=('U23', '6'),
             pads=sot23_5({'1': 'OUT', '2': 'GND', '3': 'SENSE', '5': 'VDD'})),
        dict(part='C_HOLD', what='10u 0805 on 3V0 to GND (hold-up)', anchor=('U39', '5'),
             pads=two_pad(0.8, 1.4, 1.7, ('3V0', 'GND'))),
        dict(part='R_BLEED', what='0402 bleeder 3V3D to GND', anchor=('U25', '1'),
             pads=two_pad(0.4, 0.6, 0.9, ('3V3D', 'GND'))),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='kicad-1rx/fmcw3_1rx.kicad_pcb')
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    obs, zones = ps.obstacles(b)
    # planned R993 (top) and R996 (bottom) from place_space.csv: 0402 pads
    with open('analysis/11_board_1rx/place_space.csv') as fh:
        for r in csv.DictReader(fh):
            if r['found'] != 'True':
                continue
            s = 'F' if r['side'] == 'top' else 'B'
            x, y, rot = float(r['x']), float(r['y']), int(r['rot'])
            hx, hy = ((0.9 + 0.4) / 2, 0.3) if rot == 0 else (0.3, (0.9 + 0.4) / 2)
            obs[s].append((x - hx - ps.CL, y - hy - ps.CL, x + hx + ps.CL, y + hy + ps.CL))
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
                        if ps.free(body, side, obs, zones) and all(ps.free(r, side, obs, zones) for r in rects):
                            best = (d, side, round(x, 1), round(y, 1), rot, body, pp)
                            break
        if best is None:
            rows.append(dict(part=g['part'], what=g['what'], role='', pad='', found=False,
                             anchor='.'.join(g['anchor'])))
            print('no room', g['part'])
            continue
        d, side, x, y, rot, body, pp = best
        obs[side].append(body)
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
