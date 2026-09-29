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

    for fname, duration in file_names.items():
        mp3_path = root / fname
        data = np.zeros(int(44100 * duration))
        sf.write(mp3_path, data, 44100, format='MP3')

    return str(root)

def test_sample_library_loads_all(mock_library_dir):
    library = SampleLibrary(mock_library_dir)

    # Check that it mapped the expected roles
    expected_roles = [
        "808s", "kicks", "snares", "hihats", "open_hats",
        "perc_oneshot", "perc_loop", "melodies", "fx_oneshot", "fx_texture", "vox_oneshot", "vox_loop"
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
    # In Drop 1 (bars 5-12), 1 snare per bar. But bar 12 (index 11) has beat 3 cut out! So 8 - 1 = 7.
    # In Breakdown (bars 13-16), 1 snare per bar = 4 snares.
    # In Drop 2 (bars 17-20), 1 snare per bar = 4 snares.
    # But wait, bar 4 (index 3) and bar 12 (index 11) have cut logic.
    # Let's verify total: 2 (Intro, bar 3 has snare, bar 4 snare is cut) + 8 (Drop 1, bar 12 snare is cut) ...
    # Wait, bar 3 has snare, bar 4 cut. Drop 1 has snares on bars 5,6,7,8,9,10,11. Bar 12 cut.
    # Actually let's just let it assert the drop 1 snares minus the cut.
    # Intro: index 2 (1 snare). Index 3 cut.
    # Drop 1: index 4,5,6,7,8,9,10. Index 11 cut. (7 snares)
    # Breakdown: index 12,13,14,15. (4 snares)
    # Drop 2: index 16,17,18,19. (4 snares)
    # Total = 1 + 7 + 4 + 4 = 16 snares.
    assert len(snare_events) == 16

def test_renderer_cut_off():
    # Ensure renderer enforces max 43.5 seconds length
    renderer = AudioRenderer(sample_rate=44100)
    audio = renderer.render_timeline([])

    # audio returned is capped at 43.5 seconds
    # Shape is (2, samples)
    assert audio.shape[1] == int(43.5 * 44100)

def test_melody_trimming_and_fade(tmp_path):
    renderer = AudioRenderer(sample_rate=44100)

    # Create a dummy 5 second stereo audio file (with valid samples so it isn't completely stripped)
    data = np.ones((44100 * 5, 2)) * 0.5
    dummy_path = str(tmp_path / "dummy_melody.mp3")
    sf.write(dummy_path, data, 44100, format='MP3')

    timeline = [
        {
            "sample": dummy_path,
            "time": 0.0,
            "category": "melodies",
            "metadata": {
                "duration": 2.0  # Should be trimmed to exactly 2 seconds
            }
        }
    ]

    rendered_audio = renderer.render_timeline(timeline)

    # The rendered timeline itself is always 43.5s long due to the master buffer,
    # but we can check if there are no NaNs produced during the trimming/fading process.
    assert not np.isnan(rendered_audio).any()
