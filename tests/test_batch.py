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


from typer.testing import CliRunner
from beatbattle.cli import app

runner = CliRunner()

def generate_beat(sample_dir, output_file, seed, batch=1):
    runner.invoke(app, [
        "generate",
        "--samples-dir", sample_dir,
        "--output-file", str(output_file),
        "--seed", str(seed),
        "--batch", str(batch)
    ])

def test_batch_outputs_are_different(mock_samples_dir, tmp_path):
    out_prefix = tmp_path / "batch_out.wav"
    generate_beat(mock_samples_dir, out_prefix, seed=101, batch=4)

    out1 = tmp_path / "batch_out_1.wav"
    out2 = tmp_path / "batch_out_2.wav"
    out3 = tmp_path / "batch_out_3.wav"
    out4 = tmp_path / "batch_out_4.wav"

    assert out1.exists()
    assert out2.exists()
    assert out3.exists()
    assert out4.exists()

    data1, _ = sf.read(out1)
    data2, _ = sf.read(out2)
    assert not np.array_equal(data1, data2), "Outputs must not be identical across different seeds in batch!"
