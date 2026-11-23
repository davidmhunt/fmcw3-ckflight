"""par-11 step 5: the rail load budget (analysis/12_rail_loads/loads.py).

The per-rail sums equal the consumer table; the ripple matches the ti-lmr51420 equation 10 on a
hand-worked case; the pass marks use the stated Isat and Irms of the APS0650M330A.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "analysis" / "12_rail_loads"
sys.path.insert(0, str(HERE))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


currents = _load("currents")
L = _load("loads")


@pytest.fixture(scope="module")
def result():
    return L.build()


@pytest.fixture(scope="module")
def consumers():
    return json.load(open(currents.CONSUMERS))


@pytest.fixture(scope="module")
def step3():
    return json.load(open(L.VCCINT))["estimate"]


@pytest.mark.parametrize("board", ["2rx", "1rx"])
@pytest.mark.parametrize("rail", ["1V0", "3V8", "5V6"])
def test_rail_sum_equals_consumer_table(result, consumers, step3, board, rail):
    rows, problems = currents.table(board, consumers)
    assert not problems
    for which, key in (("typ", "dc_typ_a"), ("max", "dc_max_a")):
        ma = sum(r[which] or 0 for r in rows if r["rail"] == rail)
        if rail == "1V0":
            ma += step3[f"{which}_mA"]
        assert result["boards"][board][rail][key] == pytest.approx(ma / 1000.0, abs=1e-9)


def test_1v0_includes_the_fpga_core_and_other_rails_do_not(result, consumers, step3):
    rows, _ = currents.table("2rx", consumers)
    other = sum(r["max"] or 0 for r in rows if r["rail"] == "1V0") / 1000.0
    assert result["boards"]["2rx"]["1V0"]["dc_max_a"] == pytest.approx(other + step3["max_mA"] / 1000.0)
    assert step3["max_mA"] > 0


def test_ripple_hand_worked_5v6_500khz():
    # Vout = 0.6 * (1 + 100/12) = 5.6 V; L = 33 uH - 20 % = 26.4 uH; fsw 500 kHz; VIN 12 V
    # dIL = 5.6 * (12 - 5.6) / (12 * 26.4e-6 * 500e3) = 35.84 / 158.4 = 0.226263 A
    assert L.vout("5V6") == pytest.approx(5.6)
    assert L.ripple(5.6, 26.4, 500e3) == pytest.approx(35.84 / 158.4, rel=1e-9)
    assert L.ripple(5.6, 26.4, 500e3) == pytest.approx(0.226263, abs=1e-6)
    d = L.build()
    assert d["boards"]["2rx"]["5V6"]["ripple_pp_a"]["500 kHz"] == pytest.approx(0.226263, abs=1e-6)
    assert d["l_low_uh"] == pytest.approx(26.4)


def test_peak_is_dc_plus_half_ripple(result):
    for rails in result["boards"].values():
        for r in rails.values():
            for f in ("500 kHz", "1.1 MHz"):
                assert r["peak_max_a"][f] == pytest.approx(r["dc_max_a"] + r["ripple_pp_a"][f] / 2)
                assert r["peak_typ_a"][f] == pytest.approx(r["dc_typ_a"] + r["ripple_pp_a"][f] / 2)
            assert r["peak_worst_a"] == max(r["peak_max_a"].values())


def test_pass_marks_use_stated_isat_and_irms(result):
    ind = L.INDUCTOR
    assert (ind["isat_a"], ind["irms_a"], ind["dcr_ohm"], ind["L_uH"]) == (3.53, 2.32, 0.178, 33.0)
    assert L.PEAK_LIMIT_A == pytest.approx(0.6 * 3.53)
    assert L.DC_LIMIT_A == pytest.approx(2.0 / 3.0 * 2.32)
    assert L.DC_LIMIT_A < L.LMR_RATING_A == 2.0
    lim = result["limits"]
    assert lim["peak_a"] == pytest.approx(2.118) and lim["dc_a"] == pytest.approx(1.54667, abs=1e-5)
    for rails in result["boards"].values():
        for r in rails.values():
            assert r["peak_ok"] == (r["peak_worst_a"] <= lim["peak_a"])
            assert r["dc_ok"] == (r["dc_max_a"] <= lim["dc_a"])
            assert r["copper_loss_typ_w"] == pytest.approx(r["dc_typ_a"] ** 2 * 0.178)
    assert result["aps0650_ok"] == int(all(
        r["peak_ok"] and r["dc_ok"] for b in result["boards"].values() for r in b.values()))
    assert result["peak_max_a"] == max(r["peak_worst_a"] for b in result["boards"].values() for r in b.values())
    assert result["dc_max_a"] == max(r["dc_max_a"] for b in result["boards"].values() for r in b.values())


def test_fault_case_against_isat(result):
    f = result["fault"]
    assert f["ihs_pk_oc_a"] == dict(min=2.7, typ=3.5, max=5.1)
    assert f["isat_a"] == 3.53
    assert f["saturates_at"] == dict(min=False, typ=False, max=True)
