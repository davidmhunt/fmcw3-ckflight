"""openEMS microstrip smoke test: a straight line sized for ~50 ohm on h=1.0 mm, er=4.3.

Follows the openEMS MSL_NotchFilter tutorial without the stub. Hammerstad-Jensen gives
w = 1.95 mm -> 50 ohm. The MSL port extracts the line impedance (V/I at the measurement plane);
prints "Z0_MEAN <ohm>" over 1-5 GHz. Usage: openems_msl.py WORKDIR
"""
import sys

import numpy as np
from CSXCAD import ContinuousStructure
from openEMS import openEMS
from openEMS.physical_constants import C0

work = sys.argv[1]
unit = 1e-3
h, er, w, L = 1.0, 4.3, 1.95, 30.0   # mm
f_max = 6e9

FDTD = openEMS(NrTS=60000, EndCriteria=1e-4)
FDTD.SetGaussExcite(f_max / 2, f_max / 2)
FDTD.SetBoundaryCond(["PML_8", "PML_8", "MUR", "MUR", "PEC", "MUR"])
CSX = ContinuousStructure()
FDTD.SetCSX(CSX)
mesh = CSX.GetGrid()
mesh.SetDeltaUnit(unit)

res = C0 / (f_max * np.sqrt(er)) / unit / 50
third = np.array([2 * res / 3, -res / 3]) / 4

mesh.AddLine("x", [-L, L])
mesh.SmoothMeshLines("x", res)

mesh.AddLine("y", 0)
mesh.AddLine("y", w / 2 + third)
mesh.AddLine("y", -w / 2 - third)
mesh.SmoothMeshLines("y", res / 4)
mesh.AddLine("y", [-15 * w, 15 * w])
mesh.SmoothMeshLines("y", res)

mesh.AddLine("z", np.linspace(0, h, 5))
mesh.AddLine("z", 8)
mesh.SmoothMeshLines("z", res)

sub = CSX.AddMaterial("sub", epsilon=er)
sub.AddBox([mesh.GetLine("x", 0), mesh.GetLine("y", 0), 0],
           [mesh.GetLine("x", -1), mesh.GetLine("y", -1), h])

pec = CSX.AddMetal("pec")
port = [None, None]
port[0] = FDTD.AddMSLPort(1, pec, [-L, -w / 2, h], [0, w / 2, 0], "x", "z",
                          excite=-1, FeedShift=10 * res, MeasPlaneShift=L / 3, priority=10)
port[1] = FDTD.AddMSLPort(2, pec, [L, -w / 2, h], [0, w / 2, 0], "x", "z",
                          MeasPlaneShift=L / 3, priority=10)

FDTD.Run(work, cleanup=True)

f = np.linspace(1e9, 5e9, 41)
for p in port:
    p.CalcPort(work, f)          # no ref_impedance: Z_ref is the line's own impedance
z = np.real(port[0].Z_ref)
print("Z0_MEAN %.2f" % np.mean(z))
for p in port:
    p.CalcPort(work, f, ref_impedance=50)
s11 = port[0].uf_ref / port[0].uf_inc
s21 = port[1].uf_ref / port[0].uf_inc
print("S11_DB_MAX %.1f" % np.max(20 * np.log10(np.abs(s11))))
print("S21_DB_MEAN %.2f" % np.mean(20 * np.log10(np.abs(s21))))
