with open("beatbattle/arranger.py", "r") as f:
    text = f.read()

# Instead of hardcoding "perc_oneshot" or "fx_oneshot", let's replace them with a dynamic pick from active_vox / active_fx.
# Actually, the simplest way is to intercept it inside safe_add itself!
# If safe_add is called with "fx_oneshot", but "fx_oneshot_2" is the active one, we remap it!

remap_inject = """            def safe_add(category: str, beat_time: float, metadata: Dict[str, Any] = None):
                nonlocal last_vox_position

                # Remap generic hardcoded calls to the active ones in the pool if applicable
                if category == "fx_oneshot" and active_fx:
                    # Pick an active fx oneshot (prioritize unplayed via active_fx which already did priority sorting)
                    fx_oneshots = [f for f in active_fx if "oneshot" in f]
                    if fx_oneshots: category = fx_oneshots[0]
                elif category == "perc_oneshot" and active_vox:
                    perc_oneshots = [p for p in active_vox if "perc_oneshot" in p]
                    if perc_oneshots: category = perc_oneshots[0]

                # Only add if it's an active FX/Vox, or if it's not FX/Vox"""

target = """            def safe_add(category: str, beat_time: float, metadata: Dict[str, Any] = None):
                nonlocal last_vox_position

                # Only add if it's an active FX/Vox, or if it's not FX/Vox"""

text = text.replace(target, remap_inject)

with open("beatbattle/arranger.py", "w") as f:
    f.write(text)
