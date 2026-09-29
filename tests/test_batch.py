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

        # Generate stable, non-random dummy noise based on frequency so the only variations
        # come from the arrangement seed, not the actual audio sample changing
        samples = int(sr * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        freq = 440.0 + (hash(fname) % 400) # give different samples different pitches
        data = np.sin(2 * np.pi * freq * t).astype(np.float32) * 0.1
        sf.write(str(mp3_path), data, sr, format='MP3')

    return str(root)


def test_batch_seed_decoupling(mock_samples_dir):
    """
    Verifies that running the pipeline with two different seeds produces two distinct waveforms,
    ensuring that the randomization logic in the arranger actually generates variation.
    """
    library = SampleLibrary(mock_samples_dir)
    arranger = TrapArranger()
    renderer = AudioRenderer(sample_rate=44100)
    mastering = MasteringChain()

    # Generate beat 1 with seed 42
    timeline1 = arranger.create_timeline(library, variation_seed=42)
    raw_audio1 = renderer.render_timeline(timeline1)
    audio1 = mastering.process(raw_audio1, 44100)

    # Generate beat 2 with seed 999
    timeline2 = arranger.create_timeline(library, variation_seed=999)
    raw_audio2 = renderer.render_timeline(timeline2)
    audio2 = mastering.process(raw_audio2, 44100)

    # The two tracks should NOT be perfectly identical
    assert not np.allclose(audio1, audio2, atol=1e-5), "Generations with different seeds produced identical audio arrays"
