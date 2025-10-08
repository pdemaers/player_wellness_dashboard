"""
Player Measurements (height & weight) entry form.

This admin view lets staff record monthly height (cm, int) and weight (kg, 1 decimal)
for every player in a selected team on a given date.

Constraints & behavior:
    - One measurement document per (team, date); saving will UPSERT that document.
    - Each row has: player_id, player name, height_cm, weight_kg, absent.
      If 'absent' is True, height/weight are stored as null.
    - Basic validation enforces integer heights and 1-decimal weights on save.
    - Standard audit fields are included: created, last_updated, user.

Data source:
    - Reads roster from MongoDB via PlayerMeasurementsRepo.get_roster_for_team()
    - Writes to the `player_measurements` collection via PlayerMeasurementsRepo.upsert_measurement_session()

Notes:
    - Import-safe for mkdocstrings (no side effects at import time).
    - Requires: utils.team_selector.team_selector, utils.constants.TEAMS
"""

from __future__ import annotations
from datetime import date, datetime
from typing import List, Dict, Any

import streamlit as st
import pandas as pd

from utils.team_selector import team_selector
from utils.ui_utils import get_table_height
from utils.constants import TEAMS
from db.repositories.player_measurements_repo import PlayerMeasurementsRepository
from db.errors import DatabaseError


def render(mongo, user: str | None = None) -> None:
    """Render the Player Measurements view."""
    st.title(":material/square_foot: Player Measurements")

    repo = PlayerMeasurementsRepository(mongo)
    try:
        repo.ensure_indexes()
    except DatabaseError as e:
        st.error(f"Failed to ensure indexes on 'player_measurements': {e}", icon=":material/error:")
        st.stop()

    # --- Team selection ---
    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    # --- Date selection ---
    meas_date: date = st.date_input("Measurement date", value=date.today(), format="DD/MM/YYYY", width=200)

    # --- Load roster for table ---
    try:
        roster = mongo.get_player_names(team=team, style="LAST_FIRST")  # [{player_id, name}]
    except DatabaseError as e:
        st.error(f"Failed to load roster: {e}")
        return

    if not roster:
        st.warning("No players found for the selected team.", icon=":material/warning:")
        return

    # Build editable table
    df_source = pd.DataFrame(
        {
            "player_id": [p["player_id"] for p in roster],
            "player_name": [p["display_name"] for p in roster],   # consistent with other modules
            "height_cm": [None] * len(roster),
            "weight_kg": [None] * len(roster),
            "absent": [False] * len(roster),
        }
    )

    st.caption("Enter integer heights (cm) and 1-decimal weights (kg). Mark players absent if not measured.")
    edited_df = st.data_editor(
        df_source,
        hide_index=True,
        use_container_width=True,
        column_config={
            "player_name": st.column_config.TextColumn("Player", disabled=True),
            "height_cm": st.column_config.NumberColumn("Height (cm)", step=1, format="%d"),
            "weight_kg": st.column_config.NumberColumn("Weight (kg)", step=0.1, format="%.1f"),
            "absent": st.column_config.CheckboxColumn("Absent"),
        },
        column_order=["player_name", "height_cm", "weight_kg", "absent"],  # hides player_id
        num_rows="fixed",
        key=f"measurements_editor_{team}_{meas_date.isoformat()}",
        height=get_table_height(len(df_source))
    )

    # --- Save button ---
    if st.button("Save measurements", type="primary", icon=":material/save:"):
        try:
            entries: List[Dict[str, Any]] = []
            for _, row in edited_df.iterrows():
                pid = str(row["player_id"])
                pname = str(row["player_name"])
                absent = bool(row["absent"])

                # Normalize values
                height_val = None if pd.isna(row["height_cm"]) else int(row["height_cm"])
                weight_val = None if pd.isna(row["weight_kg"]) else round(float(row["weight_kg"]), 1)

                # If absent, override measurements to None
                if absent:
                    height_val, weight_val = None, None

                # Basic validation: if not absent, enforce required numeric inputs
                if not absent:
                    if height_val is None or weight_val is None:
                        st.error(f"Missing values for {pname}. Either mark absent or fill both fields.", icon=":material/error:")
                        st.stop()

                entries.append(
                    {
                        "player_id": pid,
                        "player_name": pname,
                        "height_cm": height_val,
                        "weight_kg": weight_val,
                        "absent": absent,
                    }
                )

            doc_id = repo.upsert_measurement_session(
                team=team,
                measurement_date=meas_date,
                entries=entries,
                user=user or "unknown",
            )
            st.success(f"Measurements saved for {team} on {meas_date.isoformat()}.", icon=":material/check_circle:")
        except ValueError as ve:
            st.error(f"Validation error: {ve}", icon=":material/error:")
        except DatabaseError as de:
            st.error(f"Database error while saving: {de}", icon=":material/error:")
        except Exception as e:
            st.error(f"Unexpected error: {e}", icon=":material/error:")