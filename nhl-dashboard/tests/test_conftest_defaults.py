"""Tests verifying conftest factory defaults match app-level conventions (Issue #107)."""


class TestBoxscoreFactoryDefaults:
    """Verify boxscore_factory() produces correct status via the API response."""

    def test_live_boxscore_game_produces_non_null_live_block(
        self, client, boxscore_factory
    ):
        """A LIVE boxscore game must produce a non-null live block in the API response."""
        boxscore_factory("BOS", "TOR", game_state="LIVE")
        data = client.get("/api/games/today").get_json()
        game = data["games"][0]
        assert game["live"] is not None
