"""
Peak limiting and loudness normalization.
"""
import numpy as np
import scipy.signal


class MasteringChain:
    """
    Applies final mastering processes to rendered audio.
    """

    def __init__(self, target_rms_db: float = -9.0, true_peak: float = -0.3) -> None:
        """
        Initializes the MasteringChain.

        Args:
            target_rms_db: The target loudness level in dB (RMS).
            true_peak: The maximum true peak level in dBFS.
        """
        self.target_rms_db = target_rms_db
        self.true_peak_linear = 10 ** (true_peak / 20.0)

    def _apply_highpass(self, audio: np.ndarray, sample_rate: int, cutoff: float = 25.0) -> np.ndarray:
        """Applies a high-pass filter using scipy."""
        nyq = 0.5 * sample_rate
        normal_cutoff = cutoff / nyq
        b, a = scipy.signal.butter(4, normal_cutoff, btype='high', analog=False)
        # Apply filter to each channel (audio shape: channels, samples)
        filtered = np.zeros_like(audio)
        for i in range(audio.shape[0]):
            filtered[i] = scipy.signal.lfilter(b, a, audio[i])
        return filtered

    def _normalize_rms(self, audio: np.ndarray) -> np.ndarray:
        """Normalizes audio to the target RMS level."""
        # Calculate current RMS
        rms = np.sqrt(np.mean(audio**2))
        if rms < 1e-10:
            return audio

        current_rms_db = 20 * np.log10(rms)
        gain_db = self.target_rms_db - current_rms_db
        gain_linear = 10 ** (gain_db / 20.0)

        return audio * gain_linear

    def apply_limiting(self, audio: np.ndarray) -> np.ndarray:
        """
        Applies a peak limiter to the audio to prevent clipping.

        Args:
            audio: The input audio array.

        Returns:
            The limited audio array.
        """
        pass

    def normalize_loudness(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Normalizes the audio to the target LUFS level.

        Args:
            audio: The input audio array.
            sample_rate: The audio sample rate.

        Returns:
            The loudness-normalized audio array.
        """
        pass

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Applies the complete native mastering chain (filtering, normalization, soft clipping/limiting).

        Args:
            audio: The input audio array. (Shape: channels, samples)
            sample_rate: The audio sample rate.

        Returns:
            The fully mastered audio array.
        """
        # 1. High-pass filter (cut sub-rumble below 25 Hz)
        audio = self._apply_highpass(audio, sample_rate, cutoff=25.0)

        # 2. Normalize to competitive Trap loudness (-9 dB RMS target)
        audio = self._normalize_rms(audio)

        # 3. Simple soft clipper/limiter to keep true peak < -0.3 dBFS
        # A simple hyperbolic tangent (tanh) soft clipper scaled to the true peak limit
        # audio / limit scales it so peak is 1, tanh keeps it < 1, then scale back to limit.
        # To avoid heavy distortion on quiet parts, we only heavily affect peaks.
        # Simple hard-clip fallback: np.clip(audio, -self.true_peak_linear, self.true_peak_linear)
        # Using a soft clip:
        audio = np.tanh(audio) * self.true_peak_linear

        return audio
