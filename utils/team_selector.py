import streamlit as st

def team_selector(
        teams: list[str],
        *,
        session_key: str = "selected_team",
        widget_key: str = "team_selector") -> str:
    """
    Simple reusable team selector using segmented controls.

    Args:
        teams: list of team names (e.g., ["U18", "U21"])
        key: session_state key to store the selected team

    Returns:
        The selected team (string).
    """
    if session_key not in st.session_state:
        st.session_state[session_key] = teams[0]  # default to first team

    current = st.session_state[session_key]

    selected = st.segmented_control(
        "Select team",
        options=teams,
        selection_mode="single",
        default=current if current in teams else 0,
        key=widget_key,
    )
    return selected