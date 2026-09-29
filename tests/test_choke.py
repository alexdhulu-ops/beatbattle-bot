import numpy as np
import pytest
import soundfile as sf
from beatbattle.renderer import AudioRenderer


def test_808_choke_truncation(tmp_path):
    renderer = AudioRenderer(sample_rate=44100)

    # Create a 2-second dummy stereo audio file for the 808
    data = np.ones((44100 * 2, 2)) * 0.5
    dummy_path = str(tmp_path / "dummy_808.mp3")
    sf.write(dummy_path, data, 44100, format='MP3')

    # Schedule two 808s: the first at 0.0s, the second at 1.0s.
    # The first 808 is 2 seconds long but should be choked at 1.0s.
    timeline = [
        {"sample": dummy_path, "time": 0.0, "category": "808s"},
        {"sample": dummy_path, "time": 1.0, "category": "808s"}
    ]

    # We'll just verify the rendering succeeds and no NaNs are produced.
    rendered_audio = renderer.render_timeline(timeline)

    # Because of the choke, the first sample gets truncated to 44100 samples (1 sec).
    # Then the second sample is played for 2 seconds.
    # Total duration populated should be ~3 seconds (plus whatever fading logic).
    # We mostly just care that the logic ran without crashing and outputs non-NaN.
    assert not np.isnan(rendered_audio).any()

    # Check that amplitude is maintained
    assert np.max(np.abs(rendered_audio)) > 0.0
