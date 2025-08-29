"""Session Management view.

Provides an admin interface to:
- Create new training sessions and matches (T1–T4, M).
- Browse sessions in a calendar (with legend and basic click interactions).

Data flow:
    - New sessions are submitted to `MongoWrapper.add_session()`, which is
      responsible for serializing dates, computing `weeknumber`, and generating
      a stable `session_id` (e.g., YYYYMMDD + team).
    - Existing sessions are read via `MongoWrapper.get_sessions_df(team=...)`.

Import safety:
    - This module must be import-safe for mkdocstrings; avoid side effects at import time.
"""

from __future__ import annotations

import streamlit as st
from datetime import date
import pandas as pd

# Utilities
from utils.calendar_view import (
    sessions_df_to_events,
    render_calendar,
    render_legend,
    SESSION_TYPE_STYLES,
)

def render(mongo, user):
    """Render the Session Management admin page.

    Renders a form to add sessions and a calendar view of existing sessions.
    Uses `mongo.add_session()` to insert and `mongo.get_sessions_df()` to read.

    Args:
        mongo: Database wrapper (e.g., `MongoWrapper`) with:
            - `add_session(session: dict) -> bool`
            - `get_sessions_df(team: str | None = None) -> pd.DataFrame`
        user: Authenticated user context (not used here, included for consistency).

    Returns:
        None. Streamlit UI is rendered directly.

    UI/Behavior:
        - **New Session** form:
            - Date (defaults to today)
            - Team (U18/U21)
            - Type (T1–T4, M)
            - Duration (1–240 min)
          On submit, delegates to `mongo.add_session()`. Success triggers `st.rerun()` to refresh the calendar.

        - **Calendar**:
            - Team filter (All/U18/U21)
            - Legend with color coding per session type
            - Click interactions:
                - dateClick → info banner with clicked date
                - eventClick → expander with raw event payload

    Error handling:
        - Wraps DB operations in try/except and displays `st.error` with details.
        - Falls back to `mongo.get_sessions()` if `get_sessions_df()` is unavailable.

    Notes:
        - `MongoWrapper.add_session()` should:
            - serialize `date` to a proper datetime
            - compute `weeknumber` from ISO calendar
            - generate `session_id` deterministically (e.g., `YYYYMMDD + team`)
        - This page intentionally **does not** edit `session_id` once created.
    """

    st.title(":material/calendar_month: Session Management")

    # --- Add Session Form ----------------------------------------------------
    st.subheader("New Session")
    with st.form("add_session_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            session_date = st.date_input("Date", value=date.today())
        with col2:
            team = st.selectbox("Team", ["U18", "U21"])
        with col3:
            session_type = st.selectbox("Type", ["T1", "T2", "T3", "T4", "M"])
        with col4:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, step=5)

        submitted = st.form_submit_button("Add Session", icon=":material/save:")
        if submitted:
            session = {
                "date": session_date,         # mongo wrapper should serialize dates
                "team": team,
                "session_type": session_type,
                "duration": int(duration),
            }
            try:
                if mongo.add_session(session):
                    st.success("Session added!", icon=":material/check_box:")
                    st.rerun()  # refresh the calendar immediately
                else:
                    st.error("Failed to add session.", icon=":material/error_outline:")
            except Exception as e:
                st.error(f"Error adding session: {e}")

    # --- Calendar View -------------------------------------------------------
    st.subheader("Calendar")

    team_filter = st.selectbox("Filter by Team", ["All", "U18", "U21"], key="sess_team_filter")
    selected_team = None if team_filter == "All" else team_filter

    # Fetch sessions as DataFrame (use your existing wrapper)
    try:
        df = mongo.get_sessions_df(team=selected_team)
    except AttributeError:
        # Fallback if you only have a list API
        try:
            docs = mongo.get_sessions(team=selected_team)  # list[dict]
            df = pd.DataFrame(docs) if docs else pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to load sessions: {e}")
            return
    except Exception as e:
        st.error(f"Failed to load sessions: {e}")
        return

    events = sessions_df_to_events(df)

    state = render_calendar(
        events=events,
        key=f"calendar_{selected_team or 'all'}",
        options=None,  # use defaults; supply your own dict to override
    )

    st.markdown("**Legend**")
    render_legend(SESSION_TYPE_STYLES)

    # Optional: react to interactions
    if state.get("callback") == "dateClick":
        clicked = state["dateClick"]["dateStr"]  # 'YYYY-MM-DD'
        st.info(f"Clicked date: {clicked}")
    elif state.get("callback") == "eventClick":
        evt = state["eventClick"]["event"]
        st.info(f"Selected: {evt.get('title','Session')}")
        with st.expander("Event details"):
            st.json(evt)