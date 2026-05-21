"""Tests for implied probability and edge math — services/implied.py."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from services.implied import american_to_implied, devig_two_way, edge  # noqa: E402


def test_american_to_implied_positive_odds():
    """+120 should yield ~45.45 implied probability."""
    result = american_to_implied(120)
    assert abs(result - 45.45) < 0.01


def test_american_to_implied_negative_odds():
    """-140 should yield ~58.33 implied probability."""
    result = american_to_implied(-140)
    assert abs(result - 58.33) < 0.01


def test_devig_two_way_sums_to_100():
    """Devigged away + home probabilities must sum to exactly 100.0."""
    p_away, p_home = devig_two_way(45.45, 58.33)
    assert abs(p_away + p_home - 100.0) < 0.001


def test_edge_positive():
    """edge(fair=47.5, market=45.0) should return 2.5."""
    result = edge(47.5, 45.0)
    assert result == pytest.approx(2.5)
