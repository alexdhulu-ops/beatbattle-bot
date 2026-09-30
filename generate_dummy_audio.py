import numpy as np
import soundfile as sf
import os

sr = 44100
for f in ["808.wav", "kick.wav", "snare.wav", "hihat.wav", "synth1.wav"]:
    data = np.zeros(int(sr * 1.0))
    sf.write(os.path.join("test_samples", f), data, sr)
