"""Tests for implied probability and edge calculation (Issue #28)."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'backend'))

from services.implied import american_to_implied, devig_two_way, edge


def test_american_to_implied_positive_odds():
    assert abs(american_to_implied(120) - 45.45) < 0.01


def test_american_to_implied_negative_odds_140():
    assert abs(american_to_implied(-140) - 58.33) < 0.01


def test_american_to_implied_negative_odds_110():
    assert abs(american_to_implied(-110) - 52.38) < 0.01


def test_devig_two_way_equal_sides():
    away, home = devig_two_way(52.38, 52.38)
    assert abs(away - 50.0) < 0.01
    assert abs(home - 50.0) < 0.01


def test_devig_two_way_unequal_sides():
    away, home = devig_two_way(60.0, 45.0)
    assert abs(away - 57.14) < 0.01
    assert abs(home - 42.86) < 0.01


def test_edge_positive():
    assert edge(52.5, 45.0) == pytest.approx(7.5)


def test_edge_negative():
    assert edge(44.0, 47.5) == pytest.approx(-3.5)
