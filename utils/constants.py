"""
Central place for app-wide constants and lightweight helpers.
Keep this module dependency-free to avoid circular imports.
"""

TEAMS = ["U18", "U21"]

ABSENCE_REASONS = ["injury", "illness", "excused", "other team", "AWOL"]

# --- Public color map for legends & consistent styling -----------------------
SESSION_TYPE_STYLES: Dict[str, Dict[str, str]] = {
    "T1": {"color": "#2563eb", "label": "T1 - Low Intensity"},   # blue
    "T2": {"color": "#10b981", "label": "T2 - Aerobic/Tech"},    # green
    "T3": {"color": "#f59e0b", "label": "T3 - Mixed/Load"},      # amber
    "T4": {"color": "#ef4444", "label": "T4 - High Intensity"},  # red
    "M":  {"color": "#7c3aed", "label": "Match"},                # purple
}