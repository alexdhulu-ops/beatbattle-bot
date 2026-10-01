with open("beatbattle/arranger.py", "r") as f:
    text = f.read()

import re

# Update signature
target_def = "def create_timeline(self, library: Any, rng: np.random.Generator | None = None) -> List[Dict[str, Any]]:"
new_def = "def create_timeline(self, library: Any, rng: np.random.Generator | None = None, unplayed_samples: set = None) -> List[Dict[str, Any]]:"
text = text.replace(target_def, new_def)

# Add logic for unplayed tracking near the beginning
unplayed_init_target = """        if rng is None:
            rng = np.random.default_rng()
        events = []"""
unplayed_init_new = """        if rng is None:
            rng = np.random.default_rng()
        if unplayed_samples is None:
            unplayed_samples = set()
        events = []"""
text = text.replace(unplayed_init_target, unplayed_init_new)

# Prioritize unplayed synths
synth_logic_target = """        # Synth Layering Logic (25% Solo, 50% Duo, 25% Trio)
        synth_count = rng.choice([1, 2, 3], p=[0.25, 0.50, 0.25])
        active_synths = rng.choice(all_synths, size=min(synth_count, len(all_synths)), replace=False).tolist() if all_synths else []"""

synth_logic_new = """        # Synth Layering Logic (25% Solo, 50% Duo, 25% Trio)
        synth_count = rng.choice([1, 2, 3], p=[0.25, 0.50, 0.25])

        # Priority Injection for Synths
        unplayed_synths = [s for s in all_synths if s in unplayed_samples]
        active_synths = []
        if unplayed_synths:
            priority_count = min(len(unplayed_synths), synth_count)
            active_synths = rng.choice(unplayed_synths, size=priority_count, replace=False).tolist()

        remaining_count = synth_count - len(active_synths)
        if remaining_count > 0:
            remaining_pool = [s for s in all_synths if s not in active_synths]
            if remaining_pool:
                active_synths += rng.choice(remaining_pool, size=min(remaining_count, len(remaining_pool)), replace=False).tolist()"""

text = text.replace(synth_logic_target, synth_logic_new)

# Prioritize unplayed FX / Vox
fx_logic_target = """        # FX / Vocals Layering Logic
        all_fx = [k for k in library.library.keys() if k.startswith("fx_")]
        all_vox = [k for k in library.library.keys() if k.startswith("vox_")]

        active_fx = rng.choice(all_fx, size=rng.integers(0, len(all_fx) + 1), replace=False).tolist() if all_fx else []
        active_vox = rng.choice(all_vox, size=rng.integers(0, len(all_vox) + 1), replace=False).tolist() if all_vox else []"""

fx_logic_new = """        # FX / Vocals Layering Logic
        all_fx = [k for k in library.library.keys() if k.startswith("fx_")]
        all_vox = [k for k in library.library.keys() if k.startswith("vox_")]

        # Priority Injection for FX/Vox
        unplayed_fx = [f for f in all_fx if f in unplayed_samples]
        unplayed_vox = [v for v in all_vox if v in unplayed_samples]

        active_fx = []
        target_fx = rng.integers(1, len(all_fx) + 1) if unplayed_fx else rng.integers(0, len(all_fx) + 1)
        if unplayed_fx:
            active_fx = unplayed_fx
        else:
            active_fx = rng.choice(all_fx, size=target_fx, replace=False).tolist() if all_fx else []

        active_vox = []
        target_vox = rng.integers(1, len(all_vox) + 1) if unplayed_vox else rng.integers(0, len(all_vox) + 1)
        if unplayed_vox:
            active_vox = unplayed_vox
        else:
            active_vox = rng.choice(all_vox, size=target_vox, replace=False).tolist() if all_vox else []"""

text = text.replace(fx_logic_target, fx_logic_new)

# Pop from unplayed_samples on add_event
add_event_target = """            sample_path = library.get_sample(category)
            if sample_path:
                time_sec = beat_time * self.beat_duration_sec
                event = {"sample": sample_path, "time": time_sec, "category": category}
                if metadata:
                    event["metadata"] = metadata
                events.append(event)"""
add_event_new = """            sample_path = library.get_sample(category)
            if sample_path:
                if category in unplayed_samples:
                    unplayed_samples.remove(category)
                time_sec = beat_time * self.beat_duration_sec
                event = {"sample": sample_path, "time": time_sec, "category": category}
                if metadata:
                    event["metadata"] = metadata
                events.append(event)"""
text = text.replace(add_event_target, add_event_new)


with open("beatbattle/arranger.py", "w") as f:
    f.write(text)
