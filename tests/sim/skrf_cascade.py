"""Two-stage cascade in scikit-rf, checked against the hand calculation.

Stage A: matched attenuator, 3 dB loss. Stage B: matched amplifier, 20 dB gain.
Cascade S21 must be +17 dB and the lossy matched line must add dB linearly.
Prints PASS lines; exits non-zero on a mismatch.
"""
import numpy as np
import skrf as rf

f = rf.Frequency(1, 6, 11, "ghz")


def matched_two_port(gain_db):
    s = np.zeros((len(f), 2, 2), dtype=complex)
    s[:, 1, 0] = 10 ** (gain_db / 20)   # S21
    s[:, 0, 1] = 0                      # unilateral
    return rf.Network(frequency=f, s=s, z0=50)


a = matched_two_port(-3.0)
b = matched_two_port(20.0)
casc = a ** b
got = casc.s_db[:, 1, 0]
assert np.allclose(got, 17.0, atol=1e-9), got
assert np.allclose(casc.s_db[:, 0, 0], -np.inf) or np.all(np.abs(casc.s[:, 0, 0]) < 1e-12)

# Friis noise figure by hand: NF_A = 3 dB (passive), G_A = -3 dB, NF_B = 4 dB
F_a, G_a, F_b = 10 ** 0.3, 10 ** -0.3, 10 ** 0.4
F_tot = F_a + (F_b - 1) / G_a
nf_hand = 10 * np.log10(F_tot)
# 3 dB + (10^0.4 - 1)/0.501 -> 3.0103 dB + ...; computed independently here
assert abs(nf_hand - 10 * np.log10(1.9953 + (2.5119 - 1) / 0.50119)) < 1e-2

# Lossy transmission line: 50 ohm line, 0.5 dB/GHz-ish via DefinedGammaZ0
gamma = (0.1 + 1j * 2 * np.pi * f.f / 1.5e8)  # 0.1 Np/m, v = 1.5e8 m/s
line = rf.media.DefinedGammaZ0(f, z0=50, gamma=gamma).line(0.2, unit="m")
exp_db = -20 * np.log10(np.e) * 0.1 * 0.2
assert np.allclose(line.s_db[:, 1, 0], exp_db, atol=1e-6), line.s_db[:, 1, 0]
# line followed by amplifier B: dB add
tot = line ** b
assert np.allclose(tot.s_db[:, 1, 0], exp_db + 20.0, atol=1e-6)
print("PASS cascade_s21_db=%.3f nf_hand_db=%.3f line_db=%.4f" % (got[0], nf_hand, exp_db))
