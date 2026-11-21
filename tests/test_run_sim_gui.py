"""./run --sim-gui --print: the docker command, without running docker or touching xhost."""
import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELPER = ["bash", "/work/tools/sim_gui_ltspice.sh"]


def printed(*args, display=":1"):
    env = {**os.environ, "DISPLAY": display}
    out = subprocess.run([str(ROOT / "run"), "--sim-gui", "--print", *args], env=env,
                         capture_output=True, text=True, check=True).stdout
    return shlex.split(out)


def after_image(c):
    return c[c.index("fmcw3-sim") + 1:]


def test_generic_command():
    c = printed("xclock")
    assert c[:2] == ["docker", "run"]
    assert after_image(c) == ["xclock"]
    assert "/tmp/.X11-unix:/tmp/.X11-unix" in c
    assert "DISPLAY=:1" in c
    assert f"{os.getuid()}:{os.getgid()}" in c
    assert f"{ROOT}:/work" in c


def test_ipc_host_for_x_shared_memory():
    assert "--ipc=host" in printed("xclock")


def test_dpi_default_and_override(monkeypatch):
    monkeypatch.delenv("SIM_GUI_DPI", raising=False)
    assert "SIM_GUI_DPI=144" in printed("xclock")
    monkeypatch.setenv("SIM_GUI_DPI", "192")
    assert "SIM_GUI_DPI=192" in printed("xclock")


def test_helper_sets_logpixels_in_per_run_prefix():
    text = (ROOT / "tools" / "sim_gui_ltspice.sh").read_text()
    assert "LogPixels" in text and "Control Panel\\Desktop" in text and "SIM_GUI_DPI" in text


def test_ltspice_net_example_is_ltspice_syntax():
    net = (ROOT / "tests/sim/rc_lowpass_ltspice.net").read_text()
    assert ".control" not in net and ".ac " in net


def test_ltspice_shortcut_with_file():
    c = printed("ltspice", "tests/sim/rc_lowpass.cir")
    assert after_image(c) == HELPER + ["tests/sim/rc_lowpass.cir"]


def test_ltspice_shortcut_without_file():
    assert after_image(printed("ltspice")) == HELPER


def test_x_access_is_own_user_only_and_revoked():
    text = (ROOT / "run").read_text()
    assert 'grant="SI:localuser:$(id -un)"' in text
    assert 'xhost "+$grant"' in text
    assert 'trap \'xhost "-$grant"' in text
    assert "xhost +\n" not in text and "xhost + " not in text
