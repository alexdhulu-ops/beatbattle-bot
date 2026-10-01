with open("beatbattle/arranger.py", "r") as f:
    text = f.read()

# The reviewer explicitly requested: "Implement the pre-drop cut purely as a grid-based mute:
# silence all active tracks (drums, bass, melody) on beat 4 of the last bar before the drop,
# without relying on any specific transition sample."
# So I should change the mute logic to just `return` unconditionally, silencing EVERYTHING including FX/Vox.

target = """                # Requirement 4: Pre-Drop Gap / Mute (Beat 4 Cut)
                # Hard-mute all instruments (drums, sub/808, melody) on beat 4 (local_beat >= 3.0) of the last bar before the drop
                # We optionally allow fx_risers or isolated vocals.
                if is_pre_drop_bar() and local_beat >= 3.0:
                    if not category.startswith("fx_") and not category.startswith("vox_"):
                        return"""

new_target = """                # Requirement 4: Pre-Drop Gap / Mute (Beat 4 Cut)
                # Hard-mute ALL active instruments on beat 4 (local_beat >= 3.0) of the last bar before the drop
                if is_pre_drop_bar() and local_beat >= 3.0:
                    return"""

text = text.replace(target, new_target)

with open("beatbattle/arranger.py", "w") as f:
    f.write(text)
