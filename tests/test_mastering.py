import numpy as np
import pytest
from beatbattle.mastering import MasteringChain

def test_mastering_chain_processing():
    mastering = MasteringChain(target_rms_db=-9.0, true_peak=-0.3)
    sr = 44100

    # Create a dummy stereo signal with loud peaks and multiple frequencies
    t = np.linspace(0, 1.0, sr)
    # 20 Hz (should be attenuated), 55 Hz (boosted), 10 kHz (boosted)
    signal_l = np.sin(2 * np.pi * 20 * t) + np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 10000 * t)
    signal_r = np.sin(2 * np.pi * 20 * t) + np.sin(2 * np.pi * 55 * t) - 0.5 * np.sin(2 * np.pi * 10000 * t)

    audio = np.array([signal_l, signal_r], dtype=np.float32)

    # Intentionally clip it way past 1.0 to test limiting
    audio *= 5.0

    processed = mastering.process(audio, sr)

    # Assert no NaNs
    assert not np.isnan(processed).any()

    # Assert True Peak Compliance
    true_peak_linear = 10 ** (-0.3 / 20.0)
    max_val = np.max(np.abs(processed))

    # Allow a tiny bit of floating point precision wiggle room
    assert max_val <= true_peak_linear + 1e-5

    # We can also assert shape hasn't changed
    assert processed.shape == audio.shape
