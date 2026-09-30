"""
Pattern and song timeline generator.
"""
from typing import List, Dict, Any
import numpy as np
import soundfile as sf
from beatbattle.pitch import detect_fundamental_freq, freq_to_midi, key_to_midi, constrain_to_minor_scale, constrain_to_root_or_fifth


def get_midi_note(file_path: str, library: Any, category: str, fmin: float, fmax: float) -> float:
    # First, try to use parsed metadata from the filename (e.g. "_Am_")
    if file_path:
        meta = library.get_metadata(category)
        if meta and "key" in meta:
            parsed_midi = key_to_midi(meta["key"])
            if parsed_midi > 0:
                return parsed_midi

    # Fallback to FFT autocorrelation pitch detection
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

    def create_timeline(self, library: Any, rng: np.random.Generator | None = None) -> List[Dict[str, Any]]:
        """
        Creates a 24-bar Trap timeline mapping samples from the SampleLibrary.

        Args:
            library: An instance of SampleLibrary.
            rng: A numpy random Generator instance for procedural arrangement variation.

        Returns:
            A full timeline of events for the song. Each event is a dict containing
            at least 'sample', 'time', and potentially 'metadata'.
        """
        if rng is None:
            rng = np.random.default_rng()
        events = []

        # Detect root keys to align 808s and tonal one-shots to the synth
        synth_cat = None
        synth_path = None
        for cat in ["synth_loop_1", "synth_oneshot_1", "synth_loop_2", "synth_oneshot_2"]:
            p = library.get_sample(cat)
            if p:
                synth_path = p
                synth_cat = cat
                break

        bass_path = library.get_sample("808s")

        melody_note = get_midi_note(synth_path, library, synth_cat, fmin=100.0, fmax=800.0) if synth_path else 60.0
        bass_note = get_midi_note(bass_path, library, "808s", fmin=35.0, fmax=95.0) if bass_path else 60.0

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
                cat_note = get_midi_note(cat_path, library, cat, fmin=100.0, fmax=800.0)
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

        all_synths = [k for k in library.library.keys() if k.startswith("synth_")]

        # Synth Layering Logic (25% Solo, 50% Duo, 25% Trio)
        synth_count = rng.choice([1, 2, 3], p=[0.25, 0.50, 0.25])
        active_synths = rng.choice(all_synths, size=min(synth_count, len(all_synths)), replace=False).tolist() if all_synths else []

        synth_loops = [s for s in active_synths if "loop" in s]
        synth_oneshots = [s for s in active_synths if "oneshot" in s]

        # FX / Vocals Layering Logic
        all_fx = [k for k in library.library.keys() if k.startswith("fx_")]
        all_vox = [k for k in library.library.keys() if k.startswith("vox_")]

        active_fx = rng.choice(all_fx, size=rng.integers(0, len(all_fx) + 1), replace=False).tolist() if all_fx else []
        active_vox = rng.choice(all_vox, size=rng.integers(0, len(all_vox) + 1), replace=False).tolist() if all_vox else []

        # Minor pentatonic intervals for short melodies (0, 3, 5, 7, 10)
        pentatonic_intervals = [0, 3, 5, 7, 10]

        # 808 Bassline Algorithms
        bass_algorithm = rng.choice(["root_pedal", "octave_bounce", "walking"])

        # Arrangement Flow
        # 0: Intro -> Drop -> Breakdown -> Drop -> Outro (Standard)
        # 1: Drop -> Breakdown -> Verse -> Drop -> Outro (Immediate Drop)
        arrangement_flow = rng.choice([0, 1])

        # Pre-Drop Cut Break (60% chance)
        pre_drop_break = rng.random() < 0.6

        # Half-Time Section (30% chance)
        half_time_section = rng.random() < 0.3

        def get_hihat_vel_and_swing(beat_pos):
            # Alternating accents with jitter
            is_on_beat = (beat_pos % 1.0) < 0.1
            base_vel = rng.uniform(0.85, 0.95) if is_on_beat else rng.uniform(0.65, 0.80)
            jitter = rng.uniform(-0.05, 0.05)
            vel = max(0.0, min(1.0, base_vel + jitter))

            # Swing micro-timing (2-5ms delay on off-beats)
            swing_beats = 0.0
            if not is_on_beat:
                swing_ms = rng.integers(2, 6) # 2 to 5 ms
                swing_beats = (swing_ms / 1000.0) / self.beat_duration_sec

            return vel, swing_beats

        def get_snare_vel():
            return rng.uniform(0.90, 1.0)

        # Intro Lead Synth Choice (Balanced round-robin/uniform across seeds)
        intro_synth = rng.choice(active_synths) if active_synths else None

        # Kick Presence Probability (Active in 70% of generated beats)
        kick_active = rng.random() < 0.70

        # Kick Templates (3 global variations)
        # 0: Standard bounce
        # 1: Heavy off-beat syncopation
        # 2: Sparse bounce
        kick_template = rng.choice([0, 1, 2])

        # Open Hats Presence Probability
        open_hat_active = rng.random() < 0.70

        # Hihat Subdivision Templates (3 global variations)
        # 0: Straight 8ths (every 0.5)
        # 1: Rolling triplets (approximation)
        # 2: Bouncy syncopated (sparse)
        hihat_template = rng.choice([0, 1, 2])

        # Snare/Clap Layering Selection
        # If both are available, randomly choose whether to use Snare, Clap, or Both
        has_snare = library.get_sample("snares") is not None
        has_clap = library.get_sample("claps") is not None

        active_snare_layers = []
        if has_snare and has_clap:
            layer_choice = rng.choice([0, 1, 2])
            if layer_choice == 0:
                active_snare_layers = ["snares"]
            elif layer_choice == 1:
                active_snare_layers = ["claps"]
            else:
                active_snare_layers = ["snares", "claps"]
        elif has_snare:
            active_snare_layers = ["snares"]
        elif has_clap:
            active_snare_layers = ["claps"]

        for bar in range(self.total_bars):
            start_beat = bar * self.beats_per_bar

            # Map logical structure blocks based on arrangement flow
            if arrangement_flow == 0:
                is_intro = bar < 4
                is_drop1 = 4 <= bar < 12
                is_verse = False
                is_breakdown = 12 <= bar < 16
                is_drop2 = 16 <= bar < 20
                is_outro = 20 <= bar < 24
            else:
                is_intro = bar < 4 # Changed from No True Intro to 4-bar Intro to satisfy constraints
                is_drop1 = 4 <= bar < 8
                is_breakdown = 8 <= bar < 12
                # We'll treat bars 12-16 as Verse (similar to Breakdown but with some drums)
                is_verse = 12 <= bar < 16
                is_drop2 = 16 <= bar < 20
                is_outro = 20 <= bar < 24

            # Pre-Drop Break Logic (Cut drums right before drop)
            def is_pre_drop_bar():
                return (arrangement_flow == 0 and bar in [3, 15]) or (arrangement_flow == 1 and bar in [7, 15])

            def should_skip_drum_beat(beat_time):
                local_beat = beat_time - start_beat
                if pre_drop_break and is_pre_drop_bar():
                    if local_beat >= 2.0: # Cut drums last 2 beats
                        return True
                return False

            def safe_add(category: str, beat_time: float, metadata: Dict[str, Any] = None):
                # Only add if it's an active FX/Vox, or if it's not FX/Vox
                if category.startswith("fx_") and category not in active_fx:
                    return
                if category.startswith("vox_") and category not in active_vox:
                    return

                metadata = metadata or {}

                # Apply Groove Humanization
                if category in ["hihats", "open_hats"]:
                    vel, swing = get_hihat_vel_and_swing(beat_time)
                    if "velocity" not in metadata:
                        metadata["velocity"] = vel
                    beat_time += swing
                elif category in ["snares", "claps"]:
                    if "velocity" not in metadata:
                        metadata["velocity"] = get_snare_vel()

                # Pre-Drop Silence / Respiration: Cut all melodic instruments and bass on the final beat (beat 3 to 4) before the drop
                local_beat = beat_time - start_beat
                if is_pre_drop_bar() and local_beat >= 3.0:
                    if category.startswith("synth_") or category == "808s" or category == "kicks":
                        return

                # Regular drum skipping
                if category.startswith("synth_") or category.startswith("fx") or category.startswith("vox"):
                    add_event(category, beat_time, metadata)
                elif not should_skip_drum_beat(beat_time):
                    add_event(category, beat_time, metadata)

            # Determine 808 pitch for this bar based on algorithm
            bar_in_progression = bar % 8

            if bass_algorithm == "root_pedal":
                # Stays on root mostly, occasional 5th (7 semitones)
                current_shift = 0 if rng.random() < 0.8 else 7
            elif bass_algorithm == "octave_bounce":
                # Bounces between root and octave
                current_shift = 0 if bar_in_progression % 2 == 0 else 12
            else: # "walking"
                # Wanders between root, minor 3rd (3), 5th (7), minor 7th (10)
                current_shift = rng.choice([0, 3, 7, 10])

            raw_pitch = base_808_shift + current_shift
            current_pitch = constrain_to_minor_scale(raw_pitch)

            # Turnaround glide on bars 4 (index 3) and 8 (index 7)
            glide = (bar_in_progression == 3 or bar_in_progression == 7)

            # Turnaround/accent markers
            is_turnaround = bar % 4 == 3

            # Intro / Bridge Ambiance
            if bar == 0 or bar == 12:
                safe_add("fx_texture", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "attenuate": -14.0})

            # Dynamic Halftime Pitch Modifier
            pitch_modifier = -12 if half_time_section and (is_outro or is_verse) else 0

            # Bars 1-4 (Intro): melodies, snares/claps on beat 3 on bars 3-4, fx_oneshot, and dry Vox on bar 4
            if is_intro:
                if bar == 0 or (arrangement_flow == 1 and bar == 4): # first bar of intro block
                    intro_metadata = {"halftime": True, "duration": 4 * self.bar_duration_sec}
                    if rng.random() < 0.5:
                        intro_metadata["filter_sweep_intro"] = True
                    else:
                        intro_metadata["filter_sweep"] = True # Static muffled fallback

                    safe_add("fx_oneshot", start_beat) # Impact downbeat bar 1

                    # Enforce minimum foundational density in intro
                    if intro_synth and "loop" in intro_synth:
                        safe_add(intro_synth, start_beat, metadata=intro_metadata)
                    else:
                        # Fallback: if there's no loop synth selected, force the first available loop synth
                        # or at least a foundational atmospheric layer so the intro isn't empty/dead air.
                        fallback_loop = next((s for s in all_synths if "loop" in s), None)
                        if fallback_loop:
                            safe_add(fallback_loop, start_beat, metadata=intro_metadata)
                        else:
                            safe_add("fx_texture", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "attenuate": -10.0})

                # Short melodies (syncopated arps/hits)
                if intro_synth and "oneshot" in intro_synth:
                    # Rhythmic Trap Pattern: beats 0, 1.5, 2.5, 3.75
                    arp_beats = [0, 1.5, 2.5, 3.75]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals)
                        # Optionally drop octave down for some hits
                        if rng.random() < 0.2:
                            pitch -= 12
                        safe_add(intro_synth, start_beat + ab, metadata={"pitch_shift": int(pitch)})

                if bar >= 2: # Bars 3-4 (index 2-3)
                    for layer in active_snare_layers:
                        safe_add(layer, start_beat + 2) # Beat 3
                if bar == 3: # Bar 4
                    # Accelerating snare fill on the last bar of the intro (beats 2.0 to 4.0)
                    for layer in active_snare_layers:
                        # 8th notes (2.0, 2.5)
                        safe_add(layer, start_beat + 2.0, metadata={"velocity": 0.6})
                        safe_add(layer, start_beat + 2.5, metadata={"velocity": 0.7})
                        # 16th notes (3.0, 3.25, 3.5, 3.75)
                        safe_add(layer, start_beat + 3.0, metadata={"velocity": 0.8})
                        safe_add(layer, start_beat + 3.25, metadata={"velocity": 0.85})
                        safe_add(layer, start_beat + 3.5, metadata={"velocity": 0.95})
                        safe_add(layer, start_beat + 3.75, metadata={"velocity": 1.0})

                    if rng.random() < 0.33:
                        safe_add("fx_oneshot", start_beat + 3, metadata={"tape_stop": True}) # Pre-drop transition bar 4 beat 4
                    else:
                        safe_add("fx_oneshot", start_beat + 3)
                    safe_add("vox_oneshot", start_beat + 3.5, metadata={"pan": 0.5}) # Final half-beat panned right

            # Bars 5-12 (Drop 1)
            elif is_drop1:
                if (arrangement_flow == 0 and bar == 4) or (arrangement_flow == 1 and bar == 4):
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

                # 808s with ducking metadata matching kicks and pitch
                safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})
                if kick_active:
                    safe_add("kicks", start_beat) # Kick on beat 1 locking to 808

                # Vary syncopation based on global template
                kick_hits = []
                if kick_template == 0:
                    kick_hits = [1.5]
                elif kick_template == 1:
                    kick_hits = [2.5]
                elif kick_template == 2:
                    kick_hits = [2.75, 3.5]

                for k_pos in kick_hits:
                    safe_add("808s", start_beat + k_pos, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})
                    if kick_active:
                        safe_add("kicks", start_beat + k_pos) # Lock kick to 808

                for layer in active_snare_layers:
                    safe_add(layer, start_beat + 2) # Snare/Clap on beat 3

                # Hi-hat Subdivision
                if hihat_template == 0:
                    # Straight 8ths
                    for i in range(8):
                        safe_add("hihats", start_beat + i * 0.5, metadata={"pan": main_hihat_pan})
                elif hihat_template == 1:
                    # Rolling Triplets (approximation)
                    for i in range(12):
                        safe_add("hihats", start_beat + i * 0.33, metadata={"pan": main_hihat_pan})
                elif hihat_template == 2:
                    # Bouncy Syncopated
                    for i in [0, 0.5, 0.75, 1.5, 2, 2.25, 3, 3.5]:
                        safe_add("hihats", start_beat + i, metadata={"pan": main_hihat_pan})

                # Rolls on even bars
                if bar % 2 == 1: # "Even" in 1-based indexing, odd in 0-based indexing
                    roll_start = rng.choice([2.0, 3.0, 3.25])
                    # 1/32 rolls with velocity ramp and alternating panning
                    safe_add("hihats", start_beat + roll_start, metadata={"velocity": 0.5, "pan": -0.8})
                    safe_add("hihats", start_beat + roll_start + 0.125, metadata={"velocity": 0.7, "pan": 0.8})
                    safe_add("hihats", start_beat + roll_start + 0.25, metadata={"velocity": 0.9, "pan": -0.8})
                    safe_add("hihats", start_beat + roll_start + 0.375, metadata={"velocity": 1.0, "pan": 0.8})

                if open_hat_active:
                    safe_add("open_hats", start_beat + 1.5, metadata={"pan": main_hihat_pan})
                    safe_add("open_hats", start_beat + 3.5, metadata={"pan": main_hihat_pan})

                # Syncopated ghost hits and vocals
                if is_turnaround:
                    safe_add("vox_oneshot", start_beat + 2.5, metadata={"pan": -0.5, "pitch_shift": tonal_oneshots_shift.get("vox_oneshot", 0)})
                    safe_add("perc_oneshot", start_beat + 3.75, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

            # Bars 13-16 (Breakdown or Verse)
            elif is_breakdown or is_verse:
                if (arrangement_flow == 0 and bar == 12) or (arrangement_flow == 1 and bar == 8) or (arrangement_flow == 1 and bar == 12):
                    verse_meta = {"duration": 4 * self.bar_duration_sec, "filter_sweep": True}
                    if is_verse and half_time_section:
                        verse_meta["halftime"] = True
                        verse_meta["pitch_shift"] = pitch_modifier

                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata=verse_meta)
                    safe_add("vox_loop", start_beat, metadata={"duration": 4 * self.bar_duration_sec, "lpf": 5000, "attenuate": -14.0})

                for s_one in synth_oneshots:
                    # Sparse arpeggio on Breakdown
                    arp_beats = [0, 2]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals) + pitch_modifier
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch), "lpf": 2000})

                if bar == 15 or bar == 11: # End of Breakdown/Verse block
                    safe_add("fx_oneshot", start_beat + 3) # Pre-drop transition

                if is_verse:
                    safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})
                    if kick_active:
                        safe_add("kicks", start_beat)
                        safe_add("kicks", start_beat + 2.5)

                # Light percussion
                for layer in active_snare_layers:
                    safe_add(layer, start_beat + 2)
                safe_add("perc_oneshot", start_beat + 1.75, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

                # Sparse hihats
                for i in range(4):
                    safe_add("hihats", start_beat + i * 1.0, metadata={"pan": main_hihat_pan})

            # Bars 17-20 (Second Hard Drop)
            elif is_drop2:
                if (arrangement_flow == 0 and bar == 16) or (arrangement_flow == 1 and bar == 16):
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

                # 808s and Kick variation locking
                safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})
                safe_add("808s", start_beat + 1.5, metadata={"ducking": True, "pitch_shift": current_pitch, "glide": glide})
                if kick_active:
                    safe_add("kicks", start_beat)
                    safe_add("kicks", start_beat + 1.5)
                    safe_add("kicks", start_beat + 3.5)

                for layer in active_snare_layers:
                    safe_add(layer, start_beat + 2)

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
            elif is_outro:
                if bar == 20:
                    outro_meta = {"duration": 4 * self.bar_duration_sec}
                    if half_time_section:
                        outro_meta["halftime"] = True
                        outro_meta["pitch_shift"] = pitch_modifier

                    for s_loop in synth_loops:
                        safe_add(s_loop, start_beat, metadata=outro_meta)

                for s_one in synth_oneshots:
                    arp_beats = [0, 2]
                    for ab in arp_beats:
                        pitch = rng.choice(pentatonic_intervals) + pitch_modifier
                        safe_add(s_one, start_beat + ab, metadata={"pitch_shift": int(pitch), "attenuate": -6.0})

                # Light percs on offbeat
                safe_add("perc_oneshot", start_beat + 1.5, metadata={"pan": opposite_perc_pan, "pitch_shift": tonal_oneshots_shift.get("perc_oneshot", 0)})

                if bar < 22: # Cut 808 and kicks at bar 23 (index 22)
                    safe_add("808s", start_beat, metadata={"ducking": True, "pitch_shift": current_pitch})
                    if kick_active:
                        safe_add("kicks", start_beat)

        return events
