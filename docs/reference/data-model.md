# Data Model

## Collections

### `roster`
- `player_id`: str
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
- `session_id`: str
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

### `attendance`
- `session_id`: str
- `team`: str
- `present`: array of player_id (str or int)
- `absent`: array of objects `{ player_id: str|int, reason: str }`
- `created`: ISO datetime string
- `last_updated`: ISO datetime string
- `user`: str

### `match_minutes`
- `match_id`: str
- `team`: str
- `date`: ISO date string
- `player_minutes`: array of objects `{ player_id: str|int, minutes: int }`
- `opponent`: str
- `competition`: str

### `pdp_structure`
- `pdp_id`: str (unique)
- `name`: str
- `description`: str
- `criteria`: array of objects `{ criterion_id: str, name: str, description: str }`
- `created`: ISO datetime string

### `player_pdp`
- `player_id`: str|int
- `pdp_id`: str
- `criteria_scores`: array of objects `{ criterion_id: str, score: int, comment: str }`
- `review_date`: ISO datetime string
- `reviewer`: str

## Indexing (recommended)
- `player_wellness`: `{timestamp:1}`, `{player_id:1, timestamp:1}`
- `player_rpe`: `{session_id:1}`, `{player_id:1}`, `{timestamp:1}`
- `sessions`: `{session_id:1}` (unique), `{team:1, weeknumber:1}`
- `attendance`: `{session_id:1}`, `{team:1}`
- `match_minutes`: `{match_id:1}`, `{team:1, date:1}`
- `pdp_structure`: `{pdp_id:1}` (unique)
- `player_pdp`: