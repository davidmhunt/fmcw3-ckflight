"""Data path for real-time SAR on the 1-RX board (rx1-02 step 6).

Compares the 1-RX ADC data rate (raw 40 MSPS x 12 bit, and after the firmware's decimation by 20)
with the FT2232H synchronous FIFO rate and the FPGA's buffer resources. Plain arithmetic, no
simulator. Every datasheet constant names its manifest id and PDF page (in these files the PDF
page equals the printed folio). Firmware facts are read from davidmhunt/fmcw3-ckflight-fw at
commit cb7f097eaf21b407d9dcd2f65e28b1143f1d12d5 (read only): file and line are given.

usage: python3 analysis/11_board_1rx/data_path.py   (prints the table, writes sim/data_path.json)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FW_COMMIT = "cb7f097eaf21b407d9dcd2f65e28b1143f1d12d5"

# --- FT2232H (U33), ftdi-ft2232h-datasheet, Version 2.6 -------------------------------------
FT2232H = {
    "sync_fifo_max_mbyte_s": (40.0, "ftdi-ft2232h-datasheet p.1, 'single channel synchronous FIFO "
                                    "mode for transfers upto 40 Mbytes/Sec'"),
    "sync_fifo_stated_mbyte_s": (25.0, "ftdi-ft2232h-datasheet p.26, 'greater than 25 "
                                       "Mbytes/second over a synchronous parallel FIFO interface'"),
    "clkout_mhz": (60.0, "ftdi-ft2232h-datasheet p.32, 'The chip drives a 60 MHz CLKOUT clock'; "
                         "p.31 Table 4.1 t1 = 16.67 ns"),
    "bus_width_bits": (8, "ftdi-ft2232h-datasheet p.12 Table 3.6, D7..D0 data bus (channel A)"),
    "usb_line_mbit_s": (480.0, "ftdi-ft2232h-datasheet p.1 and p.26, USB 2.0 High Speed 480 Mbits/s"),
    "buffer_kbyte": (4.0, "ftdi-ft2232h-datasheet p.26, 4 kbytes Tx and Rx buffers per interface"),
}

# --- XC7A100T (U30), amd-ds180-7series-overview Table 4 (PDF p.3) ------------------------------
FPGA = {
    "bram36_blocks": (135, "amd-ds180-7series-overview p.3 Table 4, XC7A100T 36 Kb blocks"),
    "bram_max_kb": (4860, "amd-ds180-7series-overview p.3 Table 4, XC7A100T block RAM max (Kb)"),
    "bram_max_kb_xc7a35t": (1800, "amd-ds180-7series-overview p.3 Table 4, XC7A35T (as-ordered "
                                  "build), block RAM max (Kb)"),
}

# --- target set (analysis/targets/default.yaml; status assumed except bandwidth) ---------------
TARGETS = {
    "adc_fs_hz": 40e6,        # AD9237BCPZ-40 and the 40 MHz clock (adi-ad9237-datasheet p.3)
    "adc_bits": 12,
    "chirp_duration_s": 1e-3,  # performance.chirp_duration_s
    "sample_rate_after_decim_hz": 2e6,  # design.sample_rate_hz
    "decimation": 20,          # fir_compiler_0.xci Decimation_Rate 20, 21 taps
}

# --- firmware facts at FW_COMMIT (file: what it says) ----------------------------------------
FIRMWARE = {
    "decimation": (20, "fir_compiler_0.xci Decimation_Rate 20, Sample_Frequency 40.0; adc.vhd "
                       "lines 123-138: with the FIR off a valid pulse still comes every 20 clocks, "
                       "so the firmware has no 40 MSPS output path at all"),
    "word_bytes": (4, "control.vhd line 295: the FIFO word is adc_data_a & adc_data_b, 16 bit each "
                      "(adc.vhd lines 99-100 sign-extend the 12 bit sample to 16)"),
    "adc_fifo_words": (2048, "fifo_generator_2.xci Input_Depth 2048, width 32, common clock "
                             "block RAM; written only during the ramp (control.vhd lines 273-306)"),
    "tx_fifo_bytes": (16384, "fifo_generator_1.xci Input_Depth 16384, width 8, independent clocks, "
                             "block RAM (usb_sync.vhd lines 195-209)"),
    "rx_fifo_bytes": (1024, "fifo_generator_0.xci Input_Depth 1024, width 8, block RAM "
                            "(usb_sync.vhd lines 179-190)"),
    # byte-serial state machines, counted from the code (estimate, not simulated)
    "ctrl_clk_per_byte": (4, "control.vhd lines 428-468: TX_PREP_BYTE, TX_WRITE_BYTE and "
                             "TX_WAIT_USB_ACK (two clocks: wr_en, then wr_ack) per byte"),
    "ctrl_clk_per_word_extra": (2, "control.vhd lines 410-426: TX_READ_ADC_FIFO and "
                                   "TX_WAIT_FIFO_DATA per 32 bit word"),
    "usb_clk_per_byte": (5, "usb_sync.vhd lines 306-353: TX_IDLE, TX_READ_FIFO, TX_ONE_CLOCK, "
                            "TX_ASSERT_WRITE, TX_DEASSERT_WRITE per byte (one write per five clocks)"),
}


def v(d, k):
    return d[k][0]


KB = 1024  # bits per Kb in the AMD tables


def rates():
    fs, bits = TARGETS["adc_fs_hz"], TARGETS["adc_bits"]
    dec, fs_out = TARGETS["decimation"], TARGETS["adc_fs_hz"] / TARGETS["decimation"]
    word_bytes = v(FIRMWARE, "word_bytes")
    items = {
        "raw_12bit_packed": fs * bits / 8,
        "raw_16bit_padded": fs * 2,
        "decimated_16bit_one_channel": fs_out * 2,
        "decimated_firmware_word_32bit": fs_out * word_bytes,
    }
    limits = {
        "bus_ceiling": v(FT2232H, "clkout_mhz") * 1e6 * v(FT2232H, "bus_width_bits") / 8,
        "datasheet_max": v(FT2232H, "sync_fifo_max_mbyte_s") * 1e6,
        "datasheet_stated": v(FT2232H, "sync_fifo_stated_mbyte_s") * 1e6,
    }
    out = {"rates_mbyte_s": {k: x / 1e6 for k, x in items.items()},
           "limits_mbyte_s": {k: x / 1e6 for k, x in limits.items()},
           "raw_mbit_s": fs * bits / 1e6, "usb_line_mbit_s": v(FT2232H, "usb_line_mbit_s"),
           "decimated_sample_rate_hz": fs_out, "verdict": {}}
    for k, x in items.items():
        out["verdict"][k] = {
            "pct_of_stated_25": 100 * x / limits["datasheet_stated"],
            "pct_of_max_40": 100 * x / limits["datasheet_max"],
            "pct_of_bus_60": 100 * x / limits["bus_ceiling"],
            "fits_stated_25": x <= limits["datasheet_stated"],
            "fits_max_40": x <= limits["datasheet_max"],
        }
    # what could stream with no hardware change, 16 bit per sample, one channel
    out["max_streaming_fs_msps"] = {
        "at_stated_25": limits["datasheet_stated"] / 2 / 1e6,
        "at_max_40": limits["datasheet_max"] / 2 / 1e6,
        "min_integer_decimation_stated_25": math.ceil(fs / (limits["datasheet_stated"] / 2)),
        "min_integer_decimation_max_40": math.ceil(fs / (limits["datasheet_max"] / 2)),
    }
    return out


def firmware_ceiling():
    """Throughput ceiling of the firmware's own byte-serial FSMs (counted from the code)."""
    wb = v(FIRMWARE, "word_bytes")
    clk_word = wb * v(FIRMWARE, "ctrl_clk_per_byte") + v(FIRMWARE, "ctrl_clk_per_word_extra")
    ctrl = 40e6 / clk_word * wb
    usb = 60e6 / v(FIRMWARE, "usb_clk_per_byte")
    need = TARGETS["adc_fs_hz"] / TARGETS["decimation"] * wb
    return {"ctrl_clk_per_word": clk_word, "ctrl_ceiling_mbyte_s": ctrl / 1e6,
            "usb_fsm_ceiling_mbyte_s": usb / 1e6, "need_mbyte_s": need / 1e6,
            "ctrl_margin_pct": 100 * (ctrl / need - 1),
            "need_16bit_one_channel_mbyte_s": need / 2 / 1e6}


def buffers():
    fs, bits = TARGETS["adc_fs_hz"], TARGETS["adc_bits"]
    t = TARGETS["chirp_duration_s"]
    total_kb = v(FPGA, "bram_max_kb")
    fifo_kb = (v(FIRMWARE, "adc_fifo_words") * 32 + v(FIRMWARE, "tx_fifo_bytes") * 8
               + v(FIRMWARE, "rx_fifo_bytes") * 8) / KB
    n_raw = fs * t
    n_dec = fs / TARGETS["decimation"] * t
    raw16_kb = n_raw * 16 / KB
    raw12_kb = n_raw * bits / KB
    dec_words = n_dec + 1        # plus the 0xC8C8C8C8 header word (control.vhd line 265)
    out = {
        "bram_total_kb": total_kb, "bram_total_kbyte": total_kb / 8,
        "bram_total_kb_xc7a35t": v(FPGA, "bram_max_kb_xc7a35t"),
        "firmware_fifos_kb": fifo_kb, "firmware_fifos_pct": 100 * fifo_kb / total_kb,
        "chirp_samples_raw": n_raw, "chirp_samples_decimated": n_dec,
        "chirp_raw_16bit_kb": raw16_kb, "chirp_raw_12bit_kb": raw12_kb,
        "chirp_raw_16bit_pct_of_bram": 100 * raw16_kb / total_kb,
        "chirp_raw_12bit_pct_of_bram": 100 * raw12_kb / total_kb,
        "chirp_raw_16bit_pct_of_bram_xc7a35t": 100 * raw16_kb / v(FPGA, "bram_max_kb_xc7a35t"),
        "adc_fifo_words": v(FIRMWARE, "adc_fifo_words"),
        "chirp_decimated_words_with_header": dec_words,
        "decimated_chirp_fits_adc_fifo": dec_words <= v(FIRMWARE, "adc_fifo_words"),
        "adc_fifo_ms_at_2msps": v(FIRMWARE, "adc_fifo_words") / (fs / TARGETS["decimation"]) * 1e3,
    }
    # store and forward of one raw chirp (a firmware change only): drain time through the FT2232H
    raw_bytes = n_raw * 2
    for name, rate in (("stated_25", 25e6), ("max_40", 40e6)):
        drain = raw_bytes / rate
        out[f"raw_chirp_drain_ms_{name}"] = drain * 1e3
        out[f"raw_max_chirps_per_s_{name}"] = 1 / drain
        out[f"raw_duty_{name}"] = t / drain
    return out


def summary():
    return {"firmware_commit": FW_COMMIT, "targets": TARGETS, "rates": rates(),
            "firmware_ceiling": firmware_ceiling(), "buffers": buffers()}


def main():
    s = summary()
    r, f, b = s["rates"], s["firmware_ceiling"], s["buffers"]
    print("FT2232H limits (MB/s):", r["limits_mbyte_s"])
    for k, x in r["rates_mbyte_s"].items():
        print(f"  {k:32s} {x:6.1f} MB/s   {r['verdict'][k]['pct_of_stated_25']:5.0f} % of 25   "
              f"{r['verdict'][k]['pct_of_max_40']:5.0f} % of 40   fits 25: "
              f"{r['verdict'][k]['fits_stated_25']}")
    print("max streaming fs at 16 bit:", r["max_streaming_fs_msps"])
    print("firmware FSM ceiling:", {k: round(x, 2) for k, x in f.items()})
    print("buffers:", {k: (round(x, 2) if isinstance(x, float) else x) for k, x in b.items()})
    (HERE / "sim").mkdir(exist_ok=True)
    (HERE / "sim" / "data_path.json").write_text(json.dumps(s, indent=1) + "\n")


if __name__ == "__main__":
    main()
