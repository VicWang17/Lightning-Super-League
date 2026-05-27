# Match Engine Coupling Design

## Goal

The main FastAPI system owns game-world state: seasons, fixtures, teams,
players, standings, finance, and persistence. The Go match engine owns match
truth: lineups, tactics, match clock, events, score, extra time, penalties,
match stats, and player match ratings.

All official matches in the main system must be simulated by the Go engine.
The legacy Python random simulator is only a fallback for local development
when explicitly enabled.

## Runtime Modes

The engine exposes one contract with three runtime modes.

| Mode | Intended use | Behavior |
|------|--------------|----------|
| `realtime` | Production live match | Engine advances with a visible tick interval and exposes live state/events. |
| `accelerated` | Staging and interactive tests | Same state machine as realtime, but tick interval is much shorter. |
| `instant` | Batch tests, season fast-forward, CI | Same simulation logic, no sleep between ticks, response returns final result immediately. |

The modes differ only in pacing and delivery, not in football logic.

## Clock Ownership

The main system virtual clock controls season-level time:

- season start/end
- match days
- cup progression
- promotion/relegation
- offseason processing

The Go engine controls match-level time:

- regular time
- extra time
- penalty shootout
- event generation
- stamina decay
- live snapshots

The main clock may not advance past a match day until all fixtures scheduled
for that day are finished and persisted.

## Match Day Flow

1. `MATCH_DAY` event becomes due in `EventQueue`.
2. FastAPI loads all scheduled fixtures for that season day.
3. For each fixture, FastAPI builds a frozen `SimulateRequest` snapshot:
   team names, eight starters, bench, attributes, skills, default or saved
   tactics, match type, seed, and winner requirement.
4. FastAPI calls the Go engine.
5. Go engine simulates using the selected runtime mode.
6. FastAPI persists the result:
   fixture score/status, winner metadata, match events, match stats, player
   season stats, cumulative player stats, league standings, and cup group
   standings.
7. When all fixtures are persisted, `MATCH_DAY` is completed and later events
   may run.

## Production Environment

Production should use:

- `MATCH_ENGINE_MODE=realtime`
- `MATCH_ENGINE_FALLBACK_RANDOM=false`
- moderate concurrency limits for match start requests
- result idempotency based on `fixture_id`
- service-to-service authentication with `X-Match-Engine-Key`

Production user experience should subscribe to the Go engine for live events.
FastAPI remains the authority for final persisted results.

## Test Environment

Test and local fast-forward should use:

- `MATCH_ENGINE_MODE=instant` for deterministic fast-forward and CI
- `MATCH_ENGINE_MODE=accelerated` for testing live event delivery
- deterministic seeds derived from fixture identifiers
- the same Go engine request and result schema as production

Tests should not use the Python random simulator unless specifically testing
fallback behavior.

## Extra Time and Penalties

Regular matches are 50 minutes: two 25-minute halves.

Winner-required fixtures behave as follows:

- league and group fixtures allow draws
- knockout fixtures require a winner
- if tied after regular time, play extra time
- extra time is two 10-minute periods
- there is no extra-time halftime rest; only a boundary event between periods
- if tied after extra time, run a penalty shootout

The engine result must include:

- `winner_team_id`
- `resolution`: `regular`, `extra_time`, `penalties`, or `draw`
- `penalty_score`, when applicable

Cup progression must use `winner_team_id` instead of guessing from score.

## Integration Contract

FastAPI calls:

`POST /api/v1/engine/matches/{match_id}/start`

Request body includes:

- `match_id`
- `home_team`
- `away_team`
- `home_advantage`
- `requires_winner`
- `mode`
- `tick_interval_ms`
- `seed`

Response body includes:

- `match_id`
- `status`
- `result`

The result is the Go engine `SimulateResult`.

## First Implementation Scope

The first coupling pass implements the authoritative simulation path:

- Go HTTP engine endpoint
- extra time and penalties in Go
- FastAPI HTTP client
- fixture snapshot conversion
- match day using Go results
- final result persistence

Live WebSocket fan-out can be added after the authoritative path is stable.
