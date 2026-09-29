import numpy as np
import pytest
from beatbattle.pitch import (
    freq_to_midi,
    detect_fundamental_freq,
    constrain_to_minor_scale,
    constrain_to_root_or_fifth
)

def generate_sine_wave(freq, sr, duration):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t)

def test_freq_to_midi():
    assert abs(freq_to_midi(440.0) - 69.0) < 0.01
    assert abs(freq_to_midi(220.0) - 57.0) < 0.01

def test_detect_fundamental_freq_808():
    sr = 44100
    # Generate 55Hz (A1)
    audio = generate_sine_wave(55.0, sr, 1.0)

    freq = detect_fundamental_freq(audio, sr, fmin=35, fmax=95)
    assert abs(freq - 55.0) < 1.0

def test_detect_fundamental_freq_prominence():
    sr = 44100
    # Create white noise to ensure correlation peak is low, thus failing prominence check
    np.random.seed(42)
    audio = np.random.uniform(-1.0, 1.0, sr)
    freq = detect_fundamental_freq(audio, sr, fmin=100, fmax=800)
    # Because there's no strong fundamental, prominence check (<0.6) should trigger and return 0.0
    assert freq == 0.0

def test_detect_fundamental_freq_melody():
    sr = 44100
    # Generate 440Hz (A4)
    audio = generate_sine_wave(440.0, sr, 1.0)

    freq = detect_fundamental_freq(audio, sr, fmin=100, fmax=800)
    assert abs(freq - 440.0) < 5.0 # allow slight wiggle room for autocorrelation resolution

def test_constrain_to_minor_scale():
    # Natural minor intervals: 0, 2, 3, 5, 7, 8, 10
    assert constrain_to_minor_scale(0) == 0
    assert constrain_to_minor_scale(1) == 0 # nearest 0 or 2, favors first matching usually or min diff
    assert constrain_to_minor_scale(4) == 3 or constrain_to_minor_scale(4) == 5
    assert constrain_to_minor_scale(8) == 8
    assert constrain_to_minor_scale(11) == 10

    # Octave up
    assert constrain_to_minor_scale(12) == 12
    assert constrain_to_minor_scale(15) == 15

def test_constrain_to_root_or_fifth():
    # intervals: 0, 7, 12
    assert constrain_to_root_or_fifth(0) == 0
    assert constrain_to_root_or_fifth(2) == 0
    assert constrain_to_root_or_fifth(4) == 7
    assert constrain_to_root_or_fifth(8) == 7
    assert constrain_to_root_or_fifth(11) == 12

    # Negative octave
    assert constrain_to_root_or_fifth(-5) == -5 # -12 + 7 = -5
    assert constrain_to_root_or_fifth(-1) == 0
