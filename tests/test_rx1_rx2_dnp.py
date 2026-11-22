"""rx1-02 step 4: the RX2-only part list, from the kicad/ netlist."""
import importlib.util
import pathlib
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not found")


@pytest.fixture(scope="module")
def res():
    spec = importlib.util.spec_from_file_location(
        "rx2_dnp", ROOT / "analysis" / "11_board_1rx" / "rx2_dnp.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.analyse()


def test_chains_end_on_the_expected_adc_channel(res):
    assert res["chain_end_nets"]["RX1"] == ["Net-(U8-AINA+)", "Net-(U8-AINA-)"]
    assert res["chain_end_nets"]["RX2"] == ["Net-(U8-AINB+)", "Net-(U8-AINB-)"]


def test_shared_parts_are_not_in_the_removal_list(res):
    assert res["shared"] == ["U29", "U45", "U8"]
    for ref in res["shared"] + res["lo_split_parts"]:
        assert ref not in res["only_rx2"]
    assert {"U26", "U3"} <= set(res["lo_split_parts"])


def test_rx2_only_list(res):
    only = set(res["only_rx2"])
    assert {"P2", "U16", "U13", "U28"} <= only
    assert len(only) == 48
    # The mirrored RX1 list has the same size less its own test pads and 1:1 pairs.
    assert len(res["only_rx1"]) == len(only)


def test_fpga_pins_freed(res):
    assert res["fpga_pins_freed"] == {"ADC_OE2": ["P1"], "ADC_SHDN2": ["N2"], "OFB": ["M1"]}
    assert res["u30_on_rx2_parts"] == []
