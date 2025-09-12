"""Injury Management

Tabs:
- Register Injury

Assumes:
    - NameStyle & ABSENCE_REASONS in `constants`
    - get_player_names()

"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Any, List
from utils.team_selector import team_selector

import streamlit as st
import pandas as pd

from utils.ui_utils import get_table_height

from utils.constants import TEAMS

# --- Module helpers ------------------------------------------------------------

# --- Main render function ---------------------------------------------------

def render(mongo, user):
    """Render injury management page."""
    
    st.title(":material/personal_injury: Injury Management")
             
    # --- TEAM ---------------------------------------------------------------
    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return
    
    # --- Load roster ---
    players = mongo.get_player_names(team=team, style="LAST_FIRST")
    if not players:
        st.warning("No players found in roster.", icon=":material/warning:")
        return

    # --- Player selection ---
    player_lookup = {p["display_name"]: p for p in players}
    selected_name = st.selectbox("Select a player", list(player_lookup.keys()))
    player = player_lookup[selected_name]
    player_id = player["player_id"]

