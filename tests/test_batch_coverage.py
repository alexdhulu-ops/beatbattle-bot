import pytest
from beatbattle.classifier import SampleLibrary
from beatbattle.arranger import TrapArranger
import numpy as np

def test_batch_coverage(tmp_path):
    # Create mock kit mimicking the prompt:
    # 808s, claps, fx_1, fx_2, hihats, kicks, openhats, percs_1, percs_2, snares, synths_1, synths_2, synths_3, Vox
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()

    mock_files = [
        "808s.mp3", "claps.ogg", "fx_1.ogg", "fx_2.mp3", "hihats.ogg",
        "kicks.mp3", "openhats.ogg", "percs_1.mp3", "percs_2.ogg", "snares.ogg",
        "synths_1.mp3", "synths_2.ogg", "synths_3.mp3", "Vox.ogg"
    ]

    for f in mock_files:
        (samples_dir / f).touch()

    library = SampleLibrary(str(samples_dir))
    arranger = TrapArranger()

    all_roles = set(library.library.keys())
    unplayed = set(all_roles)

    # Run batch generation
    for i in range(10):
        rng = np.random.default_rng(i + 42)
        timeline = arranger.create_timeline(library, rng=rng, unplayed_samples=unplayed)
        # unplayed is mutated in-place by arranger

    # By the end of 10 tracks, every single sample must have been used at least once.
    assert len(unplayed) == 0, f"Unplayed samples remaining after batch: {unplayed}"
