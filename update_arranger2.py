import re

with open("beatbattle/arranger.py", "r") as f:
    content = f.read()

# Requirement 2: Snare & Hi-Hat Fills / Rolls

# We will add logic directly inside the main loop `for bar in range(self.total_bars):`
# At the end of the loop, before `return events`, we can just inject our fill logic for each bar,
# or we can patch it inside the loop block.

# Let's find a good spot inside the loop. The loop has a lot of `if is_intro:`, `elif is_drop1:`, etc.
# We will just append our logic at the very end of the `for bar` block.

loop_end_target = """
            # Turnaround/accent markers
            is_turnaround = bar % 4 == 3"""

new_fills_logic = """
            # Turnaround/accent markers
            is_turnaround = bar % 4 == 3

            # --- Snare Fills ---
            # On the 4th bar of an 8-bar cycle (bars 3, 7, 11, 15, 19, 23 in 0-indexed),
            # introduce an automated snare fill at the end of the bar.
            if bar % 8 == 3 or bar % 8 == 7:
                # Unless it's muted by pre-drop cut (handled in safe_add, but here we can just add them and let safe_add filter if needed,
                # or we just avoid it if we know we are cutting. Actually we want a fill resolving into 16th notes).
                if not (pre_drop_break and is_pre_drop_bar()):
                    for layer in active_snare_layers:
                        # 8th notes resolving to 16th notes
                        safe_add(layer, start_beat + 2.5, metadata={"velocity": 0.7})
                        safe_add(layer, start_beat + 3.0, metadata={"velocity": 0.8})
                        safe_add(layer, start_beat + 3.5, metadata={"velocity": 0.9})
                        safe_add(layer, start_beat + 3.75, metadata={"velocity": 1.0})

            # --- Hi-hat Variations ---
            # Inject short rolls on beat 4 of alternating bars
            if bar % 2 == 0 and not is_pre_drop_bar():
                # 1/32 note descending velocity roll on beat 4
                roll_vels = [0.9, 0.7, 0.5, 0.3]
                for i, vel in enumerate(roll_vels):
                    safe_add("hihats", start_beat + 3.0 + i*0.125, metadata={"velocity": vel, "pan": main_hihat_pan})"""

content = content.replace(loop_end_target, new_fills_logic)

with open("beatbattle/arranger.py", "w") as f:
    f.write(content)
