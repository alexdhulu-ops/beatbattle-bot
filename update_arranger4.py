import re

with open("beatbattle/arranger.py", "r") as f:
    content = f.read()

# Requirement 4: Pre-Drop Gap / Mute (Beat 4 Cut)
# In safe_add, we already have some pre-drop silence logic, but it currently only cuts melodies and 808s on beat 3.0,
# and earlier we had `pre_drop_break` logic that conditionally cut drums.
# The user wants a HARD MUTE for ALL instruments on beat 4 of the last bar before the primary drop.
# Pre-drop bar is bar 3 (or bar 7 depending on flow).

mute_inject_target = """                # Pre-Drop Silence / Respiration: Cut all melodic instruments and bass on the final beat (beat 3 to 4) before the drop
                local_beat = beat_time - start_beat
                if is_pre_drop_bar() and local_beat >= 3.0:
                    if category.startswith("synth_") or category == "808s" or category == "kicks":
                        return"""

mute_inject_new = """                # Pre-Drop Silence / Respiration: Cut all melodic instruments and bass on the final beat (beat 3 to 4) before the drop
                local_beat = beat_time - start_beat

                # Requirement 4: Pre-Drop Gap / Mute (Beat 4 Cut)
                # Hard-mute all instruments (drums, sub/808, melody) on beat 4 (local_beat >= 3.0) of the last bar before the drop
                # We optionally allow fx_risers or isolated vocals.
                if is_pre_drop_bar() and local_beat >= 3.0:
                    if not category.startswith("fx_") and not category.startswith("vox_"):
                        return"""

content = content.replace(mute_inject_target, mute_inject_new)

# Also need to make sure loop synths that start at beat 0 of the pre-drop bar don't bleed into beat 4.
# We will do this by limiting their duration if they start at beat 0 of a pre-drop bar.
loop_dur_inject_target = """                # Requirement 3: Arrangement Breathing (Mute melodic loop on 8th bar turnaround)
                # Mute synth loops on beat 2 onwards of the 8th bar (i.e. bar 7, 15, 23)
                if category.startswith("synth_loop_") and (bar % 8 == 7):
                    # Cut loop early, so duration is only up to beat 2 (2 beats)
                    metadata["duration"] = 2.0 * self.beat_duration_sec"""

loop_dur_inject_new = """                # Requirement 3: Arrangement Breathing (Mute melodic loop on 8th bar turnaround)
                # Mute synth loops on beat 2 onwards of the 8th bar (i.e. bar 7, 15, 23)
                if category.startswith("synth_loop_") and (bar % 8 == 7):
                    # Cut loop early, so duration is only up to beat 2 (2 beats)
                    metadata["duration"] = 2.0 * self.beat_duration_sec

                # Requirement 4: Trim loop duration if it's the pre-drop bar to enforce silence on beat 4
                if category.startswith("synth_loop_") and is_pre_drop_bar():
                    # Duration is up to beat 3 (which is 3 beats long)
                    metadata["duration"] = min(metadata.get("duration", 999.0), 3.0 * self.beat_duration_sec)"""

content = content.replace(loop_dur_inject_target, loop_dur_inject_new)


with open("beatbattle/arranger.py", "w") as f:
    f.write(content)
