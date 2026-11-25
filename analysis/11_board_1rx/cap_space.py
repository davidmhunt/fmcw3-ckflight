"""Run: ./run --native python3 analysis/11_board_1rx/cap_space.py (needs pcbnew; read only).

Where can the 1-RX 10 uF caps (0805) go next to the AD9237 pins they serve?

Assumptions (stated in the answer): the AD9237 LFCSP-32 sits at the old U8 centre, rotated so its
pins 25-32 (VIN, REFT/REFB, AVDD) face the existing input network (+y); KiCad's
LFCSP-32-1EP_5x5mm footprint geometry; parts not fitted on 1-RX removed; U8's own tracks and vias
inside the old 9x9 courtyard are rerouted, everything else stays.
"""
import csv
import sys
import pcbnew

PCB = sys.argv[1] if len(sys.argv) > 1 else "kicad-1rx/fmcw3_1rx.kicad_pcb"
OUT = sys.argv[2] if len(sys.argv) > 2 else "analysis/11_board_1rx/cap_space.csv"
mm, MM = pcbnew.ToMM, pcbnew.FromMM
b = pcbnew.LoadBoard(PCB)
u8 = b.FindFootprintByReference('U8')
c = u8.GetPosition()
cx, cy = mm(c.x), mm(c.y)

dnp = set()
for r in csv.DictReader(open('parts/rx1_changes.csv')):
    if r['kind'] == 'dnp' and r['status'] == 'decided':
        dnp |= set(r['refs'].split(';'))
dnp |= {'R21'}
u8nets = {p.GetNetname() for p in u8.Pads()}
CLR = 0.15  # mm clearance kept around every obstacle (rule 0.1 + margin)

# New U8: KiCad LFCSP footprint rotated 180 deg about the old centre.
lf = pcbnew.FootprintLoad('/usr/share/kicad/footprints/Package_CSP.pretty',
                          'LFCSP-32-1EP_5x5mm_P0.5mm_EP3.25x3.25mm')
pins = {}
for p in lf.Pads():
    if p.GetNumber() in ('', '33'):
        continue
    x, y = -mm(p.GetPosition().x), -mm(p.GetPosition().y)
    w, h = mm(p.GetSize().x), mm(p.GetSize().y)
    pins[int(p.GetNumber())] = (x, y, w, h)
U8C = 3.05  # half courtyard
obst_ep = (-2.0, -2.0, 2.0, 2.0)

NAMES = {1: 'MODE2', 2: 'CLK', 3: 'OE', 4: 'PDWN', 5: 'GC', 6: 'DNC', 7: 'D0', 8: 'D1', 9: 'D2', 10: 'D3',
         11: 'D4', 12: 'D5', 13: 'D6', 14: 'D7', 15: 'DGND', 16: 'DRVDD', 17: 'D8', 18: 'D9', 19: 'D10',
         20: 'D11', 21: 'OTR', 22: 'MODE', 23: 'SENSE', 24: 'VREF', 25: 'REFB', 26: 'REFT', 27: 'AVDD',
         28: 'AGND', 29: 'VIN+', 30: 'VIN-', 31: 'AGND', 32: 'AVDD'}


def rect(x0, y0, x1, y1, m=0.0):
    return (min(x0, x1) - m, min(y0, y1) - m, max(x0, x1) + m, max(y0, y1) + m)


def hit(a, b_):
    return a[0] < b_[2] and b_[0] < a[2] and a[1] < b_[3] and b_[1] < a[3]


obst = {'F': [], 'B': []}
for f in b.GetFootprints():
    ref = f.GetReference()
    if ref == 'U8' or ref in dnp:
        continue
    side = 'B' if f.GetLayer() == pcbnew.B_Cu else 'F'
    for p in f.Pads():
        bb = p.GetBoundingBox()
        r = rect(mm(bb.GetLeft()) - cx, mm(bb.GetTop()) - cy, mm(bb.GetRight()) - cx, mm(bb.GetBottom()) - cy, CLR)
        if abs(r[0]) < 15 and abs(r[1]) < 15:
            obst[side].append((r, ref))
    # body: pad bbox of the whole part plus 0.1 (no courtyards on these library parts)
    bb = f.GetBoundingBox(False, False)
for t in b.GetTracks():
    bb = t.GetBoundingBox()
    r = rect(mm(bb.GetLeft()) - cx, mm(bb.GetTop()) - cy, mm(bb.GetRight()) - cx, mm(bb.GetBottom()) - cy, CLR)
    if not (abs(r[0]) < 15 and abs(r[1]) < 15):
        continue
    inside_old = max(abs(r[0]), abs(r[2]), abs(r[1]), abs(r[3])) < 5.6
    if t.GetNetname() in u8nets and inside_old:
        continue  # U8 fan-out, rerouted with the new footprint
    name = f'{"via" if t.Type() == pcbnew.PCB_VIA_T else "track"} {t.GetNetname()}'
    if t.Type() == pcbnew.PCB_VIA_T:
        obst['F'].append((r, name))
        obst['B'].append((r, name))
    elif t.GetLayer() == pcbnew.F_Cu:
        obst['F'].append((r, name))
    elif t.GetLayer() == pcbnew.B_Cu:
        obst['B'].append((r, name))

# Fan-out corridors of the new U8 signal pins (top side): 0.4 mm wide, 1.6 mm out from the pad.
corr = []
for n, (x, y, w, h) in pins.items():
    if NAMES[n] in ('AGND', 'DGND', 'DNC'):
        continue
    if abs(y) > abs(x):  # top/bottom row
        s = 1 if y > 0 else -1
        corr.append((rect(x - 0.2, y, x + 0.2, y + s * 1.6 + s * h / 2), n))
    else:
        s = 1 if x > 0 else -1
        corr.append((rect(x, y - 0.2, x + s * 1.6 + s * w / 2, y + 0.2), n))

PAD_L, PAD_W, PITCH = 0.8, 1.4, 1.7  # this board's SMD_0805 pads
TARGETS = [('C993', 24), ('C994', 27), ('C994', 32), ('C995', 16)]
rows = []
for cap, pin in TARGETS:
    px, py, pw, ph = pins[pin]
    best = []
    for side in ('F', 'B'):
        for ix in range(-80, 81):
            for iy in range(-80, 81):
                x, y = ix * 0.1 + px, iy * 0.1 + py
                for rot in (0, 90):
                    if rot == 0:   # pads along x
                        pads = [rect(x - PITCH / 2 - PAD_L / 2, y - PAD_W / 2, x - PITCH / 2 + PAD_L / 2, y + PAD_W / 2),
                                rect(x + PITCH / 2 - PAD_L / 2, y - PAD_W / 2, x + PITCH / 2 + PAD_L / 2, y + PAD_W / 2)]
                    else:
                        pads = [rect(x - PAD_W / 2, y - PITCH / 2 - PAD_L / 2, x + PAD_W / 2, y - PITCH / 2 + PAD_L / 2),
                                rect(x - PAD_W / 2, y + PITCH / 2 - PAD_L / 2, x + PAD_W / 2, y + PITCH / 2 + PAD_L / 2)]
                    body = rect(min(p[0] for p in pads), min(p[1] for p in pads),
                                max(p[2] for p in pads), max(p[3] for p in pads), 0.1)
                    if side == 'F' and hit(body, (-U8C, -U8C, U8C, U8C)):
                        continue
                    if side == 'B' and hit(body, obst_ep):
                        continue
                    if any(hit(body, o) for o, _ in obst[side]):
                        continue
                    if side == 'F' and any(hit(body, r) for r, n in corr if n != pin):
                        continue
                    # distance: nearest cap pad edge to the pin pad edge (straight line)
                    pin_r = rect(px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2)
                    def gap(a):
                        dx = max(a[0] - pin_r[2], pin_r[0] - a[2], 0)
                        dy = max(a[1] - pin_r[3], pin_r[1] - a[3], 0)
                        return (dx * dx + dy * dy) ** 0.5
                    d = min(gap(p) for p in pads)
                    best.append((round(d, 2), side, round(x, 1), round(y, 1), rot))
    best.sort()
    seen = []
    best = [x for x in best if x[1] == 'F'][:400] + [x for x in best if x[1] == 'B'][:400]
    for d, side, x, y, rot in best:
        if any(s == side and abs(x - sx) < 1.0 and abs(y - sy) < 1.0 for _, s, sx, sy, _ in seen):
            continue
        seen.append((d, side, x, y, rot))
        if sum(1 for q in seen if q[1] == side) > 3:
            seen.pop()
    for d, side, x, y, rot in seen:
        rows.append(dict(cap=cap, pin=f'{pin} {NAMES[pin]}', pin_xy=f'{px:.2f},{py:.2f}', side=side,
                         x=x, y=y, rot=rot, gap_mm=d))

with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r)
print('obstacles F', len(obst['F']), 'B', len(obst['B']))
