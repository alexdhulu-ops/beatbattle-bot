import os
import pytest
from typer.testing import CliRunner
import soundfile as sf
import numpy as np

from beatbattle.cli import app

runner = CliRunner()

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

        # Generate 0.5s of random noise
        data = np.random.uniform(-0.1, 0.1, sr // 2).astype(np.float32)
        sf.write(str(mp3_path), data, sr, format='MP3')

    return str(root)

def test_generate_command(mock_samples_dir, tmp_path):
    output_wav = tmp_path / "output" / "song.wav"

    result = runner.invoke(app, [
        "generate",
        "--samples-dir", mock_samples_dir,
        "--output-file", str(output_wav),
        "--tempo", "140.0"
    ])

    assert result.exit_code == 0
    assert "Loading samples from directory..." in result.stdout
    assert "Generating 24-bar Trap timeline..." in result.stdout
    assert "Rendering audio and applying mastering..." in result.stdout
    assert "Success!" in result.stdout

    # Check if the output file is created
    assert output_wav.exists()

    # Read the output and ensure it is not empty/silent
    data, sr = sf.read(str(output_wav))

    assert len(data) > 0
    assert np.max(np.abs(data)) > 0.0001

    # Since tempo is 140 and max is 43.5s, length should be bounded properly
    duration = len(data) / sr
    assert 41.0 <= duration <= 43.5
