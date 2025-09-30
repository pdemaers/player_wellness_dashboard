# Injury Overview View

## Purpose
The Injury Overview page provides coaches, analysts, and medical staff with 
a consolidated overview of all player injuries for a selected team. It is a 
**read-only** view designed for monitoring player status, not for editing.

## Features
- Team selector (`U18`, `U21`, …) using the shared component.
- Injury entries displayed in expandable panels:
  - Player name
  - Description
  - Current status
- Shaded two-column detail block with:
  - Injury date
  - Diagnostic / doctor details
  - Imagery type
  - Projected duration
  - Comments
- Treatment sessions section with expandable session notes:
  - Session date
  - Author
  - Comment
  - Post-session status

## Data Sources
- **`injuries` collection** (via `InjuryRepo`)
- **`roster` collection** for player display names

## Notes
- This view is **read-only**. Injury creation and updates are handled elsewhere.
- Import-safe: no database writes or side effects on import.
- Displays user-friendly messages when no team, no players, or no injuries exist.

## Example Screenshot
*(Insert Streamlit screenshot here once the page is live in the app)*