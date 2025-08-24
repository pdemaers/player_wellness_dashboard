"""
Reusable helpers to render a FullCalendar view via streamlit-calendar.

Dependencies:
- streamlit
- streamlit-calendar (pip install streamlit-calendar)
- pandas (for convenience when converting DataFrame -> events)

This module is UI-safe: it surfaces errors to Streamlit but won't crash your app.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date, datetime

import pandas as pd
import streamlit as st

# Try to import once at module load; show a friendly warning if missing.
try:
    from streamlit_calendar import calendar as _st_calendar
except Exception as _imp_err:  # pragma: no cover
    _st_calendar = None


# --- Public color map for legends & consistent styling -----------------------
SESSION_TYPE_STYLES: Dict[str, Dict[str, str]] = {
    "T1": {"color": "#2563eb", "label": "T1 - Low Intensity"},   # blue
    "T2": {"color": "#10b981", "label": "T2 - Aerobic/Tech"},    # green
    "T3": {"color": "#f59e0b", "label": "T3 - Mixed/Load"},      # amber
    "T4": {"color": "#ef4444", "label": "T4 - High Intensity"},  # red
    "M":  {"color": "#7c3aed", "label": "Match"},                # purple
}


def _to_iso_date(val: Any) -> Optional[str]:
    """Normalize a date-like value to 'YYYY-MM-DD'. Return None if invalid."""
    try:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.date().isoformat()
        if isinstance(val, date):
            return val.isoformat()
        # Strings / pandas Timestamps
        return pd.to_datetime(val).date().isoformat()
    except Exception:
        return None


def sessions_df_to_events(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert a sessions DataFrame into FullCalendar events.

    Expected columns (case-insensitive):
      - date
      - team
      - session_type  (T1/T2/T3/T4/M)
      - duration (minutes, optional)
      - session_id (optional)

    Returns:
        List of FullCalendar event dictionaries.
    """
    events: List[Dict[str, Any]] = []
    if df is None or df.empty:
        return events

    # Column name mapping (case-insensitive)
    cols = {c.lower(): c for c in df.columns}
    def col(name: str) -> Optional[str]:
        return cols.get(name)

    for _, row in df.iterrows():
        s_type = str(row.get(col("session_type"), "")).upper()
        d_iso = _to_iso_date(row.get(col("date")))
        duration = row.get(col("duration"))
        session_id = row.get(col("session_id"))

        if not d_iso:
            # Skip malformed dates; do not break the whole calendar.
            continue

        color = SESSION_TYPE_STYLES.get(s_type, {}).get("color", "#64748b")  # slate fallback
        title_bits = [s_type or "Session"]
        try:
            if pd.notnull(duration) and int(duration) > 0:
                title_bits.append(f"{int(duration)}m")
        except Exception:
            pass
        title = " · ".join(title_bits)

        events.append({
            "id": str(session_id) if pd.notnull(session_id) else None,
            "title": title,
            "start": d_iso,      # all-day event at session date
            "allDay": True,
            "color": color,
            "extendedProps": {
                "team": row.get(col("team")),
                "session_type": s_type,
                "duration": duration,
            }
        })
    return events


def default_calendar_options() -> Dict[str, Any]:
    """Opinionated default options for a clean team planning calendar."""
    return {
        "initialView": "dayGridMonth",
        "firstDay": 1,  # Monday
        "height": "auto",
        "locale": "en",
        "weekNumbers": True,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
        },
        "selectable": True,
        "editable": False,      # flip to True if you’ll implement eventChange
        "dayMaxEventRows": True,
        "eventDisplay": "block",
    }


def render_calendar(
    events: List[Dict[str, Any]],
    key: str,
    options: Optional[Dict[str, Any]] = None,
    custom_css: str = ".fc .fc-toolbar-title{font-size:1.25rem;}",
) -> Dict[str, Any]:
    """
    Render a FullCalendar widget and return its interaction state.

    Args:
        events: List of FullCalendar event dicts (see sessions_df_to_events()).
        key: Streamlit widget key. Change to force a re-render when needed.
        options: FullCalendar options dict. If None, uses default_calendar_options().
        custom_css: Optional CSS injected into the component.

    Returns:
        A state dict provided by streamlit-calendar (callbacks etc.), or {}.
    """
    if _st_calendar is None:
        st.warning(
            "The 'streamlit-calendar' package is not installed or failed to import. "
            "Install it with: pip install streamlit-calendar"
        )
        return {}

    if options is None:
        options = default_calendar_options()

    try:
        state = _st_calendar(
            events=events,
            options=options,
            custom_css=custom_css,
            key=key,
        )
        return state or {}
    except Exception as e:  # pragma: no cover
        st.error(f"Calendar render failed: {e}")
        return {}


def render_legend(styles: Dict[str, Dict[str, str]] = None) -> None:
    """
    Render a small color legend from a styles dict like SESSION_TYPE_STYLES.
    """
    styles = styles or SESSION_TYPE_STYLES
    cols = st.columns(len(styles))
    for i, (code, meta) in enumerate(styles.items()):
        with cols[i]:
            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:0.5rem;">
                        <span style="width:14px;height:14px;border-radius:3px;background:{meta.get('color','#000')};display:inline-block;"></span>
                        <span>{code}</span>
                    </div>""",
                unsafe_allow_html=True
            )