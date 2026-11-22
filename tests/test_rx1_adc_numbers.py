"""rx1-02 step 3: the hand numbers for the 1-RX ADC input (analysis/11_board_1rx/adc_numbers.py).

The arithmetic is checked against independent hand values; the datasheet constants carry their
manifest id and page, which this test also requires.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "adc_numbers", ROOT / "analysis/11_board_1rx/adc_numbers.py")
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


def test_every_constant_cites_a_page():
    for table in (N.AD9237, N.LTC2292, N.LP5907):
        for key, (val, src) in table.items():
            assert isinstance(val, (int, float)), key
            assert "p." in src, f"{key}: no page in {src!r}"


def test_rail_3v0_against_the_regulator():
    r = N.rail_3v0()
    assert r["ltc2292_ma"] == pytest.approx(235 / 3)            # 78.3 mA, both channels
    assert r["bias_divider_ma"] == pytest.approx(1.5)            # 3 V over 2 k
    assert r["rx1_typ_total_ma"] == pytest.approx(45.5 + 1.5 + 3 / 14.7)
    assert r["rx1_bound_total_ma"] < r["today_total_ma"] < r["u39_rating_ma"]


def test_snr_to_noise_density():
    a = N.adc_noise()
    assert a["ideal_12bit_db"] == pytest.approx(74.0, abs=0.01)
    # 2 V p-p differential: full-scale sine 0.7071 V rms; 67.0 dBFS -> 316 uV rms in 20 MHz
    assert a["ad9237"]["snr_dbfs"] == pytest.approx(67.0)
    assert a["ad9237"]["noise_rms_uv"] == pytest.approx(0.7071068e6 * 10 ** (-67 / 20), rel=1e-6)
    assert a["ad9237"]["density_nv_rthz"] == pytest.approx(315.853 / math.sqrt(20e6) * 1e3, rel=1e-4)
    assert a["decim_gain_db"] == pytest.approx(13.01, abs=0.01)
    assert a["delta_db"] == pytest.approx(3.6)


def test_dynamic_range_combines_front_end_and_adc():
    # with no front-end noise the full-band dynamic range is the ADC's own SNR (dBFS)
    d = N.dynamic_range(0.0, 0.0)
    assert d["ad9237"]["dr_nyq_db"] == pytest.approx(67.0)
    assert d["ltc2292"]["dr_nyq_db"] == pytest.approx(70.6)
    # ... and in 1 MHz of 20 MHz it gains 10 log10(20) = 13.01 dB
    assert d["ad9237"]["dr_band_db"] == pytest.approx(67.0 + 13.0103, abs=1e-3)
    # front-end noise equal to the ADC noise costs 3.01 dB
    n = N.adc_noise()["ad9237"]["noise_rms_uv"]
    assert N.dynamic_range(n, 0.0)["ad9237"]["dr_nyq_db"] == pytest.approx(67.0 - 3.0103, abs=1e-3)


def test_input_limits():
    lim = N.input_limits()
    assert (lim["vcm_min_v"], lim["vcm_max_v"]) == (0.5, 2.0)     # VREF/2, (AVDD+VREF)/2
    assert lim["half_period_ns"] == pytest.approx(12.5)
    assert lim["half_lsb_uv"] == pytest.approx(2e6 / 4096 / 2)


def test_sim_results_on_file_pass_their_checks():
    """The committed LTspice results (adc_input_sim.py) passed their hand-calculation checks."""
    data = json.loads((ROOT / "analysis/11_board_1rx/sim/adc_input.json").read_text())
    assert data["checks"] and all(c["ok"] for c in data["checks"]), data["checks"]
    assert set(data["cases"]) == {"today", "rx1"}
