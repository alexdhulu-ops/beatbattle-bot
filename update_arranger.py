import re

with open("beatbattle/arranger.py", "r") as f:
    content = f.read()

# 1. Sample Selection Probability (Vocal/FX Tags)
# In safe_add, we should inject the logic to skip vox_oneshot or fx_oneshot occasionally.
# Let's add state variables to the class or to the generate method.
# We will just patch the create_timeline method.

# We'll replace the beginning of create_timeline to initialize state variables
new_init = """
        # Track last played position of vox_oneshot to avoid repeating same position
        last_vox_position = -1.0
        # Determine 808 pitch for this bar based on algorithm
"""
content = content.replace("        # Determine 808 pitch for this bar based on algorithm", new_init)

# In safe_add, add the check for vox_oneshot and fx_oneshot probability
safe_add_orig = """            def safe_add(category: str, beat_time: float, metadata: Dict[str, Any] = None):
                # Only add if it's an active FX/Vox, or if it's not FX/Vox
                if category.startswith("fx_") and category not in active_fx:
                    return
                if category.startswith("vox_") and category not in active_vox:
                    return"""

safe_add_new = """            def safe_add(category: str, beat_time: float, metadata: Dict[str, Any] = None):
                nonlocal last_vox_position

                # Only add if it's an active FX/Vox, or if it's not FX/Vox
                if category.startswith("fx_") and category not in active_fx:
                    return
                if category.startswith("vox_") and category not in active_vox:
                    return

                # Requirement 1: Sample Selection Probability (De-duplicate Vocal/FX Tags)
                if category == "vox_oneshot" or category == "fx_oneshot":
                    # If this is specifically a pre-drop transition impact, we allow it to pass always (e.g. at beat 0 of bar 0, 16, etc.)
                    # But if it's a recurring tag, lower probability
                    is_impact = (beat_time % 16.0 == 0.0)
                    if not is_impact:
                        if rng.random() > 0.30:  # 30% chance to play
                            return

                        # If playing, make sure we don't play on the exact same bar position in consecutive 8-bar chunks or something.
                        # We'll just slightly randomize the placement within a 1-beat window if it's a vox tag.
                        local_pos = beat_time % self.beats_per_bar
                        if category == "vox_oneshot":
                            if local_pos == last_vox_position:
                                # try alternate trigger placement (e.g. shift by 1 beat or 0.5 beat)
                                beat_time += rng.choice([-0.5, 0.5, 1.0])
                                # ensure it doesn't bleed into next bar unexpectedly, though small shifts are fine

                            last_vox_position = (beat_time % self.beats_per_bar)"""

content = content.replace(safe_add_orig, safe_add_new)

with open("beatbattle/arranger.py", "w") as f:
    f.write(content)
