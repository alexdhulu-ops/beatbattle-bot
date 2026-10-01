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

    def _process_melody_dsp(self, audio: np.ndarray, metadata: Dict[str, Any] = None) -> np.ndarray:
        """
        Applies DSP to melody tracks:
        1. High-pass filter (Butterworth 2nd order around 140 Hz).
        2. Low-pass cut (Butterworth 2nd order around 7500 Hz).
        3. Stereo widening (Haas effect, ~15ms delay on right channel).
        """
        nyq = 0.5 * self.sample_rate

        metadata = metadata or {}

        # Halftime / Pitch down (-12 semitones, 0.5x speed)
        if metadata.get("halftime"):
            # Resample length to 2x (slow down) which intrinsically lowers pitch by an octave when played at original sample rate
            new_len = int(audio.shape[1] * 2.0)
            # scipy.signal.resample processes along the last axis by default
            audio = scipy.signal.resample(audio, new_len, axis=1)

        # High-pass filter at 35-40 Hz to cleanly remove low-end rumble while retaining body
        hp_cutoff = 38.0 / nyq
        b_hp, a_hp = scipy.signal.butter(2, hp_cutoff, btype='high', analog=False)
        audio = self._apply_biquad(audio, b_hp, a_hp)

        # Low-pass filter (or automate a sweep if requested)
        if metadata.get("filter_sweep_intro"):
            # Implement a chunked time-varying low-pass filter (sweeping from ~800 Hz to 20 kHz)
            num_chunks = max(1, audio.shape[1] // (self.sample_rate // 10)) # ~10 chunks per second
            chunk_size = audio.shape[1] // num_chunks

            filtered_audio = np.zeros_like(audio)

            # Exponentially spaced frequencies for a natural sweep feel
            freqs = np.geomspace(800.0, 20000.0, num_chunks)

            for i in range(num_chunks):
                start = i * chunk_size
                end = start + chunk_size if i < num_chunks - 1 else audio.shape[1]

                chunk = audio[:, start:end]

                cutoff = min(freqs[i], nyq - 1.0) / nyq
                b_lp, a_lp = scipy.signal.butter(2, cutoff, btype='low', analog=False)

                filtered_chunk = self._apply_biquad(chunk, b_lp, a_lp)
                filtered_audio[:, start:end] = filtered_chunk

            audio = filtered_audio
        else:
            if metadata.get("filter_sweep"):
                lp_cutoff = 800.0 / nyq
            else:
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

        # Pre-drop Tape-stop effect
        if metadata.get("tape_stop"):
            # Apply tape stop (pitch/speed deceleration) to the last beat
            # Assumes 140 BPM -> beat duration = 60/140 ~ 0.428s
            # For robustness, just grab the last ~0.5 seconds if available
            tail_sec = min(0.5, audio.shape[1] / self.sample_rate)
            tail_samples = int(tail_sec * self.sample_rate)

            if tail_samples > 1000:
                body_samples = audio.shape[1] - tail_samples

                # We need to stretch/decelerate the tail chunk.
                # A simple interpolation over a warped time axis simulates tape stop
                tail_chunk = audio[:, body_samples:]

                # t_original maps [0, tail_samples] linearly
                t_original = np.arange(tail_samples)

                # By applying an exponential or power curve > 1 to the readout index,
                # we sample increasingly sparsely, simulating slowing down
                # For an extreme tape stop, power = 2 or 3.
                t_warped = (t_original / (tail_samples - 1)) ** 2.5 * (tail_samples - 1)

                stopped_chunk = np.zeros_like(tail_chunk)
                for ch in range(2):
                    stopped_chunk[ch] = np.interp(t_warped, t_original, tail_chunk[ch])

                # To complete the tape stop effect, quickly fade out the very end
                fade_out_samples = int(0.05 * self.sample_rate)
                if fade_out_samples < tail_samples:
                    fade_curve = np.linspace(1.0, 0.0, fade_out_samples)
                    stopped_chunk[:, -fade_out_samples:] *= fade_curve

                audio[:, body_samples:] = stopped_chunk

        return audio

    def render_timeline(self, timeline: List[Dict[str, Any]]) -> np.ndarray:
        """
        Renders a sequence of events into an audio array, with a hard cut at 45.5 seconds.

        Args:
            timeline: A list of events defining the song timeline.

        Returns:
            A numpy array representing the rendered audio (stereo, 44100Hz).
        """
        max_duration_sec = 45.5
        max_samples = int(max_duration_sec * self.sample_rate)

        # Main stereo buffer
        master_buffer = np.zeros((2, max_samples), dtype=np.float32)

        # Find all kick times to trigger sidechain ducking on 808s
        kick_times = [event["time"] for event in timeline if event.get("category") == "kicks"]

        # Determine 808 event start times to enforce monophonic choke
        # We sort them to ensure we grab the immediate next chronological 808 start
        eight08_times = sorted([event["time"] for event in timeline if event.get("category") == "808s"])

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

                # Automatic silence stripping / transient detection to fix timing delays.
                # Find the first index where amplitude crosses a minimal threshold (-40 dBFS ~= 0.01).
                # Actually, requirement specifies: e.g. -40 dBFS or 0.01 * np.max(np.abs(audio))
                abs_max = np.max(np.abs(data))
                if abs_max > 0:
                    threshold = 0.01 * abs_max
                    # Check max amplitude across channels at each sample
                    max_across_channels = np.max(np.abs(data), axis=0)
                    above_threshold_indices = np.where(max_across_channels > threshold)[0]
                    if len(above_threshold_indices) > 0:
                        first_index = above_threshold_indices[0]
                        # Strip all leading samples before that threshold
                        data = data[:, first_index:]

                # Resample if necessary (using simple linear interpolation for this stub, or just raise error)
                # In this system, we expect all samples to be 44.1k or we could use librosa.
                # For simplicity in this engine, we will assume sf.read loads them, but we enforce shape.
                sample_cache[file_path] = (data, sr)

            # ALWAYS copy from the cache to prevent permanent mutation of cached audio arrays
            audio_data, sr = sample_cache[file_path]
            audio_data = audio_data.copy()

            # Mono Summing for Low-End (kicks, 808s)
            if category in ["kicks", "808s"]:
                if audio_data.ndim > 1:
                    mono = np.mean(audio_data, axis=0, keepdims=True)
                    audio_data = np.repeat(mono, 2, axis=0)

            metadata = event.get("metadata", {})

            # General effects: Panning
            if "pan" in metadata:
                # pan value between -1.0 (left) and 1.0 (right)
                pan = metadata["pan"]
                left_gain = np.cos((pan + 1) * np.pi / 4)
                right_gain = np.sin((pan + 1) * np.pi / 4)
                audio_data[0] *= left_gain
                audio_data[1] *= right_gain

            # General effects: LPF
            if "lpf" in metadata:
                nyq = 0.5 * sr
                cutoff = metadata["lpf"] / nyq
                b_lp, a_lp = scipy.signal.butter(2, cutoff, btype='low', analog=False)
                audio_data = self._apply_biquad(audio_data, b_lp, a_lp)

            # General effects: Attenuation (Gain Staging)
            if "attenuate" in metadata:
                gain_linear = 10 ** (metadata["attenuate"] / 20.0)
                audio_data *= gain_linear

            # Base Target Gain Staging relative to kick (0.0 dB reference, target -6.0 dBFS)
            # Normalizing individual track stems relative to each other:
            # Snare/clap is boosted +2.5 to +3.0 dB relative to original -8.0 dB
            target_gains = {
                "kicks": -6.0,
                "808s": -7.5, # -1.5 relative to kick
                "snares": -4.5, # +1.5 relative to kick
                "claps": -4.5,
                "hihats": -16.0, # -10.0 relative to kick
                "open_hats": -16.0,
                "perc_oneshot": -16.0, # -10.0 relative to kick
                "perc_loop": -16.0,
                "vox_oneshot": -18.0, # -12.0 relative to kick
                "vox_loop": -18.0,
                "fx_oneshot": -18.0,
                "fx_texture": -18.0
            }

            target_gain = -9.5 if category.startswith("synth_") else target_gains.get(category)

            if target_gain is not None:
                # Calculate current peak to normalize it, then apply target gain
                current_peak = np.max(np.abs(audio_data))
                if current_peak > 0:
                    audio_data = audio_data / current_peak
                audio_data *= (10 ** (target_gain / 20.0))

            # Per-Track Corrective EQ
            nyq = 0.5 * sr
            if category.startswith("synth_"):
                b_hp, a_hp = scipy.signal.butter(2, 35.0 / nyq, btype='high', analog=False)
                audio_data = self._apply_biquad(audio_data, b_hp, a_hp)

            # Requirement 3: Dynamic Low-Pass Filtering
            if "lpf" in metadata:
                cutoff = metadata["lpf"]
                b_lpf, a_lpf = scipy.signal.butter(2, cutoff / nyq, btype='low', analog=False)
                audio_data = self._apply_biquad(audio_data, b_lpf, a_lpf)
            elif category in ["perc_oneshot", "perc_loop", "vox_oneshot", "vox_loop", "fx_oneshot", "fx_texture", "snares"]:
                b_hp, a_hp = scipy.signal.butter(2, 40.0 / nyq, btype='high', analog=False)
                audio_data = self._apply_biquad(audio_data, b_hp, a_hp)
            elif category == "808s":
                b_hp, a_hp = scipy.signal.butter(2, 28.0 / nyq, btype='high', analog=False)
                audio_data = self._apply_biquad(audio_data, b_hp, a_hp)

                # Gentle notch around 250 Hz (Q=1.0)
                b_n, a_n = scipy.signal.iirnotch(250.0 / nyq, Q=1.0)
                audio_data = self._apply_biquad(audio_data, b_n, a_n)
            elif category in ["hihats", "open_hats"]:
                b_hp, a_hp = scipy.signal.butter(2, 350.0 / nyq, btype='high', analog=False)
                audio_data = self._apply_biquad(audio_data, b_hp, a_hp)

            if category.startswith("synth_"):
                audio_data = self._process_melody_dsp(audio_data, metadata)

            # Length trimming for loops (vox_loop, perc_loop, fx_texture, and synth_loop_X)
            if "duration" in metadata and (category.startswith("synth_loop_") or category in ["vox_loop", "perc_loop", "fx_texture"]):
                target_samples = int(metadata["duration"] * sr)

                # If audio is shorter than target duration and it's a loop, we could time-stretch.
                # A simple naive time-stretch via resampling (since full phase-vocoder is heavy for a stub)
                if audio_data.shape[1] < target_samples and not category.startswith("synth_loop_"):
                    audio_data = scipy.signal.resample(audio_data, target_samples, axis=1)

                if audio_data.shape[1] > target_samples:
                    audio_data = audio_data[:, :target_samples]

                    # Apply a 50ms smooth fade-out at the cut point to prevent clicks
                    fade_sec = 0.050
                    fade_samples = int(fade_sec * sr)
                    if audio_data.shape[1] > fade_samples:
                        # Cosine fade out curve
                        t = np.linspace(0, np.pi/2, fade_samples)
                        fade_curve = np.cos(t)
                        audio_data[:, -fade_samples:] *= fade_curve

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

            # General effects: Pitch Shifting (used for 808s and tonal one-shots)
            if "pitch_shift" in metadata:
                pitch_shift_semitones = metadata["pitch_shift"]
                if pitch_shift_semitones != 0:
                    # Resample to static pitch shift (speed up / slow down)
                    ratio = 2.0 ** (-pitch_shift_semitones / 12.0)
                    new_len = int(audio_data.shape[1] * ratio)
                    audio_data = scipy.signal.resample(audio_data, new_len, axis=1)

            # Apply glide and saturation for 808s based on metadata
            if category == "808s":
                # 808 Monophonic Choke ("cut-self") logic
                # Find the start time of the next 808
                next_808_time = None
                for t in eight08_times:
                    if t > start_time_sec + 0.001: # Avoid matching the current 808's time due to float precision
                        next_808_time = t
                        break

                if next_808_time is not None:
                    # Calculate how many samples until the next 808 hits
                    samples_until_next = int((next_808_time - start_time_sec) * sr)

                    if audio_data.shape[1] > samples_until_next:
                        # Truncate the current 808 right before the next one hits
                        audio_data = audio_data[:, :samples_until_next]

                        # Apply a 5ms linear fade-out to prevent clicks when choking
                        fade_samples = int(0.005 * sr)
                        if audio_data.shape[1] > fade_samples:
                            fade_curve = np.linspace(1.0, 0.0, fade_samples)
                            audio_data[:, -fade_samples:] *= fade_curve
                glide = metadata.get("glide", False)

                # Apply soft-clipping saturation (gain drive -> tanh)
                drive_linear = 2.5
                audio_data = np.tanh(audio_data * drive_linear)

                if glide:
                    # Implement smooth 100-200ms pitch slide envelope.
                    glide_samples = int(0.150 * sr) # 150ms glide
                    if audio_data.shape[1] > glide_samples:
                        t_original = np.arange(glide_samples)
                        t_warped = t_original ** 1.5 / (glide_samples ** 0.5)

                        glided_chunk = np.zeros((2, glide_samples), dtype=np.float32)
                        for ch in range(2):
                            glided_chunk[ch] = np.interp(t_warped, t_original, audio_data[ch, :glide_samples])

                        audio_data[:, :glide_samples] = glided_chunk

            # Volume scaling for hihat velocity
            if "velocity" in event.get("metadata", {}):
                audio_data = audio_data * event["metadata"]["velocity"]

            # Very basic sidechain simulation for 808s
            if category == "808s":
                for kt in kick_times:
                    # If kick hits while 808 is playing
                    if start_time_sec <= kt < start_time_sec + (audio_data.shape[1] / sr):
                        duck_start_sample = int((kt - start_time_sec) * sr)

                        # Ducking params: ~4-6 dB dip, 80-120ms release
                        ducking_linear = 10 ** (-5.0 / 20)
                        decay_samples = int(0.100 * sr)

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

        # Apply 1.5s exponential fade out at the end to naturally decay tails
        fade_sec = 1.5
        fade_samples = int(fade_sec * self.sample_rate)
        if master_buffer.shape[1] >= fade_samples:
             # Exponential curve down to 0
             t = np.linspace(1.0, 0.0, fade_samples)
             fade_curve = t ** 2.0
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
