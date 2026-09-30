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

    def _apply_highpass(self, audio: np.ndarray, sample_rate: int, cutoff: float = 28.0) -> np.ndarray:
        """Applies a high-pass filter using scipy sosfilt to remove DC/sub-rumble."""
        nyq = 0.5 * sample_rate
        normal_cutoff = cutoff / nyq
        sos = scipy.signal.butter(4, normal_cutoff, btype='high', analog=False, output='sos')
        # Apply filter to each channel (audio shape: channels, samples)
        filtered = np.zeros_like(audio)
        for i in range(audio.shape[0]):
            filtered[i] = scipy.signal.sosfilt(sos, audio[i])
        return filtered

    def _apply_peaking_eq(self, audio: np.ndarray, sample_rate: int, f0: float, gain_db: float, Q: float) -> np.ndarray:
        """Applies a peaking EQ filter using a biquad design from scipy."""
        # Simple analog peaking filter transformation to digital is complex manually,
        # but scipy provides iircomb or peaking via peak/notch, though standard peaking
        # requires direct biquad coefficient calculation (RBJ Cookbook).
        A = 10 ** (gain_db / 40.0)
        w0 = 2 * np.pi * f0 / sample_rate
        alpha = np.sin(w0) / (2 * Q)

        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A

        b = np.array([b0, b1, b2]) / a0
        a = np.array([a0, a1, a2]) / a0

        filtered = np.zeros_like(audio)
        for i in range(audio.shape[0]):
            filtered[i] = scipy.signal.lfilter(b, a, audio[i])
        return filtered

    def _apply_high_shelf(self, audio: np.ndarray, sample_rate: int, f0: float, gain_db: float, Q: float = 0.707) -> np.ndarray:
        """Applies a high-shelf EQ filter (RBJ Cookbook)."""
        A = 10 ** (gain_db / 40.0)
        w0 = 2 * np.pi * f0 / sample_rate
        alpha = np.sin(w0) / (2 * Q)

        b0 = A * ((A+1) + (A-1)*np.cos(w0) + 2*np.sqrt(A)*alpha)
        b1 = -2*A * ((A-1) + (A+1)*np.cos(w0))
        b2 = A * ((A+1) + (A-1)*np.cos(w0) - 2*np.sqrt(A)*alpha)
        a0 = (A+1) - (A-1)*np.cos(w0) + 2*np.sqrt(A)*alpha
        a1 = 2 * ((A-1) - (A+1)*np.cos(w0))
        a2 = (A+1) - (A-1)*np.cos(w0) - 2*np.sqrt(A)*alpha

        b = np.array([b0, b1, b2]) / a0
        a = np.array([a0, a1, a2]) / a0

        filtered = np.zeros_like(audio)
        for i in range(audio.shape[0]):
            filtered[i] = scipy.signal.lfilter(b, a, audio[i])
        return filtered

    def _apply_trap_eq(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Applies the master bus curve (Trap EQ)."""
        # Low-end warmth (+1.5 dB @ 55 Hz, Q=1.0)
        audio = self._apply_peaking_eq(audio, sample_rate, f0=55.0, gain_db=1.5, Q=1.0)
        # Mud cut (-1.0 dB @ 350 Hz, Q=1.2)
        audio = self._apply_peaking_eq(audio, sample_rate, f0=350.0, gain_db=-1.0, Q=1.2)
        # High-end sheen (+1.5 dB @ 10 kHz, standard Q)
        audio = self._apply_high_shelf(audio, sample_rate, f0=10000.0, gain_db=1.5, Q=0.707)
        return audio

    def _apply_mid_side(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Splits signal into Mid/Side, boosts Side channel high frequencies,
        and reconstructs L/R for stereo widening.
        """
        # Ensure stereo
        if audio.shape[0] != 2:
            return audio

        L = audio[0]
        R = audio[1]

        # M/S Encoding
        M = (L + R) / np.sqrt(2)
        S = (L - R) / np.sqrt(2)

        # We need to process S as a 2D array to use our helper methods
        S_2d = np.array([S])

        # Boost side channel above 2.5 kHz by +1.0 dB
        S_2d = self._apply_high_shelf(S_2d, sample_rate, f0=2500.0, gain_db=1.0, Q=0.707)

        S = S_2d[0]

        # M/S Decoding
        new_L = (M + S) / np.sqrt(2)
        new_R = (M - S) / np.sqrt(2)

        return np.array([new_L, new_R])

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

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Applies the complete native mastering chain (filtering, normalization, soft clipping/limiting).

        Args:
            audio: The input audio array. (Shape: channels, samples)
            sample_rate: The audio sample rate.

        Returns:
            The fully mastered audio array.
        """
        # 1. High-pass filter (cut sub-rumble below 28 Hz using sosfilt)
        audio = self._apply_highpass(audio, sample_rate, cutoff=28.0)

        # 2. Apply Master Bus Curve (Trap EQ)
        audio = self._apply_trap_eq(audio, sample_rate)

        # 3. Mid/Side Balance (Stereo widening)
        audio = self._apply_mid_side(audio, sample_rate)

        # 4. Normalize to competitive Trap loudness (-9 dB RMS target)
        audio = self._normalize_rms(audio)

        # 5. Stage 1: Soft Clipper (np.tanh) to glue mix and round off transients
        drive = 1.2
        audio = np.tanh(audio * drive)

        # 6. Stage 2: Lookahead Limiter / Ceiling (-0.3 dBFS)
        # We find the new absolute peak and scale it exactly to the true peak limit.
        max_peak = np.max(np.abs(audio))
        if max_peak > 0:
            audio = (audio / max_peak) * self.true_peak_linear

        return audio
