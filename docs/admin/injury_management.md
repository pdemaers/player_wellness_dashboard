# Injury Management

This page lets **physios** register injuries and track **treatment sessions** for any player.  

---

## TL;DR

- **Tab 1 – Register New Injury**: create a new injury record for the selected player.  
- **Tab 2 – Treatment Sessions**: pick an existing injury, view its details in a compact two-column layout, browse prior treatment sessions, and add a new treatment session comment.

---

## Data Model

**Collection:** `player_injuries` — one document **per injury**.  
Each treatment session is appended to that injury’s `treatment_sessions` array.

```json
{
  "_id": "...",
  "player_id": 21285,
  "team": "U21",
  "injury_date": "2025-09-14",
  "description": "Right hamstring strain during acceleration",
  "diagnostic": "Suspected grade 1 biceps femoris",
  "doctor_visit_date": "2025-09-15",
  "doctor_name": "Dr. Janssens",
  "imagery_type": "MRI",
  "projected_duration": "10 days",
  "comments": ["Initial pain 3/10, walking ok"],
  "treatment_sessions": [
    {
      "session_date": "2025-09-16",
      "comment": "Isometrics pain-free; added gentle cycling 10’",
      "created_by": "physio@club.tld",
      "created_at": "2025-09-16T07:40:21Z"
    }
  ],
  "created_by": "physio@club.tld",
  "created_at": "2025-09-14T09:15:00Z",
  "updated_by": "physio@club.tld",
  "updated_at": "2025-09-16T07:40:21Z"
}