import re

with open("beatbattle/renderer.py", "r") as f:
    content = f.read()

# Requirement 3 renderer support:
# Implement LPF in the renderer if metadata contains "lpf"
# Currently renderer checks "if category.startswith("synth_"): b_hp, a_hp = ..."
# We will inject an LPF filter pass.

lpf_inject_target = """            # Per-Track Corrective EQ
            nyq = 0.5 * sr
            if category.startswith("synth_"):
                b_hp, a_hp = scipy.signal.butter(2, 35.0 / nyq, btype='high', analog=False)
                audio_data = self._apply_biquad(audio_data, b_hp, a_hp)"""

lpf_inject_new = """            # Per-Track Corrective EQ
            nyq = 0.5 * sr
            if category.startswith("synth_"):
                b_hp, a_hp = scipy.signal.butter(2, 35.0 / nyq, btype='high', analog=False)
                audio_data = self._apply_biquad(audio_data, b_hp, a_hp)

            # Requirement 3: Dynamic Low-Pass Filtering
            if "lpf" in metadata:
                cutoff = metadata["lpf"]
                b_lpf, a_lpf = scipy.signal.butter(2, cutoff / nyq, btype='low', analog=False)
                audio_data = self._apply_biquad(audio_data, b_lpf, a_lpf)"""

content = content.replace(lpf_inject_target, lpf_inject_new)

with open("beatbattle/renderer.py", "w") as f:
    f.write(content)
