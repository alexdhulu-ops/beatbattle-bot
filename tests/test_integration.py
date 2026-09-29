import os
import pytest
import soundfile as sf
import numpy as np

from beatbattle.classifier import SampleLibrary
from beatbattle.arranger import TrapArranger
from beatbattle.renderer import AudioRenderer
from beatbattle.mastering import MasteringChain

@pytest.fixture
def mock_samples_dir(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()

    folders = [
        "808s", "kicks", "claps", "snares", "hihats", "openhats",
        "percs_1", "percs_2", "synths_1", "synths_2", "synths_3",
        "fx_1", "fx_2", "Vox"
    ]

    sr = 44100
    for folder in folders:
        folder_path = root / folder
        folder_path.mkdir()
        mp3_path = folder_path / f"{folder}_01.mp3"

        # Generate 0.5s of random noise to ensure non-silence
        # We use a small amplitude to avoid extreme clipping before limiter
        data = np.random.uniform(-0.1, 0.1, sr // 2).astype(np.float32)
        sf.write(str(mp3_path), data, sr, format='MP3')

    return str(root)

def test_end_to_end_rendering(mock_samples_dir, tmp_path):
    # Initialize components
    library = SampleLibrary(mock_samples_dir)
    arranger = TrapArranger()
    renderer = AudioRenderer(sample_rate=44100)
    mastering = MasteringChain()

    # Generate timeline
    timeline = arranger.create_timeline(library, variation_seed=42)

    # Render audio
    raw_audio = renderer.render_timeline(timeline)

    # Process audio
    mastered_audio = mastering.process(raw_audio, 44100)

    # Save output
    output_path = tmp_path / "test_output.wav"
    sf.write(str(output_path), mastered_audio.T, 44100)

    # Assertions
    assert output_path.exists()

    # Read back
    data, sr = sf.read(str(output_path))

    # Check duration (41.0 to 43.5 seconds)
    duration = len(data) / sr
    assert 41.0 <= duration <= 43.5

    # Check non-silence (RMS > 0 or max > 0)
    assert np.max(np.abs(data)) > 0.0001
