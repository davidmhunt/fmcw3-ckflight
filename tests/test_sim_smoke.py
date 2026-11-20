"""Smoke tests of the simulation tools in the fmcw3-sim image (docker/Dockerfile.sim).

Build: docker build -t fmcw3-sim -f docker/Dockerfile.sim docker/
The tests run each case in that image (repo mounted at /work), or directly when the suite
itself runs inside it. With neither available they skip with a reason.
Fixtures are in tests/sim/.
"""
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "fmcw3-sim"


def _in_sim_image() -> bool:
    return shutil.which("ngspice") is not None and Path("/opt/openEMS").is_dir()


def _image_present() -> bool:
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    return r.returncode == 0


_MODE = "direct" if _in_sim_image() else ("docker" if _image_present() else None)
pytestmark = pytest.mark.skipif(
    _MODE is None,
    reason="sim image '%s' absent (build: docker build -t %s -f docker/Dockerfile.sim docker/)"
    % (IMAGE, IMAGE),
)


def sim(cmd: list[str], timeout: int = 900) -> str:
    """Run cmd in /work (the repo root) in the sim image; return stdout+stderr."""
    if _MODE == "direct":
        full, cwd = cmd, ROOT
    else:
        import os
        full = ["docker", "run", "--rm", "-u", "%d:%d" % (os.getuid(), os.getgid()),
                "-v", "%s:/work" % ROOT, "-w", "/work", IMAGE] + cmd
        cwd = None
    r = subprocess.run(full, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    out = r.stdout + r.stderr
    assert r.returncode == 0, "command failed (%d): %s\n%s" % (r.returncode, cmd, out[-3000:])
    return out


def _meas(out: str, name: str) -> float:
    m = re.search(r"^%s\s*=\s*([-+0-9.eE]+)" % name, out, re.M)
    assert m, "no %s in ngspice output:\n%s" % (name, out[-2000:])
    return float(m.group(1))


def test_ngspice_rc_lowpass_matches_formula():
    out = sim(["ngspice", "-b", "tests/sim/rc_lowpass.cir"])
    fc = 1 / (2 * math.pi * 1e3 * 159.15494e-9)
    assert fc == pytest.approx(1000, rel=1e-4)
    f = lambda x: -10 * math.log10(1 + (x / fc) ** 2)  # noqa: E731
    assert _meas(out, "g_fc") == pytest.approx(f(1e3), abs=0.02)    # -3.01 dB
    assert _meas(out, "g_dec") == pytest.approx(f(1e4), abs=0.02)   # -20.04 dB
    assert _meas(out, "g_lo") == pytest.approx(f(10), abs=0.02)


def test_ngspice_loads_subckt_model_and_runs():
    # Generic macro-model in vendor subckt style; the vendor LT6232 model could not be fetched
    # unattended (see docs/analysis-tools.md).
    out = sim(["ngspice", "-b", "tests/sim/opamp_gain.cir"], timeout=120)
    m = re.search(r"v\(out\)\s*=\s*([-+0-9.eE]+)", out)
    assert m, out[-2000:]
    assert float(m.group(1)) == pytest.approx(10 * 0.2, rel=2e-3)      # closed-loop gain 10, 0.2 V in
    assert _meas(out, "g_lf") == pytest.approx(20.0, abs=0.1)          # 20 dB at 10 kHz


def test_scikit_rf_two_stage_cascade():
    out = sim(["python3", "tests/sim/skrf_cascade.py"], timeout=120)
    assert "PASS cascade_s21_db=17.000" in out


def test_openems_microstrip_about_50_ohm():
    out = sim(["sh", "-c", "mkdir -p /tmp/msl && python3 tests/sim/openems_msl.py /tmp/msl"],
              timeout=1500)
    z = float(re.search(r"Z0_MEAN\s+([0-9.]+)", out).group(1))
    assert 45 <= z <= 55, "extracted microstrip impedance %.1f ohm" % z
    assert float(re.search(r"S11_DB_MAX\s+(-?[0-9.]+)", out).group(1)) < -20   # matched to 50 ohm
    assert float(re.search(r"S21_DB_MEAN\s+(-?[0-9.]+)", out).group(1)) > -0.5  # lossless line
