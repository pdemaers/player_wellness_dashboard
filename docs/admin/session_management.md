# Session Management

Create and browse sessions (T1–T4 training, M = match) used by the dashboards and RPE mapping.

## New Session
Fields:

- **Date** – defaults to today.
- **Team** – U18 / U21.
- **Type** – T1–T4 or **M** (match).
- **Duration (min)** – 1–240.

When you click **Add Session**:

- The app calls `add_session()` in the database layer.
- The DB layer serializes the date, computes `weeknumber`, and generates a **stable `session_id`** (e.g., `YYYYMMDD` + team).
- On success the calendar refreshes automatically.

> **Good practice:** Create sessions in advance for the week. It simplifies post-session RPE entries and analysis.

## Calendar
- **Filter by Team** (All / U18 / U21).
- Color coding by session type (see **Legend** under the calendar).
- Click a **date** to see the selected day.
- Click an **event** to open raw details (ID, title, etc.).

## Policy
- `session_id` is generated automatically and is **not edited** here.
- If you need to correct a wrong session (wrong date or team), delete it in the DB and add a new one (keeps IDs coherent).

## Troubleshooting
- **Calendar empty:** check the team filter or confirm sessions exist for the selected period.
- **Failed to add session:** check duration/type values; verify DB connectivity (error message shown).
- **RPE not linking to session:** confirm `session_id` format aligns between Registration app and Dashboard DB layer.