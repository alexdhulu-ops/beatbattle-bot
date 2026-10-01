with open("beatbattle/arranger.py", "r") as f:
    text = f.read()

target = """        # FX / Vocals Layering Logic
        all_fx = [k for k in library.library.keys() if k.startswith("fx_")]
        all_vox = [k for k in library.library.keys() if k.startswith("vox_")]"""

new_text = """        # FX / Vocals Layering Logic
        all_fx = [k for k in library.library.keys() if k.startswith("fx_")]
        all_vox = [k for k in library.library.keys() if k.startswith("vox_") or k.startswith("perc_oneshot")]"""
text = text.replace(target, new_text)

with open("beatbattle/arranger.py", "w") as f:
    f.write(text)
