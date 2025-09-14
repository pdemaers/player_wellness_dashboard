"""
Central place for app-wide constants and lightweight helpers.
Keep this module dependency-free to avoid circular imports.
"""

from enum import Enum
from typing import Dict, List, Mapping, Sequence, Literal

# --- Teams and absence reasons -------------------------------------------

TEAMS: List[str] = ["U18", "U21"]

# Absence reasons with labels and Material icons
ABSENCE_REASONS: List[Dict[str, str]] = [
    {"id": "physio_internal", "label": "Physio Internal", "emoji": "🏥"},
    {"id": "injury", "label": "Injury", "emoji": "🩼"},
    {"id": "individual", "label": "Individual", "emoji": "🏃"},
    {"id": "other_team", "label": "Other team", "emoji": "🥇"},
    {"id": "holiday", "label": "Holiday", "emoji": "✈️"},
    {"id": "physio_external", "label": "Physio External", "emoji": "🚑"},
    {"id": "school", "label": "School", "emoji": "🎓"},
    {"id": "illness", "label": "Illness", "emoji": "🤒"},
    {"id": "awol", "label": "AWOL", "emoji": "⚠️"},
]

PRESENT_EMOJI = "✅"
UNKNOWN_EMOJI = "❔"

# Players to exempt from specific calculations (hard-coded ids)
EXEMPT: List[int] = [21511, 21772, 21007, 21984]

# --- Session type styling ---------------------------------------------------

SESSION_TYPE_STYLES: Dict[str, Dict[str, str]] = {
    "T1": {"color": "#2563eb", "label": "T1 - Low Intensity"},   # blue
    "T2": {"color": "#10b981", "label": "T2 - Aerobic/Tech"},    # green
    "T3": {"color": "#f59e0b", "label": "T3 - Mixed/Load"},      # amber
    "T4": {"color": "#ef4444", "label": "T4 - High Intensity"},  # red
    "M":  {"color": "#7c3aed", "label": "Match"},                # purple
}

# --- Registration start date to optimize data quality calculation -----------

REGISTRATION_START_DATE = "2025-08-04"

# --- Roles ------------------------------------------------------------------

class Role(str, Enum):
    ADMIN = "admin"
    COACH = "coach"
    PHYSIO = "physio"
    TEAM_MANAGER = "team_manager"  # reserved for future

# --- Pages ------------------------------------------------------------------

# Mapping: page name -> icon
PAGE_ICONS = {
    "Roster Management": "people-fill",
    "Session Management": "calendar2-event-fill",
    "PDP Structure": "file-earmark-text",
    "Wellness Dashboard": "heart-pulse",
    "RPE Dashboard": "bar-chart-line",
    "Session Dashboard": "stopwatch",
    "Create PDP": "file-earmark-plus",
    "PDP Library": "archive",
    "Attendance": "person-check",
    "Injury Management": "hospital",
    "RPE data quality": "database-fill-exclamation"
}

ROLE_ALLOWED_PAGES = {
    "admin": [
        "Roster Management", "Session Management", "PDP Structure",
        "Wellness Dashboard", "RPE Dashboard", "Session Dashboard",
        "Create PDP", "PDP Library", "Attendance", "Injury Management", 
        "RPE data quality"
    ],
    "coach": [
        "Wellness Dashboard", "RPE Dashboard", "Session Dashboard",
        "Create PDP", "PDP Library", "Attendance"
    ],
    "physio": [
        "Wellness Dashboard", "RPE Dashboard"
    ],
}

# Allowed styles for player name rendering
NameStyle = Literal[
    "LAST_FIRST",         # "DOE, John"
    "First Last",         # "John Doe"
    "LAST FirstInitial."  # "DOE J."
]

IMAGERY_TYPES = ["", "MRI", "Echo", "X-ray"]
INJURY_DURATION_UNITS = ["Day(s)", "Week(s)", "Month(s)"]