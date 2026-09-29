"""
Pattern and song timeline generator.
"""
from typing import List, Dict, Any
import numpy as np
import soundfile as sf
from beatbattle.pitch import detect_fundamental_freq, freq_to_midi, constrain_to_minor_scale, constrain_to_root_or_fifth


def get_midi_note(file_path: str, fmin: float, fmax: float) -> float:
    try:
        data, sr = sf.read(file_path, frames=44100 * 2)
        freq = detect_fundamental_freq(data, sr, fmin=fmin, fmax=fmax)
        if freq > 0:
            return freq_to_midi(freq)
    except Exception:
        pass
    return 60.0


class TrapArranger:
    """
    Arranges audio samples into a 24-bar Trap song timeline at 140 BPM.
    """

    def __init__(self, tempo: float = 140.0) -> None:
        """
        Initializes the TrapArranger. Locks tempo at given value (default 140 BPM).

        Args:
            tempo: The tempo in beats per minute.
        """
        self.tempo = tempo
        self.beats_per_bar = 4
        self.total_bars = 24

        # Calculate duration of one beat in seconds
        self.beat_duration_sec = 60.0 / self.tempo
        self.bar_duration_sec = self.beat_duration_sec * self.beats_per_bar
        self.total_duration_seconds = self.bar_duration_sec * self.total_bars

    def create_timeline(self, library: Any, variation_seed: int | None = None) -> List[Dict[str, Any]]:
        """
        Creates a 24-bar Trap timeline mapping samples from the SampleLibrary.

        Args:
            library: An instance of SampleLibrary.
            variation_seed: An integer seed to vary kick syncopations and hihat rolls.

        Returns:
            A full timeline of events for the song. Each event is a dict containing
            at least 'sample', 'time', and potentially 'metadata'.
        """
        rng = np.random.default_rng(variation_seed)
        events = []

        # Detect root keys to align 808s and tonal one-shots to the synth
        synth_path = (
            library.get_sample("synth_loop_1") or
            library.get_sample("synth_oneshot_1") or
            library.get_sample("synth_loop_2") or
            library.get_sample("synth_oneshot_2")
        )
        bass_path = library.get_sample("808s")

        melody_note = get_midi_note(synth_path, fmin=100.0, fmax=800.0) if synth_path else 60.0
        bass_note = get_midi_note(bass_path, fmin=35.0, fmax=95.0) if bass_path else 60.0

        # Calculate base shift required to match the 808 to the melody's root key
        # Round the shift strictly to the nearest integer semitone
        base_808_shift = round((melody_note % 12) - (bass_note % 12))

        # Keep shift within -6 to +5 semitones to minimize artifacts
        if base_808_shift > 5:
            base_808_shift -= 12
        elif base_808_shift < -6:
            base_808_shift += 12

        # Abort transposition if detected shift exceeds strict limit (+/- 4 semitones) or base notes failed
        if abs(base_808_shift) > 4 or melody_note == 0.0 or bass_note == 0.0:
            base_808_shift = 0

        # Detect tonal center of vox/perc one-shots if possible to tune them
        tonal_oneshots_shift = {}
        for cat in ["vox_oneshot", "perc_oneshot"]:
            cat_path = library.get_sample(cat)
            if cat_path:
                cat_note = get_midi_note(cat_path, fmin=100.0, fmax=800.0)
                raw_shift = round((melody_note % 12) - (cat_note % 12))
                tonal_oneshots_shift[cat] = constrain_to_root_or_fifth(raw_shift)

        def add_event(category: str, beat_time: float, metadata: Dict[str, Any] = None):
            sample_path = library.get_sample(category)
            if sample_path:
                time_sec = beat_time * self.beat_duration_sec
                event = {"sample": sample_path, "time": time_sec, "category": category}
                if metadata:
                    event["metadata"] = metadata
                events.append(event)

        # Simple 8-bar chord progression for 808s: Root -> Minor 6th -> Minor 7th -> Root
        # In natural minor: Minor 6th = 8 semitones (or -4), Minor 7th = 10 semitones (or -2)
        chord_progression = [0, 0, 8, 8, 10, 10, 0, 0]

        main_hihat_pan = rng.choice([-0.2, 0.2])
        opposite_perc_pan = -main_hihat_pan

        synth_loops = [k for k in library.library.keys() if k.startswith("synth_loop_")]
        synth_oneshots = [k for k in library.library.keys() if k.startswith("synth_oneshot_")]

        # Minor pentatonic intervals for short melodies (0, 3, 5, 7, 10)
        pentatonic_intervals = [0, 3, 5, 7, 10]

        for bar in range(self.total_bars):
            start_beat = bar * self.beats_per_bar

            # Beat cut check: total beat cut on beats 3 and 4 of bar 4 (index 3) and bar 12 (index 11) for drums/808
            def should_skip_drum_beat(beat_time):
                if bar in [3, 11] and (beat_time - start_beat) >= 2.0:
                    return True
                return False

            def safe_add(category: str, beat_time: float, metadata: Dict[str, Any] = None):
                # Don't cut melodies, only drums/bass on the cut sections
                if category.startswith("synth_") or category.startswith("fx"):
                    add_event(category, beat_time, metadata)
                elif not should_skip_drum_beat(beat_time):
                    add_event(category, beat_time, metadata)

            # Determine 808 pitch for this bar, applying base root key shift constrained to natural minor
            bar_in_progression = bar % 8
            raw_pitch = base_808_shift + chord_progression[bar_in_progression]
            current_pitch = constrain_to_minor_scale(raw_pitch)

            # Turnaround glide on bars 4 (index 3) and 8 (index 7)
            glide = (bar_in_progression == 3 or bar_in_progression == 7)

            # Turnaround/accent markers
            is_turnaround = bar % 4 == 3

            # Intro / Bridge Ambiance
            if bar == 0 or bar == 12:
                safe_add("fx_texture", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "attenuate": -14.0})

            # Bars 1-4 (Intro): melodies, snares/claps on beat 3 on bars 3-4, fx_oneshot, and dry Vox on bar 4
            if bar < 4:
                if bar == 0:
                    intro_metadata = {"halftime": True, "duration": 4 * self.bar_duration_sec}
                    if rng.random() < 0.5:
                        intro_metadata["filter_sweep_intro"] = True
                    else:
                        intro_metadata["filter_sweep"] = True # Static muffled fallback

                    safe_add("fx_oneshot", start_beat) # Impact downbeat bar 1

                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata=intro_metadata)

                # Short melodies (syncopated arps/hits)
                for s_one in synth_oneshots:
                    # Rhythmic Trap Pattern: beats 0, 1.5, 2.5, 3.75
                    arp_beats = [0, 1.5, 2.5, 3.75]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals)
                        # Optionally drop octave down for some hits
                        if rng.random() < 0.2:
                            pitch -= 12
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch)})

                if bar >= 2: # Bars 3-4 (index 2-3)
                    safe_add("snares", start_beat + 2) # Beat 3
                if bar == 3: # Bar 4
                    if rng.random() < 0.33:
                        safe_add("fx_oneshot", start_beat + 3, metadata={"tape_stop": True}) # Pre-drop transition bar 4 beat 4
                    else:
                        safe_add("fx_oneshot", start_beat + 3)
                    safe_add("vox_oneshot", start_beat + 3.5, metadata={"pan": 0.5}) # Final half-beat panned right

            # Bars 5-12 (Drop 1)
            elif 4 <= bar < 12:
                if bar == 4:
                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata={"duration": 8 * self.bar_duration_sec})
                    safe_add("fx_oneshot", start_beat) # Impact downbeat
                    safe_add("vox_loop", start_beat, metadata={"duration": 8 * self.bar_duration_sec, "lpf": 5000, "attenuate": -12.0})
                    safe_add("perc_loop", start_beat, metadata={"duration": 8 * self.bar_duration_sec, "attenuate": -6.0})

                for s_one in synth_oneshots:
                    arp_beats = [0, 1.5, 2.5, 3.75]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals)
                        if rng.random() < 0.2:
                            pitch -= 12
                        # Occasional double hit for variation (1/16th later)
                        if rng.random() < 0.3:
                            safe_add(s_one, start_beat + ab + 0.25, metadata={"pitch_shift": int(pitch), "attenuate": -6.0})
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch)})

                safe_add("kicks", start_beat) # Kick on beat 1

                # Vary kick syncopation based on seed (including 16th note off-beats)
                # Pick randomly between 3 distinct kick syncopation templates
                kick_template = rng.choice([0, 1, 2])
                kick_hits = []
                if kick_template == 0:
                    kick_hits = [1.5]
                elif kick_template == 1:
                    kick_hits = [2.5]
                elif kick_template == 2:
                    kick_hits = [2.75, 3.5]

                for k_pos in kick_hits:
                    safe_add("kicks", start_beat + k_pos)
                    safe_add("808s", start_beat + k_pos, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})

                # 808s with ducking metadata matching kicks and pitch
                safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})

                safe_add("snares", start_beat + 2) # Snare on beat 3

                # Pick randomly between 2 hi-hat roll densities
                hihat_density = rng.choice([0, 1])

                # 1/8 hihats (every 0.5 beats)
                for i in range(8):
                    if hihat_density == 1 and i % 2 != 0:
                        continue # sparse hi-hats
                    safe_add("hihats", start_beat + i * 0.5, metadata={"pan": main_hihat_pan})

                # Rolls on even bars
                if bar % 2 == 1: # "Even" in 1-based indexing, odd in 0-based indexing
                    roll_start = rng.choice([2.0, 3.0, 3.25])
                    # 1/32 rolls with velocity ramp and alternating panning
                    safe_add("hihats", start_beat + roll_start, metadata={"velocity": 0.5, "pan": -0.8})
                    safe_add("hihats", start_beat + roll_start + 0.125, metadata={"velocity": 0.7, "pan": 0.8})
                    safe_add("hihats", start_beat + roll_start + 0.25, metadata={"velocity": 0.9, "pan": -0.8})
                    safe_add("hihats", start_beat + roll_start + 0.375, metadata={"velocity": 1.0, "pan": 0.8})

                safe_add("open_hats", start_beat + 1.5, metadata={"pan": main_hihat_pan})

                # Syncopated ghost hits and vocals
                if is_turnaround:
                    safe_add("vox_oneshot", start_beat + 2.5, metadata={"pan": -0.5, "pitch_shift": tonal_oneshots_shift.get("vox_oneshot", 0)})
                    safe_add("perc_oneshot", start_beat + 3.75, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

            # Bars 13-16 (Breakdown)
            elif 12 <= bar < 16:
                if bar == 12:
                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata={"duration": 4 * self.bar_duration_sec, "filter_sweep": True})
                    safe_add("vox_loop", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "lpf": 5000, "attenuate": -14.0})

                for s_one in synth_oneshots:
                    # Sparse arpeggio on Breakdown
                    arp_beats = [0, 2]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals)
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch), "lpf": 2000})

                if bar == 15: # Bar 16
                    safe_add("fx_oneshot", start_beat + 3) # Pre-drop transition bar 16 beat 4

                # Light percussion, no 808s or kicks
                safe_add("snares", start_beat + 2)
                safe_add("perc_oneshot", start_beat + 1.75, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

                # Sparse hihats
                for i in range(4):
                    safe_add("hihats", start_beat + i * 1.0, metadata={"pan": main_hihat_pan})

            # Bars 17-20 (Second Hard Drop)
            elif 16 <= bar < 20:
                if bar == 16:
                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata={"duration": 4 * self.bar_duration_sec})
                    safe_add("fx_oneshot", start_beat) # Impact on drop
                    safe_add("vox_loop", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "lpf": 5000, "attenuate": -10.0})
                    safe_add("perc_loop", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "attenuate": -6.0})

                for s_one in synth_oneshots:
                    arp_beats = [0, 1.5, 2.5, 3.75]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals)
                        if rng.random() < 0.2:
                            pitch -= 12
                        if rng.random() < 0.3:
                            safe_add(s_one, start_beat + ab + 0.25, metadata={"pitch_shift": int(pitch), "attenuate": -6.0})
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch)})

                # Kick variation
                safe_add("kicks", start_beat)
                safe_add("kicks", start_beat + 1.5)
                safe_add("kicks", start_beat + 3.5)

                safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})
                safe_add("808s", start_beat + 1.5, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})

                safe_add("snares", start_beat + 2)

                # Aggressive hihat rolls (1/16 triplets approximation and 1/32)
                # Alternating behavior
                for i in range(16):
                    vel = 0.5 + (i / 32.0) # velocity ramp
                    pan_val = -0.8 if i % 2 == 0 else 0.8
                    safe_add("hihats", start_beat + i * 0.25, metadata={"velocity": vel, "pan": pan_val})

                safe_add("perc_oneshot", start_beat + 1.75, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})
                safe_add("perc_oneshot", start_beat + 3.25, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

                if is_turnaround:
                    safe_add("vox_oneshot", start_beat + 3.5, metadata={"pan": 0.5, "pitch_shift": tonal_oneshots_shift.get("vox_oneshot", 0)})

            # Bars 21-24 (Outro)
            elif 20 <= bar < 24:
                if bar == 20:
                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata={"duration": 4 * self.bar_duration_sec})

                for s_one in synth_oneshots:
                    arp_beats = [0, 2]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals)
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch), "attenuate": -6.0})

                # Light percs on offbeat
                safe_add("perc_oneshot", start_beat + 1.5, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

                if bar < 22: # Cut 808 and kicks at bar 23 (index 22)
                    safe_add("kicks", start_beat)
                    safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch})

        return events


class SongArranger:
    """
    Arranges audio samples and patterns into a complete song timeline.
    """

    def __init__(self, tempo: float = 120.0, time_signature: tuple[int, int] = (4, 4)) -> None:
        """
        Initializes the SongArranger.

        Args:
            tempo: The tempo of the song in beats per minute (BPM).
            time_signature: The time signature of the song (numerator, denominator).
        """
        pass

    def generate_pattern(self, samples: List[Dict[str, Any]], length_beats: int) -> List[Dict[str, Any]]:
        """
        Generates a rhythmic pattern from a list of samples.

        Args:
            samples: A list of sample dictionaries.
            length_beats: The length of the pattern in beats.

        Returns:
            A list of events defining the pattern.
        """
        pass

    def create_timeline(self, patterns: List[List[Dict[str, Any]]], arrangement_structure: List[str]) -> List[Dict[str, Any]]:
        """
        Creates a complete song timeline by assembling patterns according to a structure.

        Args:
            patterns: A list of patterns (lists of events).
            arrangement_structure: A list of pattern identifiers indicating the order.

        Returns:
            A full timeline of events for the song.
        """
        pass
