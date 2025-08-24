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