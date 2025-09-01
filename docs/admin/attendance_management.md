# Attendance Management

The **Attendance Management** page allows coaches to register player presence and absence for each training session or match in one simple workflow.

---

## Features

- **Team selection**  
  Choose between `U18` and `U21` via a segmented control.

- **Session selection**  

  - Sessions are shown by date only (`dd/mm/yyyy` format).  
  - Defaults to today’s session if available, otherwise the most recent.  
  - Shows today plus the last 5 sessions.

- **Presence registration**  

  - All players of the selected team are displayed as pills.  
  - Coaches select the players who were present.  
  - Player IDs are hidden; only names are shown.

- **Absence registration**  

  - Players not marked as present are automatically listed as absentees.  
  - Each absentee has a dropdown to assign a reason:  
  
    - `injury`  
    - `illness`  
    - `excused`  
    - `other team`  
    - `AWOL`

- **Save attendance**  
  - Presences and absentees are saved together in one step.  
  - Confirmation message shows the selected session date and team, e.g.:  
    > *Attendance saved for 01/09/2025 — U21.*

---

## Data Flow

- **Sessions** are retrieved from `MongoWrapper.get_recent_sessions(team=...)`.  
- **Rosters** are retrieved from `MongoWrapper.get_roster_players(team=...)`.  
- **Attendance** is written in one go via `MongoWrapper.upsert_attendance_full(...)`.

---

## Database Schema

Attendance data is stored in the `attendance` collection, one document per session:

```json
{
  "session_id": "20250901U21",
  "team": "U21",
  "present": [21234, 21301, 21315],
  "absent": [
    {"player_id": 21285, "reason": "injury"},
    {"player_id": 21299, "reason": "excused"}
  ],
  "created": "2025-09-01T08:30:00Z",
  "last_updated": "2025-09-01T08:35:00Z",
  "user": "Coach Name"
}