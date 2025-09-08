# Attendance Management

The **Attendance Management** page allows coaches to both register attendance for each session and review a season-long attendance overview.

---

## Features

### Team Selection
- Coaches choose between `U18` and `U21` via a segmented control.
- The team selector is displayed **outside the tabs**, so it applies to both registration and overview.

### Tabs
The page is divided into two tabs:

1. **Register Attendance**
   - Select session by date (shown in `dd/mm/yyyy`, defaults to today).
   - All players of the team are shown as **pills**.  
     Coaches select the players who were present.
   - Players not selected are automatically listed as **absentees**.
   - For each absentee, a dropdown allows assigning a reason:
     - 🩼 Injury  
     - 🏃 Individual  
     - 🏥 Physio Internal  
     - 🚑 Physio External  
     - 🎓 School  
     - ✈️ Holiday  
     - 🤒 Illness  
     - ⚠️ AWOL  
     - 🥇 Other team
   - Attendance is saved in one step. Both presence and absence are written to the database.

2. **Overview**
   - Displays a **player × session date matrix** with compact emojis.
   - **Rows** = players, **Columns** = session dates (shown as `dd/mm` with the full date available in a tooltip).
   - **Cells** = emoji for attendance status:
     - ✅ Present  
     - 🩼, 🏃, 🏥, 🎓, ✈️, 🤒, ⚠️, 🥇 (absence reasons as above)  
     - ❔ No entry
   - Table options:
     - Interactive mode (`st.data_editor`): scrollable/sortable, with approximate centering.
     - Static mode (`pd.Styler`): perfectly centered icons, non-interactive.
   - A legend is displayed below the table.

---

## Data Flow

- **Sessions** are loaded via `MongoWrapper.get_recent_sessions(team=...)`.  
- **Rosters** are loaded via `MongoWrapper.get_roster_players(team=...)`.  
- **Attendance** is written and updated via `MongoWrapper.upsert_attendance_full(...)`.  
- **Overview matrix** is generated with a helper that:
  - Fetches all sessions (deduplicated by date).
  - Builds a DataFrame with one row per player, one column per session date.
  - Fills cells with emojis depending on attendance status.

---

## Database Schema

Attendance is stored in the `attendance` collection, one document per session:

```json
{
  "session_id": "20250901U21",
  "team": "U21",
  "present": [21234, 21301, 21315],
  "absent": [
    {"player_id": 21285, "reason": "injury"},
    {"player_id": 21299, "reason": "school"}
  ],
  "created": "2025-09-01T08:30:00Z",
  "last_updated": "2025-09-01T08:35:00Z",
  "user": "Coach Name"
}