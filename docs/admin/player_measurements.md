# Player Measurements

A monthly admin workflow to record height (cm) and weight (kg) for all players in a team on a given date.

## Purpose
- Standardize anthropometric data entry across squads.
- Keep one canonical document per `(team, date)` with complete per-player rows.
- Preserve audit information (`created`, `last_updated`, `user`).

## UI (Streamlit)
- **Team selector** (U18/U21)
- **Date selector** (default = today)
- **Editable table** of players:
  - `player_id` (read-only)
  - `player_name` (read-only)
  - `height_cm` (integer, cm)
  - `weight_kg` (one decimal, kg)
  - `absent` (checkbox)
- **Save** button performs an UPSERT into `player_measurements`.

> When `absent = true`, both `height_cm` and `weight_kg` are stored as `null`.
> The player list is populated via MongoWrapper.get_player_names(team, style="LAST_FIRST"), ensuring consistency across all views (injury, attendance, wellness, etc.).

## Data Model

**Collection**: `player_measurements`

One document per `(team, date)`:

```json
{
  "_id": ObjectId,
  "measurement_id": "U21-2025-09-30",
  "team": "U21",
  "date": "2025-09-30",
  "entries": [
    {
      "player_id": "21539",
      "player_name": "Smith, Alex",
      "height_cm": 182,
      "weight_kg": 76.4,
      "absent": false
    },
    {
      "player_id": "21577",
      "player_name": "Doe, Jamie",
      "height_cm": null,
      "weight_kg": null,
      "absent": true
    }
  ],
  "created": "2025-09-30T10:12:00Z",
  "last_updated": "2025-09-30T10:12:00Z",
  "user": "analyst@example.com"
}