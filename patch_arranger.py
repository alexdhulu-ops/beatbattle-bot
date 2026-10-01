with open("beatbattle/arranger.py", "r") as f:
    text = f.read()

target = """def get_midi_note(file_path: str, fmin: float, fmax: float) -> float:
    try:
        data, sr = sf.read(file_path, frames=44100 * 2)"""

replacement = """def get_midi_note(file_path: str, fmin: float, fmax: float) -> float:
    try:
        from beatbattle.audio_utils import load_audio
        data, sr = load_audio(file_path)
        # load_audio returns shape (channels, samples). We only need mono and a short chunk
        data = data.mean(axis=0)[:44100 * 2]"""

if target in text:
    text = text.replace(target, replacement)
    print("Patched arranger.py")
else:
    print("Target not found in arranger.py")

with open("beatbattle/arranger.py", "w") as f:
    f.write(text)
