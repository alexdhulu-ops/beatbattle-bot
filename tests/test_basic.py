import pytest

import beatbattle
from beatbattle import classifier, arranger, renderer, mastering, cli


def test_imports():
    """
    Test that all modules can be imported.
    """
    assert classifier is not None
    assert arranger is not None
    assert renderer is not None
    assert mastering is not None
    assert cli is not None


def test_classifier_stub():
    c = classifier.SampleClassifier()
    assert c.analyze_sample("dummy.wav") is None


def test_arranger_stub():
    a = arranger.SongArranger()
    assert a.generate_pattern([], 4) is None


def test_renderer_stub():
    r = renderer.AudioRenderer()
    # It now returns an actual np.ndarray instead of None
    assert r.render_timeline([]) is not None


def test_mastering_stub():
    m = mastering.MasteringChain()
    # pass numpy array stub if we imported numpy in test, otherwise just testing instantiation
    assert m is not None


def test_cli_stub():
    assert cli.app is not None
