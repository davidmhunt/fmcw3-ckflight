"""rx1-05 step 5: the pass check on fixture waveforms, the order map on a fixture netlist, and the LD39200
ramp fit against the points read from the datasheet figure (st-ld39200-datasheet p.13, Figure 23).

No simulator and no KiCad: the waveforms are built here, the netlist is a dict of components and nets in the
form rx2_dnp.netlist() returns.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1] / "analysis" / "15_rx1_powerup"


def _load(name):
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "11_board_1rx"))
    spec = importlib.util.spec_from_file_location("rx1pu_" + name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PC = _load("passcheck")
SEQ = _load("sequence")
SIM = _load("powerup_sim")


# ---- waveform fixtures ------------------------------------------------------------------------
T = np.linspace(0.0, 0.040, 40001)          # 40 ms, 1 us steps


def ramp(t0, t_rise, v_end):
    """0 until t0, linear to v_end over t_rise, then flat."""
    return np.clip((T - t0) / t_rise, 0.0, 1.0) * v_end


NOMINAL = {"3V0": 3.0, "3V3A": 3.3, "1V8": 1.8, "3V3D": 3.3, "1V0": 1.008}


def good_rails():
    """1V0 first, then 3V0, then 1V8, then 3V3D (the DS181 order, 3V0 before the rest)."""
    return {"1V0": ramp(0.002, 0.003, 1.008), "3V0": ramp(0.004, 0.003, 3.0), "3V3A": ramp(0.008, 0.002, 3.3),
            "1V8": ramp(0.008, 0.002, 1.8), "3V3D": ramp(0.012, 0.002, 3.3)}


def test_pin_inside_the_limit_passes():
    avdd = ramp(0.004, 0.003, 3.0)
    pin = np.minimum(avdd + 0.25, 3.25)     # follows AVDD at +0.25 V
    r = PC.pin_check(T, pin, avdd)
    assert r["ok"] and r["over_max_v"] < 0.0


def test_pin_above_avdd_plus_0p3_fails():
    avdd = ramp(0.004, 0.003, 3.0)
    pin = avdd + 0.35                        # 50 mV over AVDD + 0.3 V
    r = PC.pin_check(T, pin, avdd)
    assert not r["ok"]
    assert r["over_max_v"] == pytest.approx(0.05, abs=1e-9)


def test_pin_driven_before_avdd_fails():
    """CLK at 3.3 V while AVDD is still 0: the power-up failure the directive is about."""
    avdd = ramp(0.010, 0.003, 3.0)
    clk = ramp(0.002, 0.001, 3.3)
    assert not PC.pin_check(T, clk, avdd)["ok"]


def test_pin_below_agnd_minus_0p3_fails():
    avdd = np.full_like(T, 3.0)
    assert not PC.pin_check(T, np.full_like(T, -0.31), avdd)["ok"]
    assert PC.pin_check(T, np.full_like(T, -0.29), avdd)["ok"]


def test_clk_steady_state_3v3_on_3v0_fails_by_its_margin():
    """3V3D 3.3 V on a pin against AVDD 3.0 V: 3.3 V is exactly AVDD + 0.3 V, so a 2 % high 3V3D fails."""
    avdd = np.full_like(T, 3.0)
    assert PC.pin_check(T, np.full_like(T, 3.3), avdd)["ok"]
    assert not PC.pin_check(T, np.full_like(T, 3.3 * 1.02), avdd)["ok"]


def test_good_start_order_passes():
    r = good_rails()
    starts = {k: PC.first_cross(T, r[k], 0.1 * NOMINAL[k]) for k in ("3V3A", "1V8", "3V3D")}
    assert PC.start_check(T, r["3V0"], starts)["ok"]
    assert PC.order_check(T, r, NOMINAL, ["1V0", "1V8", "3V3D"])["ok"]


def test_rail_starting_before_3v0_fails():
    r = good_rails()
    r["3V3A"] = ramp(0.001, 0.002, 3.3)       # 3V3A starts at 1 ms, 3V0 passes 1.2 V near 5.2 ms
    starts = {k: PC.first_cross(T, r[k], 0.1 * NOMINAL[k]) for k in ("3V3A", "1V8", "3V3D")}
    res = PC.start_check(T, r["3V0"], starts)
    assert not res["ok"]
    assert res["per_rail"] == {"3V3A": False, "1V8": True, "3V3D": True}


def test_rail_that_never_starts_does_not_fail_the_start_check():
    r = good_rails()
    assert PC.start_check(T, r["3V0"], {"3V3A": None, "1V8": None, "3V3D": None})["ok"]


def test_fpga_rail_out_of_order_fails():
    r = good_rails()
    r["1V8"] = ramp(0.001, 0.002, 1.8)        # VCCAUX before VCCINT (1V0 up at ~5 ms)
    res = PC.order_check(T, r, NOMINAL, ["1V0", "1V8", "3V3D"])
    assert not res["ok"] and res["out_of_order"] == [("1V0", "1V8")]
    r = good_rails()
    r["3V3D"] = ramp(0.004, 0.002, 3.3)       # VCCO before VCCAUX
    res = PC.order_check(T, r, NOMINAL, ["1V0", "1V8", "3V3D"])
    assert not res["ok"] and ("1V8", "3V3D") in res["out_of_order"]


def test_fpga_rail_missing_while_a_later_one_is_up_fails():
    r = good_rails()
    r["1V0"] = np.zeros_like(T)
    assert not PC.order_check(T, r, NOMINAL, ["1V0", "1V8", "3V3D"])["ok"]


def test_vcco_minus_vccaux_above_limit_too_long_fails():
    vcco = np.full_like(T, 3.3)
    vccaux = np.full_like(T, 0.5)             # difference 2.8 V, over 2.625 V
    # 40 ms is under 300 ms: passes the time, so stretch the axis to 0.5 s
    t = np.linspace(0.0, 0.5, 5001)
    vcco, vccaux = np.full_like(t, 3.3), np.full_like(t, 0.5)
    res = PC.vcco_vccaux_check(t, vcco, vccaux)
    assert not res["ok"] and res["max_v"] == pytest.approx(2.8)
    assert res["t_above_s"] > PC.T_VCCO2VCCAUX_S


def test_vcco_minus_vccaux_above_limit_briefly_passes():
    vcco = np.full_like(T, 3.3)
    vccaux = np.full_like(T, 0.5)             # 40 ms above the limit, under 300 ms
    assert PC.vcco_vccaux_check(T, vcco, vccaux)["ok"]


def test_vcco_minus_vccaux_within_limit_passes_for_any_time():
    t = np.linspace(0.0, 2.0, 2001)
    vcco, vccaux = np.full_like(t, 3.3), np.full_like(t, 1.0)     # 2.3 V
    assert PC.vcco_vccaux_check(t, vcco, vccaux)["ok"]


def test_good_ramp_keeps_vcco_minus_vccaux_inside():
    r = good_rails()
    res = PC.vcco_vccaux_check(T, r["3V3D"], r["1V8"])
    assert res["ok"] and res["max_v"] <= PC.VCCO_VCCAUX_MAX_V


def test_limits_match_the_sources():
    assert PC.VCCO_VCCAUX_MAX_V == SIM.VCCO_VCCAUX_MAX == SEQ.VCCO_VCCAUX_MAX == 2.625
    assert PC.ABS_OVER_V == SIM.ABS_OVER == 0.3
    assert PC.EN_VIH_V == SEQ.EN_VIH["LD39200"]


# ---- the order map on a fixture netlist -------------------------------------------------------
def fixture_netlist(en23, en25):
    """12 V bucks U17 (1V0) and U18 (3V8), U39 (3V0) from 3V8, LD39200 U24 (3V3A, EN on 3V8), U23 (1V8) and U25 (3V3D) from 3V8.
    en23 / en25 name the nets on the EN pin of U23 / U25; 'via R996' puts R996 10k to 3V0 in front of U23 EN."""
    comps = {"U17": "LMR51420", "U18": "LMR51420", "U39": "LP5907-3.0", "U23": "LD3920", "U25": "LD3920", "U24": "LD3920"}
    comps = {k: dict(value=v, fp="x", sheet="/") for k, v in comps.items()}
    for r in ("R32", "R33", "R100", "R101", "R996"):
        comps[r] = dict(value="10k", fp="SMD_0402", sheet="/")
    nets = {
        "/power/12V": [("U17", "3"), ("U17", "5"), ("U18", "3"), ("U18", "5")],
        "Net-FB17": [("U17", "4"), ("R32", "2"), ("R33", "1")],
        "/1V0": [("R32", "1")],
        "Net-FB18": [("U18", "4"), ("R100", "2"), ("R101", "1")],
        "/3V8": [("R100", "1"), ("U39", "1"), ("U39", "3"), ("U23", "7"), ("U23", "8"), ("U25", "7"), ("U25", "8"),
                  ("U24", "7"), ("U24", "8"), ("U24", "6")],
        "/fpga/adc/3V0": [("U39", "5")],
        "/1V8": [("U23", "1")],
        "/3V3D": [("U25", "1")],
        "/3V3A": [("U24", "1")],
        "Net-PG23": [("U23", "5")],
        "Net-PG25": [("U25", "5")],
        "GND": [("R33", "2"), ("R101", "2")],
    }

    def tie(unit, where):
        if where == "12V":
            nets["/power/12V"].append((unit, "6"))
        elif where == "PG23":
            nets["Net-PG23"].append((unit, "6"))
        elif where == "via R996":
            nets["Net-(%s-EN)" % unit] = [(unit, "6"), ("R996", "2")]
            nets["/fpga/adc/3V0"].append(("R996", "1"))
        else:
            raise ValueError(where)

    tie("U23", en23)
    tie("U25", en25)
    return comps, nets


def classes(en23, en25):
    comps, nets = fixture_netlist(en23, en25)
    regs = SEQ.regulators(comps, nets)
    return {o[0]: SEQ.classify(o, regs, comps, nets)[0] for o in SEQ.ORDERS}, regs


def test_fixture_regulators_are_found():
    _, regs = classes("12V", "12V")
    assert regs["U17"]["out"] == "/1V0" and regs["U18"]["out"] == "/3V8"
    assert regs["U39"]["out"] == "/fpga/adc/3V0" and regs["U23"]["pg"] == "Net-PG23"


def test_en_on_12v_is_timing():
    c, _ = classes("12V", "12V")
    assert c["on-3V0-1V8"] == "timing"           # U23 EN on 12 V: nothing ties it to U39
    assert c["on-VCCINT-VCCAUX"] == "timing"
    assert c["on-VCCAUX-VCCO"] == "timing"       # U25 EN on 12 V as well


def test_en_on_a_pg_is_design():
    c, _ = classes("12V", "PG23")
    assert c["on-VCCAUX-VCCO"] == "design"       # U25 EN on the U23 PG
    assert c["on-VCCINT-VCCAUX"] == "timing"     # U23 EN still on 12 V


def test_en_on_3v0_through_a_resistor_is_design_and_the_pg_chain_follows():
    c, regs = classes("via R996", "PG23")
    assert c["on-3V0-1V8"] == "design"           # series R996 followed to U39
    assert c["on-3V0-3V3D"] == "design"          # U25 <- U23 PG <- U39
    assert c["on-VCCAUX-VCCO"] == "design"
    assert c["on-VCCINT-VCCAUX"] == "timing"     # 1V0 (U17) is not in the chain
    assert SEQ.en_source(regs["U23"], regs, *fixture_netlist("via R996", "PG23"))[:2] == ("rail", "U39")
    assert SEQ.en_source(regs["U25"], regs, *fixture_netlist("via R996", "PG23"))[:2] == ("pg", "U23")


def test_power_off_orders_are_timing_without_a_feed():
    c, _ = classes("via R996", "PG23")
    for oid in ("off-3V3D-3V0", "off-VCCO-VCCAUX", "off-VCCAUX-VCCINT"):
        assert c[oid] == "timing"


def test_order_map_file_marks_every_timing_row_with_a_fix():
    import csv
    rows = list(csv.DictReader(open(HERE / "sequence.csv")))
    assert rows
    for r in rows:
        assert r["class_rx1"] in ("design", "timing")
        if r["class_rx1"] == "timing":
            assert r["fixes"], r["id"]


# ---- the LD39200 ramp fit against the figure points -------------------------------------------
def test_fig23_points_are_a_rising_ramp_to_3v3():
    t, v = SIM.read_fig23()
    assert len(t) >= 20
    assert np.all(np.diff(t) > 0)
    assert np.all(np.diff(v) >= -0.02)           # read-off noise only
    assert v[0] < 0.1 and 3.1 < v[-1] < 3.4      # 3.3 V output (Figure 23: 3.7 V in, 3.3 V out)


def test_ld39200_ramp_fit_matches_the_plot_points():
    t, v = SIM.read_fig23()
    f = SIM.fit_ld39200(t, v)
    assert f["rms_v"] < 0.15 and f["max_err_v"] < 0.3
    model = SIM.ramp_model(t, f["td_us"], f["tau_us"])
    assert np.sqrt(np.mean((model - v) ** 2)) == pytest.approx(f["rms_v"], abs=1e-9)
    assert f["t90_us"] == pytest.approx(f["td_us"] + f["tau_us"] * np.log(10))
    # the EN-to-90 % time against the 0.1 to 0.3 ms band sequence.py and the simulation use
    assert 100.0 <= f["t90_us"] <= 300.0
    # the 90 % point of the plot itself (first point at or above 0.9 x 3.3 V) is close to the model's
    t90_plot = t[np.nonzero(v >= 0.9 * 3.3)[0][0]]
    assert abs(t90_plot - f["t90_us"]) < 40.0


def test_ld39200_fit_recovers_a_known_ramp():
    t = np.arange(0.0, 800.0, 10.0)
    v = SIM.ramp_model(t, 30.0, 60.0)
    f = SIM.fit_ld39200(t, v)
    assert f["td_us"] == pytest.approx(30.0, abs=1.0) and f["tau_us"] == pytest.approx(60.0, abs=1.0)
    assert f["rms_v"] < 0.01


def test_ld39200_fit_default_reads_the_csv():
    assert SIM.fit_ld39200()["rms_v"] < 0.15
