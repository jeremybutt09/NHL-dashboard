"""Unit tests for implied probability and de-vig math (Issue #88)."""
import pytest
from services.implied import american_to_implied, devig_two_way, edge


class TestAmericanToImplied:
    def test_american_to_implied_negative_favorite(self):
        """american_to_implied(-110) → fraction ≈ 0.5238."""
        assert american_to_implied(-110) == pytest.approx(0.5238, abs=0.0001)

    def test_american_to_implied_positive_underdog(self):
        """american_to_implied(+110) → fraction ≈ 0.4762."""
        assert american_to_implied(110) == pytest.approx(0.4762, abs=0.0001)

    def test_american_to_implied_heavy_favorite(self):
        """american_to_implied(-500) → fraction ≈ 0.8333."""
        assert american_to_implied(-500) == pytest.approx(0.8333, abs=0.0001)

    def test_american_to_implied_zero_raises(self):
        """odds=0 is undefined; must raise ValueError."""
        with pytest.raises(ValueError):
            american_to_implied(0)


class TestDevigTwoWay:
    def test_devig_two_way_symmetric_returns_half_each(self):
        """Equal raw implied probs normalize to 0.5 each."""
        away, home = devig_two_way(0.5238, 0.5238)
        assert away == pytest.approx(0.5, abs=0.0001)
        assert home == pytest.approx(0.5, abs=0.0001)

    def test_devig_two_way_sums_to_one(self):
        """De-vigged probabilities must sum to 1.0."""
        away, home = devig_two_way(0.5238, 0.5238)
        assert away + home == pytest.approx(1.0, abs=0.0001)

    def test_devig_two_way_zero_input_returns_half_each(self):
        """Zero-sum input falls back to 0.5/0.5 sentinel."""
        away, home = devig_two_way(0.0, 0.0)
        assert away == pytest.approx(0.5, abs=0.0001)
        assert home == pytest.approx(0.5, abs=0.0001)


class TestEdge:
    def test_edge_positive(self):
        """fair > market → positive edge."""
        assert edge(0.55, 0.50) == pytest.approx(0.05, abs=0.0001)

    def test_edge_negative(self):
        """fair < market → negative edge."""
        assert edge(0.48, 0.52) == pytest.approx(-0.04, abs=0.0001)
