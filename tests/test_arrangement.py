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

    # Flat directory file names mapped to the keywords required
    file_names = [
        "808_sub_bass.mp3",
        "hard_kick_01.mp3",
        "snare_clap_01.mp3",
        "closed_hihat_01.mp3",
        "openhat_01.mp3",
        "perc_wood_01.mp3",
        "perc_metal_01.mp3",
        "synth_melody_loop.mp3",
        "riser_fx_impact.mp3",
        "vocal_chant_vox.mp3"
    ]

    # Create empty 1-second mp3 files
    for fname in file_names:
        mp3_path = root / fname

        # generate 1 second of silence
        data = np.zeros(44100)
        sf.write(mp3_path, data, 44100, format='MP3')

    return str(root)

def test_sample_library_loads_all(mock_library_dir):
    library = SampleLibrary(mock_library_dir)

    # Check that it mapped the expected roles
    expected_roles = [
        "808s", "kicks", "snares", "hihats", "open_hats",
        "percs_1", "percs_2", "melodies", "fx_1", "Vox"
    ]
    for role in expected_roles:
        assert role in library.library, f"Role {role} not mapped"
        assert library.get_sample(role).endswith(".mp3")

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

    # In Intro (bars 1-4), we add snares on beat 3 of bars 3-4 = 2 snares.
    # In Drop 1 (bars 5-12), 1 snare per bar = 8 snares.
    # In Drop 2 (bars 13-20), 1 snare per bar = 8 snares.
    # Total = 18
    assert len(snare_events) == 18

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
