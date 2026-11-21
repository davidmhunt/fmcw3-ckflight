"""LTspice (under Wine) through spicelib, run inside the fmcw3-sim image.

Run it under a virtual display:  xvfb-run -a python3 tests/sim/ltspice_smoke.py WORKDIR [TI_ZIP]
Prints one line per case:  RESULT <name> PASS|FAIL <detail>   (detail carries the error text).
tests/test_sim_smoke.py runs this once and asserts on the lines.

Cases
  rc_ltspice       RC low-pass AC sweep in LTspice vs the formula
  adi_lt6231       ADI LT6231 from LTspice's bundled LTC2.lib: gain-of-10 amplifier in LTspice
  adi_in_ngspice   same model in ngspice (expected to fail: LTspice-only A-devices)
  ti_ltspice       TI LP5907-1.8 PSpice model (public zip) in LTspice
  ti_ngspice       same model in ngspice (ngbehavior=psa)
  ti_compare       the two engines' Vout(t) compared
  mixed_ti_ldo_adi_opamp
                   the TI LDO feeding the ADI op-amp in one LTspice netlist
  ti_enc_ltspice / ti_enc_ngspice
                   TI LMR51420XF PSpice model (encrypted by TI) in each engine; failures recorded
"""
import math
import os
import sys
import tempfile
import zipfile
from pathlib import Path

WORK = Path(sys.argv[1]).resolve()
TI_ZIPS = {Path(a).name: Path(a) for a in sys.argv[2:]}

PREFIX_BAKED = Path(os.environ.get("LTSPICE_PREFIX", "/opt/wineprefix"))
LT_DIR = PREFIX_BAKED / "drive_c/Program Files/ADI/LTspice"


def setup_wine():
    """The baked prefix belongs to root, and Wine insists the prefix dir is owned by the
    caller. Make our own top-level dir that symlinks into the (world-writable) baked one."""
    pre = WORK / "wineprefix"
    pre.mkdir(parents=True, exist_ok=True)
    for p in list(PREFIX_BAKED.iterdir()):
        link = pre / p.name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(p)
    os.environ.update(WINEPREFIX=str(pre), WINEDEBUG="-all", USER="root",
                      LTSPICEFOLDER=str(LT_DIR), LTSPICEEXECUTABLE="LTspice.exe")


setup_wine()
WORK.mkdir(parents=True, exist_ok=True)

from spicelib import RawRead, SimRunner  # noqa: E402
from spicelib.simulators.ltspice_simulator import LTspice  # noqa: E402
from spicelib.simulators.ngspice_simulator import NGspiceSimulator  # noqa: E402

SIM = {"ltspice": LTspice, "ngspice": NGspiceSimulator}
LIB = PREFIX_BAKED / "drive_c/users/root/AppData/Local/LTspice/lib"


def result(name, ok, detail=""):
    detail = " ".join(str(detail).split())[:600]
    print("RESULT %s %s %s" % (name, "PASS" if ok else "FAIL", detail), flush=True)


def run(engine, netlist_text, tag, timeout=240):
    """Run a netlist through spicelib; return (raw, log text). Raise with the log on failure."""
    d = WORK / tag
    d.mkdir(exist_ok=True)
    (WORK / "src").mkdir(exist_ok=True)
    net = WORK / "src" / (tag + ".net")
    net.write_text(netlist_text)
    runner = SimRunner(output_folder=str(d), simulator=SIM[engine])
    # The path, not a SpiceEditor: the editor parses included vendor libs and chokes on some.
    rawf, logf = runner.run_now(str(net), run_filename=tag + ".net", timeout=timeout)
    # LTspice also writes <tag>.op.raw (the operating point); the sweep is in <tag>.raw.
    main = d / (tag + ".raw")
    if main.exists():
        rawf = main
    log = Path(logf).read_text(errors="replace") if logf and Path(logf).exists() else ""
    if not rawf or not Path(rawf).exists():
        raise RuntimeError("no raw file from %s; log: %s" % (engine, log[-1500:]))
    return RawRead(str(rawf), dialect="ngspice" if engine == "ngspice" else None), log


def trace(raw, name):
    names = raw.get_trace_names()
    # The sweep variable is the first trace (frequency or time); an .op raw file has none.
    axis = raw.get_trace(names[0]).get_wave(0) if names[0] in ("frequency", "time") else None
    by_lower = {n.lower(): n for n in names}   # ngspice writes v(out), LTspice V(out)
    return raw.get_trace(by_lower[name.lower()]).get_wave(0), axis


RC = """* RC low-pass, fc = 1/(2 pi R C) = 1 kHz
V1 in 0 AC 1
R1 in out 1k
C1 out 0 159.15494n
.ac dec 10 10 100k
.end
"""


def case_rc():
    raw, _ = run("ltspice", RC, "rc")
    y, f = trace(raw, "V(out)")
    fc = 1 / (2 * math.pi * 1e3 * 159.15494e-9)
    worst = 0.0
    for yi, fi in zip(y, f):
        want = -10 * math.log10(1 + (abs(fi) / fc) ** 2)
        worst = max(worst, abs(20 * math.log10(abs(yi)) - want))
    g1k = [20 * math.log10(abs(yi)) for yi, fi in zip(y, f) if abs(abs(fi) - 1000) < 1][0]
    result("rc_ltspice", worst < 0.02 and abs(g1k + 3.01) < 0.02,
           "%d points, worst error %.2e dB, gain at 1 kHz %.3f dB" % (len(y), worst, g1k))


# Non-inverting gain of 10 (R1 9k to the inverting input, 1k to ground), +/-2.5 V supplies.
# LT6231 pins: 1 in+, 2 in-, 3 out, 4 V+, 5 V-. (The LT6232 symbol in LTspice's library points
# at this subckt, LTC2.lib.) The model's input range is limited like the part's: with V- = 0 an
# input of 1 V is clamped (Vout 1.27 V for a follower), so the test biases at mid-supply.
ADI = """* LT6231 gain of 10
Vcc vcc 0 2.5
Vee vee 0 -2.5
Vin in 0 0.2 AC 1
X1 in fb out vcc vee LT6231
R1 out fb 9k
R2 fb 0 1k
.lib LTC2.lib
{analysis}
.end
"""


def case_adi():
    try:
        raw, _ = run("ltspice", ADI.format(analysis=".op"), "adi_op")
        vo = float(trace(raw, "V(out)")[0][0])
        result("adi_lt6231_dc", abs(vo - 2.0) < 0.05, "Vout = %.4f V (want 2.0 V)" % vo)
        raw, _ = run("ltspice", ADI.format(analysis=".ac dec 10 10 1Meg"), "adi")
        y, f = trace(raw, "V(out)")
        g = [20 * math.log10(abs(yi)) for yi, fi in zip(y, f) if abs(abs(fi) - 1000) < 1][0]
        result("adi_lt6231", abs(g - 20.0) < 0.1, "gain at 1 kHz %.3f dB (want 20 dB)" % g)
    except Exception as e:  # noqa: BLE001
        result("adi_lt6231", False, e)
    try:
        # ngspice needs the library by path; LTspice resolves LTC2.lib itself.
        run("ngspice", ADI.format(analysis=".op").replace(".lib LTC2.lib", ".lib %s/sub/LTC2.lib" % LIB), "adi_ng")
        result("adi_in_ngspice", True, "loaded and ran")
    except Exception as e:  # noqa: BLE001
        result("adi_in_ngspice", False, e)


# TI LDO fed by a 3.6 V ramp, 180 ohm load (10 mA), EN tied to VIN. Subckt pins: VIN VOUT VEN GND.
TI_NET = """* TI LP5907 1.8 V LDO start-up
Vin vin 0 PWL(0 0 100u 3.6)
Cin vin 0 1u
Cout out 0 1u
Rl out 0 180
X1 vin out vin 0 {subckt}
{inc}
.tran 1u 2m
.end
"""


MIXED = """* TI LP5907 (PSpice model) feeding an ADI LT6231 follower, one LTspice netlist
Vin vin 0 PWL(0 0 100u 3.6)
Cin vin 0 1u
Cout out 0 1u
Rl out 0 180
X1 vin out vin 0 LP5907_1P8
{inc}
Vcc vcc 0 3.3
Vee vee 0 -3.3
X2 out buf buf vcc vee LT6231
Rb buf 0 10k
.lib LTC2.lib
.tran 1u 2m
.end
"""


def unpack(zname):
    z = TI_ZIPS.get(zname)
    if z is None or not z.is_file():
        return None
    d = WORK / ("unz_" + zname)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(d)
    return d


def model_file(d, suffix):
    for p in d.rglob("*"):
        if p.is_file() and p.suffix.lower() == suffix:
            return p
    return None


def norm(src, dst):
    """Copy a model with LF line ends (TI ships CRLF)."""
    dst.write_text(Path(src).read_bytes().decode("latin-1").replace("\r\n", "\n"))
    return dst


def at(t, y, x):
    """Linear interpolation of the wave y(t) at time x."""
    best = min(range(len(t)), key=lambda i: abs(abs(t[i]) - x))
    return float(abs(y[best]))


def case_ti():
    d = unpack("snvmap9.zip")
    if d is None:
        result("ti_ltspice", False, "snvmap9.zip not supplied (fetch via tools/fetch_sources.py)")
        return
    lib = norm(model_file(d, ".lib"), WORK / "LP5907_1P8.lib")
    net = TI_NET.format(subckt="LP5907_1P8", inc=".include %s" % lib)
    waves = {}
    for engine in ("ltspice", "ngspice"):
        text = net
        if engine == "ngspice":
            text = net.replace(".tran", ".options ngbehavior=psa\n.tran")
        try:
            raw, _ = run(engine, text, "ti_" + engine)
            y, t = trace(raw, "V(out)")
            waves[engine] = (t, y)
            result("ti_" + engine, abs(at(t, y, 2e-3) - 1.8) < 0.05,
                   "Vout(2 ms) = %.4f V (want 1.8)" % at(t, y, 2e-3))
        except Exception as e:  # noqa: BLE001
            result("ti_" + engine, False, e)
    # TI LDO and ADI op-amp in one LTspice netlist: the LDO output is buffered by an LT6231
    # follower on +/-3.3 V rails (on +/-2.5 V the op-amp's input range clips 1.8 V to 1.70 V).
    try:
        mixed = MIXED.format(inc=".include %s" % lib)
        raw, _ = run("ltspice", mixed, "mixed")
        y, t = trace(raw, "V(buf)")
        yl, _ = trace(raw, "V(out)")
        result("mixed_ti_ldo_adi_opamp", abs(at(t, y, 2e-3) - 1.8) < 0.05,
               "LDO out %.4f V, LT6231 buffer out %.4f V at 2 ms (want 1.8)"
               % (at(t, yl, 2e-3), at(t, y, 2e-3)))
    except Exception as e:  # noqa: BLE001
        result("mixed_ti_ldo_adi_opamp", False, e)
    if len(waves) == 2:
        worst = 0.0
        for x in (5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3):
            worst = max(worst, abs(at(*waves["ltspice"], x) - at(*waves["ngspice"], x)))
        result("ti_compare", worst < 0.02, "max |Vout_ltspice - Vout_ngspice| = %.4f V "
               "at 6 times 50 us..2 ms" % worst)
    else:
        result("ti_compare", False, "an engine failed: %s" % sorted(waves))


def case_enc():
    d = unpack("slum825.zip")
    if d is None:
        result("ti_enc_ltspice", False, "slum825.zip not supplied")
        return
    lib = model_file(d, ".lib")
    # Interface comment in the file names the subckt; just ask each engine to load it.
    txt = lib.read_bytes().decode("latin-1")
    sub = "LMR51420XF"
    net = ("* LMR51420XF load test\nV1 vin 0 12\nX1 vin 0 vin 0 sw fb 0 %s\n"
           ".include %s\n.op\n.end\n") % (sub, norm(lib, WORK / "LMR51420XF.lib"))
    for engine in ("ltspice", "ngspice"):
        try:
            run(engine, net, "enc_" + engine, timeout=120)
            result("ti_enc_" + engine, True, "ran (%d byte file)" % len(txt))
        except Exception as e:  # noqa: BLE001
            result("ti_enc_" + engine, False, e)


if __name__ == "__main__":
    for fn in (case_rc, case_adi, case_ti, case_enc):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            result(fn.__name__, False, repr(e))
