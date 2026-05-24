"""Unit tests for implied probability and de-vig math (Issue #88, scale fixed #106)."""
import pytest
from services.implied import american_to_implied, devig_two_way, edge


class TestAmericanToImplied:
    def test_american_to_implied_negative_favorite(self):
        """american_to_implied(-110) → percentage ≈ 52.38."""
        assert american_to_implied(-110) == pytest.approx(52.38, abs=0.01)

    def test_american_to_implied_positive_underdog(self):
        """american_to_implied(+110) → percentage ≈ 47.62."""
        assert american_to_implied(110) == pytest.approx(47.62, abs=0.01)

    def test_american_to_implied_heavy_favorite(self):
        """american_to_implied(-500) → percentage ≈ 83.33."""
        assert american_to_implied(-500) == pytest.approx(83.33, abs=0.01)

    def test_american_to_implied_zero_raises(self):
        """odds=0 is undefined; must raise ValueError."""
        with pytest.raises(ValueError):
            american_to_implied(0)


class TestDevigTwoWay:
    def test_devig_two_way_symmetric_returns_half_each(self):
        """Equal raw implied probs normalize to 50.0 each."""
        away, home = devig_two_way(52.38, 52.38)
        assert away == pytest.approx(50.0, abs=0.01)
        assert home == pytest.approx(50.0, abs=0.01)

    def test_devig_two_way_sums_to_one_hundred(self):
        """De-vigged probabilities must sum to 100.0."""
        away, home = devig_two_way(52.38, 52.38)
        assert away + home == pytest.approx(100.0, abs=0.01)

    def test_devig_two_way_zero_input_returns_half_each(self):
        """Zero-sum input falls back to 50.0/50.0 sentinel."""
        away, home = devig_two_way(0.0, 0.0)
        assert away == pytest.approx(50.0, abs=0.01)
        assert home == pytest.approx(50.0, abs=0.01)


class TestEdge:
    def test_edge_positive(self):
        """fair > market → positive edge."""
        assert edge(55.0, 50.0) == pytest.approx(5.0, abs=0.01)

    def test_edge_negative(self):
        """fair < market → negative edge."""
        assert edge(48.0, 52.0) == pytest.approx(-4.0, abs=0.01)
