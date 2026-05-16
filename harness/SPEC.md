# Project: NHL Betting & Scores Dashboard

## Product Vision
A simple Flask-based web application that provides a "Dashboard View" of daily NHL games, focusing on live scores and team-based betting odds.

## Core Features (MVP)
1. **Live Scoreboard**: Display all NHL games happening today with real-time score updates.
2. **Betting Odds**: Show Pre-game and Live In-game "Money Line" odds for each team.
3. **Team History**: For every game, show the result of the last 5 games for both teams and the season series results.

## NHL API Selection Guidance
- Use the official NHL API for all data.
- When a feature needs NHL data and the exact endpoint is not obvious, ask which endpoint should be used or suggest a short list of likely endpoints before implementation.
- Record the chosen endpoint or data source in the issue body so the implementation target is explicit.
- Keep odds display, partner branding, click-through behavior, and fallback handling as separate issues when possible.

## Technical Constraints
- **Language**: Python 3.x
- **Framework**: Flask
- **Architecture**: Modular "Skills" for data fetching.
- **Data Source**: NHL Public API (Scores/History)
