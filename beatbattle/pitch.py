"""
Automated pitch detection and musical key matching.
"""
import numpy as np
import scipy.signal


def freq_to_midi(freq: float) -> float:
    """
    Converts a frequency in Hz to a MIDI note number.
    A4 = 440 Hz = MIDI note 69.
    """
    if freq <= 0:
        return 0.0
    return 69 + 12 * np.log2(freq / 440.0)


def detect_fundamental_freq(audio: np.ndarray, sample_rate: int, fmin: float = 35.0, fmax: float = 90.0, required_confidence: float = 0.65) -> float:
    """
    Detects the fundamental frequency of an audio buffer using autocorrelation.

    Args:
        audio: 1D or 2D numpy array containing the audio data.
        sample_rate: The sample rate of the audio data.
        fmin: The minimum frequency to search for.
        fmax: The maximum frequency to search for.
        required_confidence: The required correlation confidence threshold.

    Returns:
        The detected fundamental frequency in Hz. Returns 0.0 if detection fails.
    """
    if len(audio.shape) > 1:
        # Mix to mono for detection
        audio = np.mean(audio, axis=0) if audio.shape[0] < audio.shape[1] else np.mean(audio, axis=1)

    if len(audio) == 0:
        return 0.0

    # Perform full autocorrelation
    corr = scipy.signal.correlate(audio, audio, mode='full')
    corr = corr[len(corr) // 2:]

    # Define the valid lag range based on fmin and fmax
    min_lag = int(sample_rate / fmax)
    max_lag = int(sample_rate / fmin)

    if max_lag >= len(corr):
        max_lag = len(corr) - 1

    if min_lag >= max_lag:
        return 0.0

    # Find peaks in the valid range
    corr_slice = corr[min_lag:max_lag]
    peaks, _ = scipy.signal.find_peaks(corr_slice)

    if len(peaks) > 0:
        best_peak_idx = peaks[np.argmax(corr_slice[peaks])]
        best_peak_val = corr_slice[best_peak_idx]

        # Confidence/peak-prominence check
        if corr[0] > 0 and (best_peak_val / corr[0]) >= required_confidence:
            lag = best_peak_idx + min_lag
            freq = sample_rate / lag
            return freq

    return 0.0


def constrain_to_minor_scale(target_shift: int) -> int:
    """
    Constrains a desired semitone shift to the nearest interval
    in the natural minor scale relative to the root (0).
    Minor scale intervals: 0, 2, 3, 5, 7, 8, 10
    """
    minor_intervals = [0, 2, 3, 5, 7, 8, 10]

    # Normalize shift to a single octave to find the nearest scale degree
    octave = target_shift // 12
    semitone = target_shift % 12

    nearest = min(minor_intervals, key=lambda x: abs(x - semitone))
    return int(octave * 12 + nearest)


def constrain_to_root_or_fifth(target_shift: int) -> int:
    """
    Constrains a desired semitone shift to the nearest root (0, 12, etc.)
    or perfect fifth (7) relative to the scale root.
    """
    intervals = [0, 7, 12]

    octave = target_shift // 12
    semitone = target_shift % 12

    nearest = min(intervals, key=lambda x: abs(x - semitone))

    # If it clamped to 12, bump the octave up
    if nearest == 12:
        octave += 1
        nearest = 0

    return int(octave * 12 + nearest)
