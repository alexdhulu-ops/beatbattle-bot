import re

with open("beatbattle/arranger.py", "r") as f:
    content = f.read()

# Requirement 3: Melodic Filtering & Arrangement Breathing
# During intro or bridge sections, apply a low-pass filter (cutoff around 500-800 Hz) to the melodic loop.
# Intro is bars 0-3. Bridge/Breakdown is bars 12-15 or 8-11 depending on flow.
# We will intercept the metadata assignment for `synth_` in these blocks.

# We'll just patch the `add_event` call inside `safe_add` to dynamically inject "lpf" metadata if we are in an intro/breakdown bar.

safe_add_inject_target = """                # Regular drum skipping
                if category.startswith("synth_") or category.startswith("fx") or category.startswith("vox"):
                    add_event(category, beat_time, metadata)
                elif not should_skip_drum_beat(beat_time):
                    add_event(category, beat_time, metadata)"""

safe_add_inject_new = """                # Regular drum skipping
                # Requirement 3: Melodic Filtering in Intro/Breakdown
                if category.startswith("synth_"):
                    if is_intro or is_breakdown:
                        metadata["lpf"] = 600.0  # Apply 600 Hz LPF during intro/breakdown to leave acoustic room

                # Requirement 3: Arrangement Breathing (Mute melodic loop on 8th bar turnaround)
                # Mute synth loops on beat 2 onwards of the 8th bar (i.e. bar 7, 15, 23)
                if category.startswith("synth_loop_") and (bar % 8 == 7):
                    # Cut loop early, so duration is only up to beat 2 (2 beats)
                    metadata["duration"] = 2.0 * self.beat_duration_sec

                if category.startswith("synth_") or category.startswith("fx") or category.startswith("vox"):
                    add_event(category, beat_time, metadata)
                elif not should_skip_drum_beat(beat_time):
                    add_event(category, beat_time, metadata)"""

content = content.replace(safe_add_inject_target, safe_add_inject_new)

with open("beatbattle/arranger.py", "w") as f:
    f.write(content)
