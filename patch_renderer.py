with open("beatbattle/renderer.py", "r") as f:
    text = f.read()

target = """            # Load sample if not in cache
            if file_path not in sample_cache:
                data, sr = sf.read(file_path, always_2d=True)

                # Convert to stereo if mono
                if data.shape[1] == 1:
                    data = np.repeat(data, 2, axis=1)

                # Transpose to shape (channels, samples)
                data = data.T"""

replacement = """            # Load sample if not in cache
            if file_path not in sample_cache:
                from beatbattle.audio_utils import load_audio
                data, sr = load_audio(file_path, target_sr=self.sample_rate)"""

if target in text:
    text = text.replace(target, replacement)
    print("Patched renderer.py")
else:
    print("Target not found.")

with open("beatbattle/renderer.py", "w") as f:
    f.write(text)
