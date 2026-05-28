"""Tests verifying conftest factory defaults match app-level conventions (Issue #107)."""


class TestGameFactoryDefaultStatus:
    """Verify game_factory() produces lowercase status matching the app convention."""

    def test_game_factory_default_status_is_lowercase_live(self, team_factory, game_factory):
        """Default status must be 'live', not 'LIVE' — service uses if g.status == 'live'."""
        team_factory("TOR", "Toronto Maple Leafs")
        team_factory("BOS", "Boston Bruins")
        game = game_factory("BOS", "TOR")
        assert game.status == "live"

    def test_game_factory_default_status_populates_live_block(
        self, client, boxscore_factory
    ):
        """A LIVE boxscore game must produce a non-null live block in the API response."""
        boxscore_factory("BOS", "TOR", game_state="LIVE")
        data = client.get("/api/games/today").get_json()
        game = data["games"][0]
        assert game["live"] is not None
