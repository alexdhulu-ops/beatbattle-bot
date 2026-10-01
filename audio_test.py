import numpy as np
import soundfile as sf
import os
import io

# We can create a dummy wav file and then just ensure soundfile logic works, but wait, soundfile handles ogg/mp3 directly.
try:
    data = np.zeros((100, 2))
    sf.write("test.ogg", data, 44100)
    d, sr = sf.read("test.ogg")
    print("OGG read OK")
    os.remove("test.ogg")
except Exception as e:
    print(f"OGG failed: {e}")

try:
    # write mp3 is not always supported but we can check if it reads
    pass
except Exception:
    pass
