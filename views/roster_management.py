"""Roster Management view (admin-only, no adds/deletes).

This page lets staff correct names and team assignments for existing players.
To comply with GDPR and preserve cross-app integrity, **player_id is immutable**
and **no new players can be added** here. Player additions should be performed
directly in the database (e.g., MongoDB Compass) by an admin.

Data source:
    - Reads/writes the `roster` collection via `MongoWrapper`.
    - `player_id` is the critical foreign key used by the Registration app.

Notes:
    - Import-safe for mkdocstrings (no side effects at import time).
"""

from __future__ import annotations
from typing import Any, Optional  # add this

import streamlit as st
import pandas as pd
from datetime import datetime
from db.mongo_wrapper import DatabaseError
from utils.ui_utils import get_table_height

from main import TEAMS


def render(mongo: Any, user: Optional[dict[str, Any]]) -> None:
    """Render the Roster Management page (edit-only; no adds/deletes).

    Loads the roster via `mongo.get_roster_df()`, presents an edit table with
    `player_id` disabled, and saves **only if** the set of player IDs is unchanged.

    Args:
        mongo: Database wrapper providing `get_roster_df()` and `save_roster_df()`.
        user: Authenticated user context (not used here but kept for consistency).

    Returns:
        None. Renders Streamlit UI directly.

    Error handling:
        - Database errors are caught and shown with `st.error`.

    Policy:
        - **Player additions/removals are not allowed** on this screen.
          Perform those in MongoDB directly (admin only).
    """
    st.title(":material/people: Team Roster Editor")
    st.caption(
        "Edit names or team for existing players. "
        "**Adding or removing players must be done by an admin in MongoDB (Compass).**"
    )

    try:
        df: pd.DataFrame = mongo.get_roster_df()
    except DatabaseError as e:
        st.error(str(e), icon=":material/error_outline")
        return

    # Keep a frozen copy of the original IDs for validation later
    original_ids = set(pd.to_numeric(df["player_id"], errors="coerce").astype("Int64").dropna().astype(int))

    try:
        edited = st.data_editor(
            df,
            column_config={
                "player_id": st.column_config.NumberColumn(
                    "Player ID", required=True, format="%i", disabled=True
                ),
                "player_last_name": st.column_config.TextColumn("Last Name", required=True),
                "player_first_name": st.column_config.TextColumn("First Name", required=True),
                "team": st.column_config.SelectboxColumn("Team", options=TEAMS, required=True),
                # Uncomment when needed:
                # "date_of_birth": st.column_config.DateColumn(
                #     "Date of Birth", format="DD/MM/YYYY", min_value=datetime(2000, 1, 1)
                # ),
                # "shirt_nr": st.column_config.NumberColumn("Shirt #", min_value=1, max_value=99),
                # "position": st.column_config.SelectboxColumn("Position", options=POSITIONS),
                # "preferred_foot": st.column_config.SelectboxColumn("Preferred Foot", options=["Left", "Right"])
            },
            height=get_table_height(len(df)),
            num_rows="fixed",              # 🚫 prevent adding/removing rows
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Failed to render editor: {e}", icon=":material/error_outline")
        return

    if st.button("Save changes", type="primary", icon=":material/save:"):
        # Safety checks before saving
        try:
            # Ensure player_id set is unchanged
            edited_ids = set(pd.to_numeric(edited["player_id"], errors="coerce").astype("Int64").dropna().astype(int))
            if edited_ids != original_ids:
                st.error(
                    "Player additions/removals are not allowed here. Please revert changes or perform roster updates directly in MongoDB.",
                    icon=":material/error_outline"
                )
                return

            # Basic per-row validation (optional: add stricter rules here)
            if edited[["player_first_name", "player_last_name", "team"]].isnull().any().any():
                st.error("Empty values detected. Please complete all required fields.", icon=":material/error_outline")
                return

            if mongo.save_roster_df(edited):
                st.success("Roster updated.", icon=":material/check_box")
            else:
                st.error("Failed to save roster.", icon=":material/error_outline")
        except DatabaseError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Validation or save failed: {e}", icon=":material/error_outline")