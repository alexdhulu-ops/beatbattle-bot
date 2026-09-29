"""
Audio stitching and DSP via Pedalboard.
"""
from typing import List, Dict, Any
import numpy as np
import soundfile as sf
import scipy.signal


class AudioRenderer:
    """
    Renders a song timeline into continuous audio data.
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        """
        Initializes the AudioRenderer.

        Args:
            sample_rate: The audio sample rate to use for rendering.
        """
        self.sample_rate = sample_rate

    def _apply_biquad(self, audio: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
        """Applies a filter to stereo audio."""
        filtered = np.zeros_like(audio)
        for i in range(audio.shape[0]):
            filtered[i] = scipy.signal.lfilter(b, a, audio[i])
        return filtered

    def _process_melody_dsp(self, audio: np.ndarray) -> np.ndarray:
        """
        Applies DSP to melody tracks:
        1. High-pass filter (Butterworth 2nd order around 200 Hz).
        2. Low-pass cut (Butterworth 2nd order around 7500 Hz).
        3. Stereo widening (Haas effect, ~15ms delay on right channel).
        """
        nyq = 0.5 * self.sample_rate

        # High-pass filter at 200 Hz
        hp_cutoff = 200.0 / nyq
        b_hp, a_hp = scipy.signal.butter(2, hp_cutoff, btype='high', analog=False)
        audio = self._apply_biquad(audio, b_hp, a_hp)

        # Low-pass filter at 7500 Hz
        lp_cutoff = 7500.0 / nyq
        b_lp, a_lp = scipy.signal.butter(2, lp_cutoff, btype='low', analog=False)
        audio = self._apply_biquad(audio, b_lp, a_lp)

        # Haas effect: delay right channel (channel 1) by ~15 ms
        delay_ms = 15.0
        delay_samples = int((delay_ms / 1000.0) * self.sample_rate)

        # Pad and shift the right channel
        right_channel = audio[1]
        delayed_right = np.pad(right_channel, (delay_samples, 0), mode='constant')[:-delay_samples]
        audio[1] = delayed_right

        return audio

    def render_timeline(self, timeline: List[Dict[str, Any]]) -> np.ndarray:
        """
        Renders a sequence of events into an audio array, with a hard cut at 43.5 seconds.

        Args:
            timeline: A list of events defining the song timeline.

        Returns:
            A numpy array representing the rendered audio (stereo, 44100Hz).
        """
        max_duration_sec = 43.5
        max_samples = int(max_duration_sec * self.sample_rate)

        # Main stereo buffer
        master_buffer = np.zeros((2, max_samples), dtype=np.float32)

        # Find all kick times to trigger sidechain ducking on 808s
        kick_times = [event["time"] for event in timeline if event.get("category") == "kicks"]

        # Cache loaded samples to avoid reading the same file multiple times
        sample_cache = {}

        for event in timeline:
            file_path = event["sample"]
            start_time_sec = event["time"]
            category = event.get("category")

            if start_time_sec >= max_duration_sec:
                continue # Skip events that start after the max duration

            start_sample = int(start_time_sec * self.sample_rate)

            # Load sample if not in cache
            if file_path not in sample_cache:
                data, sr = sf.read(file_path, always_2d=True)

                # Convert to stereo if mono
                if data.shape[1] == 1:
                    data = np.repeat(data, 2, axis=1)

                # Transpose to shape (channels, samples)
                data = data.T

                # Resample if necessary (using simple linear interpolation for this stub, or just raise error)
                # In this system, we expect all samples to be 44.1k or we could use librosa.
                # For simplicity in this engine, we will assume sf.read loads them, but we enforce shape.
                sample_cache[file_path] = (data, sr)

            audio_data, sr = sample_cache[file_path]

            if category == "melodies":
                audio_data = self._process_melody_dsp(audio_data.copy())

                # Sidechain ducking for melodies triggered by kicks
                for kt in kick_times:
                    # If kick hits while melody is playing
                    if start_time_sec <= kt < start_time_sec + (audio_data.shape[1] / sr):
                        duck_start_sample = int((kt - start_time_sec) * sr)

                        # Ducking params: -6dB is ~0.501 linear, 100ms decay
                        ducking_linear = 10 ** (-6 / 20)
                        decay_samples = int(0.100 * sr)

                        duck_end_sample = min(duck_start_sample + decay_samples, audio_data.shape[1])
                        actual_decay_len = duck_end_sample - duck_start_sample

                        # Apply ducking envelope (fast attack, linear decay)
                        envelope = np.linspace(ducking_linear, 1.0, actual_decay_len)
                        audio_data[:, duck_start_sample:duck_end_sample] *= envelope

            # Very basic sidechain simulation for 808s
            elif category == "808s":
                audio_data = audio_data.copy()
                for kt in kick_times:
                    # If kick hits while 808 is playing
                    if start_time_sec <= kt < start_time_sec + (audio_data.shape[1] / sr):
                        duck_start_sample = int((kt - start_time_sec) * sr)

                        # Ducking params: -4dB is ~0.63 linear, 60ms decay
                        ducking_linear = 10 ** (-4 / 20)
                        decay_samples = int(0.06 * sr)

                        duck_end_sample = min(duck_start_sample + decay_samples, audio_data.shape[1])
                        actual_decay_len = duck_end_sample - duck_start_sample

                        # Apply ducking envelope (fast attack, linear decay)
                        envelope = np.linspace(ducking_linear, 1.0, actual_decay_len)
                        audio_data[:, duck_start_sample:duck_end_sample] *= envelope

            end_sample = start_sample + audio_data.shape[1]

            if end_sample > max_samples:
                # Truncate audio_data to fit the buffer
                valid_len = max_samples - start_sample
                audio_data = audio_data[:, :valid_len]
                end_sample = max_samples

            master_buffer[:, start_sample:end_sample] += audio_data

        # Apply 0.5s fade out at the end
        fade_sec = 0.5
        fade_samples = int(fade_sec * self.sample_rate)
        if master_buffer.shape[1] >= fade_samples:
             fade_curve = np.linspace(1.0, 0.0, fade_samples)
             master_buffer[:, -fade_samples:] *= fade_curve

        return master_buffer

    def apply_dsp(self, audio: np.ndarray, effects_chain: List[Any]) -> np.ndarray:
        """
        Applies a chain of native DSP effects to audio data.

        Args:
            audio: The input audio array.
            effects_chain: A list of effects to apply.

        Returns:
            The processed audio array.
        """
        pass
