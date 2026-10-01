with open("beatbattle/arranger.py", "r") as f:
    text = f.read()

# We accidentally injected `last_vox_position = -1.0` into the middle of the `for bar in range` block but with 8-space indent,
# and it broke the 12-space indent of the next line `bar_in_progression = bar % 8`.

# Let's remove our faulty new_init injection and put it at the right place.
text = text.replace(
'''        # Track last played position of vox_oneshot to avoid repeating same position
        last_vox_position = -1.0
        # Determine 808 pitch for this bar based on algorithm''',
'''            # Determine 808 pitch for this bar based on algorithm'''
)

# And inject last_vox_position = -1.0 right before the `for bar in range` loop
loop_start = "        for bar in range(self.total_bars):"
new_loop_start = '''        last_vox_position = -1.0
        for bar in range(self.total_bars):'''
text = text.replace(loop_start, new_loop_start)

with open("beatbattle/arranger.py", "w") as f:
    f.write(text)
