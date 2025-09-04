import streamlit as st

def team_selector(teams: list[str], key: str = "team") -> str:
    """
    Simple reusable team selector using segmented controls.

    Args:
        teams: list of team names (e.g., ["U18", "U21"])
        key: session_state key to store the selected team

    Returns:
        The selected team (string).
    """
    if key not in st.session_state:
        st.session_state[key] = teams[0]  # default to first team

    selected = st.segmented_control(
        "Select team",
        options=teams,
        selection_mode="single",
        default=None,
        key=key,
    )
    return selected