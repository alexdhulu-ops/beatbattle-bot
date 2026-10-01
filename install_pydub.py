# The user mentions "Ensure the audio decoding pipeline (e.g. soundfile or pydub) reads .ogg and .mp3 files properly into NumPy audio buffers."
# Actually, soundfile handles .mp3 properly out-of-the-box in modern versions since it ships with libsndfile 1.2+.
# We will use pydub as a fallback decoder in renderer and pitch just in case.
pass
