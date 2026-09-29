import os
import pytest
import soundfile as sf
import numpy as np

from beatbattle.classifier import SampleLibrary
from beatbattle.arranger import TrapArranger
from beatbattle.renderer import AudioRenderer


@pytest.fixture
def mock_library_dir(tmp_path):
    root = tmp_path / "samples"
    root.mkdir()

    folders = [
        "808s", "kicks", "claps", "snares", "hihats", "openhats",
        "percs_1", "percs_2", "synths_1", "synths_2", "synths_3",
        "fx_1", "fx_2", "Vox"
    ]

    # Create empty 1-second wav files
    for folder in folders:
        folder_path = root / folder
        folder_path.mkdir()
        wav_path = folder_path / f"{folder}_01.wav"

        # generate 1 second of silence
        data = np.zeros(44100)
        sf.write(wav_path, data, 44100)

    return str(root)

def test_sample_library_loads_all(mock_library_dir):
    library = SampleLibrary(mock_library_dir)
    assert len(library.library) == 14
    for folder in SampleLibrary.REQUIRED_FOLDERS:
        assert folder in library.library
        assert library.get_sample(folder).endswith(".wav")

def test_trap_arranger_timeline(mock_library_dir):
    library = SampleLibrary(mock_library_dir)
    arranger = TrapArranger()
    timeline = arranger.create_timeline(library)

    assert len(timeline) > 0

    # Check total duration calculation
    assert 41.0 <= arranger.total_duration_seconds <= 43.5

    # Check snare placement on beat 3 during drop 1 (Bars 5-12, indexing 4-11)
    # Snares are on beat 3 (index 2 of the bar)
    # Start of Bar 5 (index 4) is beat 16. Snare should be at beat 18.
    snare_times_expected = []
    for bar in range(4, 12):
        beat_start = bar * 4
        snare_beat = beat_start + 2
        snare_time = snare_beat * arranger.beat_duration_sec
        snare_times_expected.append(snare_time)

    snare_events = [e for e in timeline if e["category"] == "snares"]

    # There should be snares in drop 1 and drop 2
    assert len(snare_events) == 16 # 8 for drop 1, 8 for drop 2

    snare_times_actual = [e["time"] for e in snare_events]
    for expected_time in snare_times_expected:
        # floating point comparison
        assert any(abs(actual - expected_time) < 1e-5 for actual in snare_times_actual)

def test_renderer_cut_off():
    # Ensure renderer enforces max 43.5 seconds length
    renderer = AudioRenderer(sample_rate=44100)
    audio = renderer.render_timeline([])

    # audio returned is capped at 43.5 seconds
    # Shape is (2, samples)
    assert audio.shape[1] == int(43.5 * 44100)
