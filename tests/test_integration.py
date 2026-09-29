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

    file_names = {
        "808_sub_bass.mp3": 1.0,
        "hard_kick_01.mp3": 1.0,
        "snare_clap_01.mp3": 1.0,
        "closed_hihat_01.mp3": 1.0,
        "openhat_01.mp3": 1.0,
        "perc_wood_01.mp3": 1.0,      # perc_oneshot
        "perc_metal_loop.mp3": 2.0,   # perc_loop
        "synth_melody_loop.mp3": 2.0,
        "riser_fx_impact.mp3": 1.0,   # fx_oneshot
        "ambient_fx_texture.mp3": 2.0,# fx_texture
        "vocal_chant_vox.mp3": 1.0,   # vox_oneshot
        "vocal_hook_loop.mp3": 2.0    # vox_loop
    }

    sr = 44100
    for fname, duration in file_names.items():
        mp3_path = root / fname

        # Generate random noise
        samples = int(sr * duration)
        data = np.random.uniform(-0.1, 0.1, samples).astype(np.float32)
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
