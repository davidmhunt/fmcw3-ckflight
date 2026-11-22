"""rx1-02 step 6: the data-path numbers (analysis/11_board_1rx/data_path.py).

Checks the arithmetic against hand values and that the answer the report gives holds: raw
40 MSPS x 12 bit does not fit the FT2232H synchronous FIFO, the decimated stream does, and a
decimated chirp fits the firmware's ADC FIFO.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "data_path", ROOT / "analysis/11_board_1rx/data_path.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)


def test_every_constant_cites_a_page_or_file():
    for table in (D.FT2232H, D.FPGA):
        for key, (val, src) in table.items():
            assert isinstance(val, (int, float)), key
            assert "p." in src, f"{key}: no page in {src!r}"
    for key, (val, src) in D.FIRMWARE.items():
        assert any(w in src for w in (".vhd", ".xci")), f"{key}: no firmware file in {src!r}"


def test_rates_against_hand_values():
    r = D.rates()["rates_mbyte_s"]
    assert r["raw_12bit_packed"] == pytest.approx(60.0)          # 40e6 x 12 / 8
    assert r["raw_16bit_padded"] == pytest.approx(80.0)
    assert r["decimated_16bit_one_channel"] == pytest.approx(4.0)  # 2e6 x 2
    assert r["decimated_firmware_word_32bit"] == pytest.approx(8.0)
    assert D.rates()["raw_mbit_s"] == pytest.approx(480.0)       # the whole USB 2.0 HS line rate


def test_raw_does_not_stream_decimated_does():
    r = D.rates()
    lim = r["limits_mbyte_s"]
    assert lim["bus_ceiling"] == pytest.approx(60.0)             # 60 MHz x 8 bit
    assert not r["verdict"]["raw_12bit_packed"]["fits_max_40"]
    assert not r["verdict"]["raw_12bit_packed"]["fits_stated_25"]
    assert r["verdict"]["decimated_firmware_word_32bit"]["fits_stated_25"]
    assert r["verdict"]["decimated_16bit_one_channel"]["pct_of_stated_25"] == pytest.approx(16.0)
    m = r["max_streaming_fs_msps"]
    assert m["at_stated_25"] == pytest.approx(12.5) and m["at_max_40"] == pytest.approx(20.0)
    assert (m["min_integer_decimation_stated_25"], m["min_integer_decimation_max_40"]) == (4, 2)


def test_buffers():
    b = D.buffers()
    assert b["chirp_samples_raw"] == pytest.approx(40000)
    assert b["chirp_samples_decimated"] == pytest.approx(2000)
    assert b["firmware_fifos_kb"] == pytest.approx((2048 * 32 + 16384 * 8 + 1024 * 8) / 1024)
    assert b["bram_total_kb"] == 4860 and b["bram_total_kbyte"] == pytest.approx(607.5)
    assert b["decimated_chirp_fits_adc_fifo"]                    # 2001 words in 2048
    assert b["chirp_raw_16bit_pct_of_bram"] < 15                 # a raw chirp fits the XC7A100T
    assert b["raw_chirp_drain_ms_stated_25"] == pytest.approx(3.2)
    assert b["raw_duty_stated_25"] == pytest.approx(1 / 3.2)


def test_firmware_state_machines():
    f = D.firmware_ceiling()
    assert f["ctrl_clk_per_word"] == 18
    assert f["ctrl_ceiling_mbyte_s"] == pytest.approx(40e6 / 18 * 4 / 1e6)
    assert f["usb_fsm_ceiling_mbyte_s"] == pytest.approx(12.0)
    assert f["need_mbyte_s"] == pytest.approx(8.0)


def test_results_on_file_match_the_code():
    data = json.loads((ROOT / "analysis/11_board_1rx/sim/data_path.json").read_text())
    assert data == json.loads(json.dumps(D.summary()))
