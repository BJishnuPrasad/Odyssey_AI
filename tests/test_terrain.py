import numpy as np
import pytest
from backend.analysis import terrain_indicators, classify


def test_slope_uses_metre_spacing():
    surface = np.tile(np.arange(41) * 25.0, (41, 1))
    slope, relative, _, _, valid = terrain_indicators(surface, 250)
    assert valid[20, 20]
    assert slope[20, 20] == pytest.approx(np.degrees(np.arctan(0.1)))
    assert relative[20, 20] == pytest.approx(0, abs=1e-6)


def test_nodata_and_neighbours_do_not_become_high_potential():
    surface = np.full((41, 41), 20.0)
    surface[20, 20] = np.nan
    _, _, flatness, lower, valid = terrain_indicators(surface, 250)
    assert not valid[19:22, 19:22].any()
    classified = classify(0.55 * flatness + 0.45 * lower, valid, np.ones(surface.shape, bool))
    assert (classified[19:22, 19:22] == 4).all()


def test_classification_boundaries_and_outside_mask():
    scores = np.array([[0.399, 0.4, 0.649, 0.65, 0.9, 0.9]])
    valid = np.array([[True, True, True, True, False, True]])
    inside = np.array([[True, True, True, True, True, False]])
    assert classify(scores, valid, inside).tolist() == [[1, 2, 2, 3, 4, 0]]


def test_no_neighbourhood_evidence_means_insufficient():
    surface = np.full((41, 41), np.nan)
    surface[19:22, 19:22] = 5
    *_, valid = terrain_indicators(surface, 250)
    assert not valid[20, 20]
