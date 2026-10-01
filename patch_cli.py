with open("beatbattle/cli.py", "r") as f:
    text = f.read()

target = """    console.print(f"Loading samples from {samples_dir}...")
    library = SampleLibrary(str(samples_dir))

    arranger = TrapArranger()
    renderer = AudioRenderer()

    for i in range(batch):"""

new_text = """    console.print(f"Loading samples from {samples_dir}...")
    library = SampleLibrary(str(samples_dir))

    arranger = TrapArranger()
    renderer = AudioRenderer()

    # Track all kit samples to guarantee 100% usage across the batch
    unplayed_samples = set(library.library.keys())

    for i in range(batch):"""
text = text.replace(target, new_text)

target2 = """        timeline = arranger.create_timeline(library, rng=current_rng)"""
new_text2 = """        timeline = arranger.create_timeline(library, rng=current_rng, unplayed_samples=unplayed_samples)"""
text = text.replace(target2, new_text2)

with open("beatbattle/cli.py", "w") as f:
    f.write(text)
