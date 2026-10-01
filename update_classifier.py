with open("beatbattle/classifier.py", "r") as f:
    text = f.read()

# Update valid extensions
text = text.replace('valid_extensions = (".mp3", ".wav", ".ogg")', 'valid_extensions = (".mp3", ".ogg")')

# Change get_duration to handle potential soundfile errors by falling back, though for .mp3 sf>=0.11 works if libsndfile is modern
# We'll just leave soundfile for now, but we should make sure pydub is used if necessary.
# Let's add pydub as a fallback just in case, but user said "e.g. soundfile or pydub".
# For now just update valid_extensions.
with open("beatbattle/classifier.py", "w") as f:
    f.write(text)
