with open("beatbattle/classifier.py", "r") as f:
    text = f.read()

target = """            elif "perc" in search_str:
                duration = self._get_duration(file_path)
                if duration < 1.2:
                    self._add_to_library("perc_oneshot", file_path)
                elif duration > 1.5:
                    self._add_to_library("perc_loop", file_path)"""

# We want to support multiple perc layers instead of just overwriting perc_oneshot if they are all oneshots.
# "Accents/FX: fx_1, fx_2, Vox, percs_1, percs_2 (distribute across the 10 tracks)"
# If we have percs_1, percs_2, we should just slot them. Let's make it more generic.
replacement = """            elif "perc" in search_str:
                duration = self._get_duration(file_path)
                if duration > 1.5:
                    if "perc_loop" not in self.library:
                        self._add_to_library("perc_loop", file_path)
                else:
                    if "perc_oneshot" not in self.library:
                        self._add_to_library("perc_oneshot", file_path)
                    else:
                        self._add_to_library("perc_oneshot_2", file_path)"""
text = text.replace(target, replacement)


target2 = """            elif "fx" in search_str or "riser" in search_str or "impact" in search_str:
                duration = self._get_duration(file_path)
                if duration < 1.2:
                    self._add_to_library("fx_oneshot", file_path)
                elif duration > 1.5:
                    self._add_to_library("fx_texture", file_path)"""

replacement2 = """            elif "fx" in search_str or "riser" in search_str or "impact" in search_str:
                duration = self._get_duration(file_path)
                if duration > 1.5:
                    self._add_to_library("fx_texture", file_path)
                else:
                    if "fx_oneshot" not in self.library:
                        self._add_to_library("fx_oneshot", file_path)
                    else:
                        self._add_to_library("fx_oneshot_2", file_path)"""
text = text.replace(target2, replacement2)


with open("beatbattle/classifier.py", "w") as f:
    f.write(text)
