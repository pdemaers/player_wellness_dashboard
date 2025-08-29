# Data Model

## Collections

### `roster`
- `player_id`: str (e.g., "21539")
- `player_first_name`: str
- `player_last_name`: str
- `team`: "U18" | "U21"

### `player_wellness`
- `player_id`: str
- `date`: ISO date string
- `feeling`: int (1–5)
- `sleep_hours`: float
- `timestamp`: datetime (UTC)

### `player_rpe`
- `player_id`: str | int
- `session_id`: str (e.g., "20250805U21")
- `date`: ISO datetime string
- `rpe_score`: int (1–10)
- `training_minutes`: int
- `timestamp`: datetime (UTC)

### `sessions`
- `session_id`: str (unique)
- `team`: "U18" | "U21"
- `date`: datetime
- `session_type`: "T1"|"T2"|"T3"|"T4"|"M"
- `duration`: int
- `weeknumber`: int

## Indexing (recommended)
- `player_wellness`: `{timestamp:1}`, `{player_id:1, timestamp:1}`
- `player_rpe`: `{session_id:1}`, `{player_id:1}`, `{timestamp:1}`
- `sessions`: `{session_id:1}` (unique), `{team:1, weeknumber:1}`