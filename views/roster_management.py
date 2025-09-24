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
from utils.team_selector import team_selector
from utils.ui_utils import get_table_height

from utils.constants import TEAMS


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

    # --- TEAM SELECTOR ---
    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    st.caption(f"Editing roster for **{team}**")

    try:
        team_roster_df: pd.DataFrame = mongo.get_roster_df(team=team)
    except DatabaseError as e:
        st.error(str(e), icon=":material/error_outline")
        return

    # Ensure expected columns when empty
    if team_roster_df.empty:
        team_roster_df = pd.DataFrame(columns=["player_id", "player_first_name", "player_last_name", "active"])

    # Capture ORIGINAL ids for this team (used in save validation)
    original_ids = set(
        pd.to_numeric(team_roster_df.get("player_id", pd.Series(dtype="Int64")), errors="coerce")
        .astype("Int64").dropna().astype(int)
    )

    # Prepare the dataframe for the editor (hide 'team' in UI)
    df_view = team_roster_df.drop(columns=["team"], errors="ignore")
    if df_view.empty:
        df_view = pd.DataFrame(columns=["player_id", "player_first_name", "player_last_name", "active"])

    with st.form(f"roster_form_{team}"):
        edited_df = st.data_editor(
            df_view,
            key=f"roster_editor_{team}",
            column_config={
                "player_id": st.column_config.NumberColumn(
                    "Player ID", required=True, format="%i", disabled=True
                ),
                "player_last_name": st.column_config.TextColumn("Last Name", required=True),
                "player_first_name": st.column_config.TextColumn("First Name", required=True),
                # ⚠️ don't include "team" here since we dropped that column in df_view
            },
            height=get_table_height(len(df_view)),
            num_rows="fixed",              # 🚫 prevent adding/removing rows
            use_container_width=True,
        )

        submitted = st.form_submit_button(":material/save: Save changes", type="primary")

        if submitted:
            try:
                # ---- Safety: no add/remove (same policy as before) ----
                edited_ids = set(
                    pd.to_numeric(edited_df["player_id"], errors="coerce")
                    .astype("Int64").dropna().astype(int)
                )
                if edited_ids != original_ids:
                    st.error(
                        "Player additions/removals are not allowed here. "
                        "Please revert or manage roster membership directly in MongoDB.",
                        icon=":material/error_outline:",
                    )
                    st.stop()

                # ---- Safety: no duplicate IDs within this team ----
                if edited_df["player_id"].duplicated(keep=False).any():
                    dups = edited_df["player_id"][edited_df["player_id"].duplicated(keep=False)].tolist()
                    st.error(f"Duplicate player_id(s) in the table: {sorted(set(dups))}", icon=":material/error_outline:")
                    st.stop()

                # ---- Row-level validation ----
                req_cols = ["player_first_name", "player_last_name"]
                missing_any = any(
                    edited_df[c].isna().any() or (edited_df[c].astype(str).str.strip() == "").any()
                    for c in req_cols if c in edited_df.columns
                )
                if missing_any:
                    st.error("Empty values detected. Please complete all required name fields.", icon=":material/error_outline:")
                    st.stop()

                # ---- Reattach correct team & coerce types ----
                to_save = edited_df.copy()
                to_save["team"] = team
                to_save["player_id"] = pd.to_numeric(to_save["player_id"], errors="coerce").astype("Int64")
                if to_save["player_id"].isna().any():
                    st.error("One or more player_id values are invalid.", icon=":material/error_outline:")
                    st.stop()

                # ---- Team-scoped replace ----
                ok = mongo.save_roster_df(to_save, team=team)
                if ok:
                    st.success(f"Roster for {team} updated.", icon=":material/check_box:")
                else:
                    st.error("Failed to save roster.", icon=":material/error_outlin:")

            except DatabaseError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Validation or save failed: {e}", icon=":material/error_outline:")