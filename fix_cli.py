with open("beatbattle/cli.py", "r") as f:
    text = f.read()

# Add unplayed_samples definition back, because my previous patch didn't hit properly
text = text.replace("    rng = np.random.default_rng(seed)", "    unplayed_samples = set(library.library.keys())\n    rng = np.random.default_rng(seed)")

with open("beatbattle/cli.py", "w") as f:
    f.write(text)
