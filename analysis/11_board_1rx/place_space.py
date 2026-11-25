"""Is there board space for a new small part next to a given pad? (1-RX board, read only)

Run: ./run --native python3 analysis/11_board_1rx/place_space.py [--board PCB]

For each entry of PARTS: search 0.1 mm grid positions within RADIUS of the anchor pad, on the
top and bottom sides, both orientations, for the part's two pads plus 0.15 mm clearance, clear of
every existing pad, track and via, keepouts that forbid tracks, and filled zones of nets other
than GND (a GND pour re-flows around a new part). Several parts in one group are placed one after
another, each blocking the next. Prints the nearest free spots and writes place_space.csv.
"""
import argparse
import csv

import pcbnew

mm = pcbnew.ToMM
CL = 0.15
RADIUS = 6.0
P0402 = (0.4, 0.6, 0.9)    # this board's SMD_0402: pad length, pad width, pitch (mm)

# group: parts placed together near one anchor pad
PARTS = [
    dict(group='EN isolation at the 3V0 tap (rx1-seq-r)', anchor=('U39', '5'),
         parts=[('R993', P0402), ('R996', P0402)]),
]


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def obstacles(b):
    lid = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}
    obs = {'F': [], 'B': []}
    for p in b.GetPads():
        k = p.GetBoundingBox()
        r = (mm(k.GetLeft()) - CL, mm(k.GetTop()) - CL, mm(k.GetRight()) + CL, mm(k.GetBottom()) + CL)
        for s in 'FB':
            if p.IsOnLayer(lid[s]):
                obs[s].append(r)
    for t in b.GetTracks():
        k = t.GetBoundingBox()
        r = (mm(k.GetLeft()) - CL, mm(k.GetTop()) - CL, mm(k.GetRight()) + CL, mm(k.GetBottom()) + CL)
        if t.Type() == pcbnew.PCB_VIA_T:
            obs['F'].append(r)
            obs['B'].append(r)
        elif t.GetLayer() == pcbnew.F_Cu:
            obs['F'].append(r)
        elif t.GetLayer() == pcbnew.B_Cu:
            obs['B'].append(r)
    zones = {'F': [], 'B': []}
    for z in b.Zones():
        for s in 'FB':
            if not z.IsOnLayer(lid[s]):
                continue
            if z.GetIsRuleArea():
                if z.GetDoNotAllowTracks() or z.GetDoNotAllowFootprints():
                    zones[s].append(z.Outline())
            elif z.GetNetname() != 'GND' and z.IsFilled():
                zones[s].append(z.GetFilledPolysList(lid[s]))
    return obs, zones


def free(rect, side, obs, zones):
    if any(hit(rect, o) for o in obs[side]):
        return False
    pts = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3]),
           ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)]
    for poly in zones[side]:
        for x, y in pts:
            if poly.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))):
                return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='kicad-1rx/fmcw3_1rx.kicad_pcb')
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    obs, zones = obstacles(b)
    rows = []
    for g in PARTS:
        fp = b.FindFootprintByReference(g['anchor'][0])
        pad = [p for p in fp.Pads() if p.GetNumber() == g['anchor'][1]][0]
        ax, ay = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        for ref, (pl, pw, pitch) in g['parts']:
            best = None
            for side in 'FB':
                for ix in range(-int(RADIUS * 10), int(RADIUS * 10) + 1):
                    for iy in range(-int(RADIUS * 10), int(RADIUS * 10) + 1):
                        x, y = ax + ix * 0.1, ay + iy * 0.1
                        d = (ix * ix + iy * iy) ** 0.5 * 0.1
                        if d > RADIUS or (best and d >= best[0]):
                            continue
                        for rot in (0, 90):
                            hx = (pitch + pl) / 2 if rot == 0 else pw / 2
                            hy = pw / 2 if rot == 0 else (pitch + pl) / 2
                            rect = (x - hx - CL, y - hy - CL, x + hx + CL, y + hy + CL)
                            if free(rect, side, obs, zones):
                                best = (d, side, round(x, 1), round(y, 1), rot, rect)
                                break
            if best is None:
                row = dict(group=g['group'], part=ref, anchor='.'.join(g['anchor']), found=False)
            else:
                d, side, x, y, rot, rect = best
                obs[side].append(rect)  # the next part of the group must avoid this one
                row = dict(group=g['group'], part=ref, anchor='.'.join(g['anchor']), found=True,
                           side='top' if side == 'F' else 'bottom', x=x, y=y, rot=rot,
                           dist_from_anchor_mm=round(d, 1))
            rows.append(row)
            print(row)
    keys = ['group', 'part', 'anchor', 'found', 'side', 'x', 'y', 'rot', 'dist_from_anchor_mm']
    with open('analysis/11_board_1rx/place_space.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
