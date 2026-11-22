"""Datasheet numbers and hand calculations for the 1-RX ADC input (rx1-02 step 3).

Plain Python, no simulator: the 3V0 rail load, SNR and noise of the AD9237 against the
LTC2292, and the input limits the LTspice run (adc_input_sim.py) is judged against.
Every constant names its manifest id (datasheets/manifest.yaml) and PDF page.

Page numbers are PDF pages; in these three files the PDF page equals the printed folio.

usage: python3 analysis/11_board_1rx/adc_numbers.py   (prints the tables)
"""
from __future__ import annotations

import json
import math

# --- AD9237BCPZ-40 (U8 on the 1-RX board), adi-ad9237-datasheet, Rev. C --------------------
AD9237 = {
    "span_vpp": (2.0, "adi-ad9237-datasheet p.3 Table 1 (VREF 1.0 V, MODE2 0 V: 2 V p-p)"),
    "cin_pf": (7.0, "p.3 Table 1, input capacitance, one pin to AGND (note 3: see Figure 4)"),
    "csample_pf": (5.0, "p.16 Figure 35, switched-capacitor SHA input, 5 pF per side"),
    "avdd_v": (3.0, "p.3 Table 1, AVDD typ"),
    "vref_v": (1.0, "p.18 Table 7, SENSE = AGND gives 1.0 V (step 2 strap)"),
    "iavdd_ma": (45.5, "p.3 Table 1, IAVDD typ, -40 grade at maximum clock rate"),
    "idrvdd_ma": (4.5, "p.3 Table 1, IDRVDD typ (DRVDD 2.5 V; on 3V3D, not 3V0)"),
    "p_sine_max_mw": (180.0, "p.3 Table 1, power, sine wave input, -40 grade max"),
    "snr_dbc": (66.5, "p.4 Table 3, SNR typ, fIN 2.4 MHz, -40 grade, AIN -0.5 dBFS"),
    "snr_min_dbc": (65.3, "p.4 Table 3, SNR min, fIN 19.6 MHz, -40 grade"),
    "ain_dbfs": (-0.5, "p.4 Table 3 conditions, AIN = -0.5 dBFS"),
    "noise_lsb_rms": (0.70, "p.3 Table 1, input referred noise, VREF 1.0 V"),
    "vin_absmax_over_avdd_v": (0.3, "p.7 Table 5, VIN+/VIN- to AGND -0.3 V to AVDD + 0.3 V"),
    "fs_hz": (40e6, "AD9237BCPZ-40, maximum sample rate (p.3 column -40)"),
}
# VCM limits, p.17: VCMMIN = VREF/2, VCMMAX = (AVDD + VREF)/2; settle within half a clock (p.16).

# --- LTC2292 (U8 today) --------------------------------------------------------------------
# The file on hand is the LTC2294 sheet (adi-ltc2292-datasheet, 2294fa); its related-parts
# table (p.24) is the only LTC2292 line in it. The LTC2292 sheet itself is still to obtain.
LTC2292 = {
    "span_vpp": (2.0, "adi-ltc2292-datasheet p.3, analog input range +/-1 V (SENSE = VDD)"),
    "rin_ohm": (15.0, "p.12 Figure 2, 15 ohm series per input"),
    "cpar_pf": (1.0, "p.12 Figure 2, CPARASITIC 1 pF"),
    "csample_pf": (4.0, "p.12 Figure 2, CSAMPLE 4 pF"),
    "vcm_v": (1.500, "p.4, VCM output voltage 1.475/1.500/1.525 V"),
    "vcm_rout_ohm": (4.0, "p.4, VCM output resistance"),
    "p_both_mw": (235.0, "p.24 related parts, LTC2292 dual 40 Msps 235 mW (both channels)"),
    "snr_db_table": (74.4, "p.24 related parts, LTC2292 '74.4 dB SNR': above the 74.0 dB ideal of a "
                           "12-bit converter, so a table error (the 14-bit LTC2297 row has the same)"),
    "snr_db_ltc2294": (70.6, "p.3, LTC2294 (same family, 80 Msps) SNR typ 5 MHz, AIN -1 dBFS"),
    "noise_lsb_rms": (0.3, "p.2, transition noise, SENSE = 1 V (LTC2294)"),
    "vdd_v": (3.0, "p.5, VDD typ"),
}

# --- U39 LP5907-3.0, the 3V0 regulator (ti-lp5907-datasheet) ----------------------------------
LP5907 = {"iout_max_ma": (250.0, "ti-lp5907-datasheet p.5, maximum output current 250 mA "
                                 "(p.4 recommended IOUT 0 to 250 mA)")}

# Other 3V0 loads (netlist /fpga/adc/3V0: U8, R91/R92 MODE divider, the new step 2 divider).
R91, R92 = 4.7e3, 10e3            # MODE strap, kept
RB1 = RB2 = 1.0e3                 # step 2: 1.5 V bias divider, 3V0 to GND


def v(d, k):
    return d[k][0]


def lsb_v(span_vpp: float, bits: int = 12) -> float:
    return span_vpp / 2 ** bits


def ideal_snr_db(bits: int = 12) -> float:
    return 6.02 * bits + 1.76


def snr_dbfs(snr_dbc: float, ain_dbfs: float) -> float:
    """Datasheet SNR at a signal below full scale, referred to full scale."""
    return snr_dbc - ain_dbfs


def noise_from_snr(span_vpp: float, snr_dbfs_: float, fs_hz: float):
    """Full-scale sine rms, noise rms over fs/2 and its density (white noise assumed)."""
    vfs_rms = span_vpp / 2 / math.sqrt(2)
    vn = vfs_rms * 10 ** (-snr_dbfs_ / 20)
    return vfs_rms, vn, vn / math.sqrt(fs_hz / 2)


def rail_3v0():
    """3V0 load in mA: today (LTC2292 both channels) and 1-RX (AD9237), against U39's rating."""
    i_mode = 3.0 / (R91 + R92) * 1e3
    i_div = 3.0 / (RB1 + RB2) * 1e3
    ltc = v(LTC2292, "p_both_mw") / v(LTC2292, "vdd_v")
    ad_typ = v(AD9237, "iavdd_ma")
    ad_max = v(AD9237, "p_sine_max_mw") / v(AD9237, "avdd_v")   # bound: all of P_max on AVDD
    rating = v(LP5907, "iout_max_ma")
    today = ltc + i_mode
    rx1_typ = ad_typ + i_mode + i_div
    rx1_max = ad_max + i_mode + i_div
    return {
        "ltc2292_ma": ltc, "ad9237_typ_ma": ad_typ, "ad9237_bound_ma": ad_max,
        "mode_divider_ma": i_mode, "bias_divider_ma": i_div,
        "today_total_ma": today, "rx1_typ_total_ma": rx1_typ, "rx1_bound_total_ma": rx1_max,
        "u39_rating_ma": rating,
        "today_pct": 100 * today / rating, "rx1_typ_pct": 100 * rx1_typ / rating,
        "rx1_bound_pct": 100 * rx1_max / rating,
    }


def adc_noise(decim: int = 20):
    """SNR, noise and dynamic range of both ADCs at 40 MSPS, before and after decimation."""
    fs = v(AD9237, "fs_hz")
    ad_dbfs = snr_dbfs(v(AD9237, "snr_dbc"), v(AD9237, "ain_dbfs"))
    ltc_dbfs = v(LTC2292, "snr_db_ltc2294")
    out = {"ideal_12bit_db": ideal_snr_db(12), "decimation": decim,
           "decim_gain_db": 10 * math.log10(decim)}
    for name, span, snr in (("ad9237", v(AD9237, "span_vpp"), ad_dbfs),
                            ("ltc2292", v(LTC2292, "span_vpp"), ltc_dbfs)):
        vfs, vn, dens = noise_from_snr(span, snr, fs)
        out[name] = {"snr_dbfs": snr, "vfs_rms_v": vfs, "noise_rms_uv": vn * 1e6,
                     "density_nv_rthz": dens * 1e9, "lsb_uv": lsb_v(span) * 1e6,
                     "snr_decimated_dbfs": snr + out["decim_gain_db"]}
    out["delta_db"] = out["ltc2292"]["snr_dbfs"] - out["ad9237"]["snr_dbfs"]
    return out


def combine_db(front_end_uv: float, adc_uv: float) -> float:
    """Total rms of two uncorrelated noises, in uV."""
    return math.hypot(front_end_uv, adc_uv)


def dynamic_range(fe_nyq_uv: float, fe_band_uv: float, band_hz: float = 1e6):
    """IF dynamic range at the ADC pins, full scale to total noise, for each ADC.

    fe_nyq_uv: front-end (U45 stage) noise at the pins over 0..fs/2, from the LTspice .noise run;
    fe_band_uv: the same over the decimated band (0..band_hz). ADC noise is white over fs/2,
    so its share of the band is density x sqrt(band). Mixer noise is not included (rf-01)."""
    a = adc_noise()
    out = {}
    for name in ("ad9237", "ltc2292"):
        n = a[name]
        tot = combine_db(fe_nyq_uv, n["noise_rms_uv"])
        adc_band = n["density_nv_rthz"] * 1e-3 * math.sqrt(band_hz)
        tot_band = combine_db(fe_band_uv, adc_band)
        out[name] = {"total_nyq_uv": tot, "dr_nyq_db": 20 * math.log10(n["vfs_rms_v"] / (tot * 1e-6)),
                     "adc_band_uv": adc_band, "total_band_uv": tot_band,
                     "dr_band_db": 20 * math.log10(n["vfs_rms_v"] / (tot_band * 1e-6))}
    out["loss_nyq_db"] = out["ltc2292"]["dr_nyq_db"] - out["ad9237"]["dr_nyq_db"]
    out["loss_band_db"] = out["ltc2292"]["dr_band_db"] - out["ad9237"]["dr_band_db"]
    return out


def input_limits():
    avdd, vref = v(AD9237, "avdd_v"), v(AD9237, "vref_v")
    return {"vcm_min_v": vref / 2, "vcm_max_v": (avdd + vref) / 2,
            "pin_absmax_v": avdd + v(AD9237, "vin_absmax_over_avdd_v"),
            "half_period_ns": 0.5e9 / v(AD9237, "fs_hz"),
            "half_lsb_uv": 0.5 * lsb_v(v(AD9237, "span_vpp")) * 1e6}


def summary():
    return {"rail_3v0": rail_3v0(), "adc_noise": adc_noise(), "input_limits": input_limits()}


if __name__ == "__main__":
    print(json.dumps(summary(), indent=1))
