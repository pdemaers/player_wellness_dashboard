"""
Central place for app-wide constants and lightweight helpers.
Keep this module dependency-free to avoid circular imports.
"""

from enum import Enum
from typing import Dict, List, Mapping, Sequence

# --- Teams and attendance reasons -------------------------------------------

TEAMS: List[str] = ["U18", "U21"]

ABSENCE_REASONS: List[str] = [
    "injury", "illness", "excused", "school", "other team", "AWOL"
]

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

# --- Roles ------------------------------------------------------------------

class Role(str, Enum):
    ADMIN = "admin"
    COACH = "coach"
    PHYSIO = "physio"
    TEAM_MANAGER = "team_manager"  # reserved for future

# --- Pages ------------------------------------------------------------------

# Mapping: page name -> icon
PAGES: Dict[str, str] = {
    "Wellness Dashboard": ":material/monitor_heart:",
    "RPE Dashboard": ":material/stacked_line_chart:",
    "Session Dashboard": ":material/calendar_month:",
    "Create PDP": ":material/add_circle:",
    "PDP Library": ":material/library_books:",
    "Roster Management": ":material/badge:",
    "Attendance Management": ":material/groups:",
    "Injury Management": ":material/medical_information:",
    "Settings": ":material/settings:",
}

ROLE_ALLOWED_PAGES: Mapping[Role, Sequence[str]] = {
    Role.ADMIN: list(PAGES.keys()),
    Role.COACH: [
        "Wellness Dashboard", "RPE Dashboard", "Session Dashboard",
        "Create PDP", "PDP Library"
    ],
    Role.PHYSIO: [
        "Wellness Dashboard", "RPE Dashboard"
    ],
    Role.TEAM_MANAGER: [
        # define later when role becomes active
    ],
}