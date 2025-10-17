"""Injury Overview view (read-only).

This page provides coaches and staff with an overview of all injuries 
within a selected team. Each injury entry includes core details, current 
status, and associated treatment sessions.

Data source:
    - Reads from the `injuries` collection via `InjuryRepo`.
    - Player display names are resolved from the `roster` collection.

Notes:
    - Import-safe for mkdocstrings (no side effects at import time).
    - Editing or creating injuries is handled elsewhere (not in this view).
"""

from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime, date

import streamlit as st

from db.repositories.injury_repo import InjuryRepository
from db.errors import DatabaseError
from utils.team_selector import team_selector
from utils.constants import TEAMS


# --- helper: shaded two-column details ----------------------------------------

def _render_injury_details_two_col(injury: Dict[str, Any], comments_str: str | None = None):
    """Shaded two-column block, highlights Current Status."""
    details = {
        "Date": injury.get("injury_date"),
        "Current Status": injury.get("current_status"),
        "Description": injury.get("description"),
        "Diagnostic": injury.get("diagnostic"),
        "Doctor Visit": injury.get("doctor_visit_date"),
        "Doctor Name": injury.get("doctor_name"),
        "Imagery": injury.get("imagery_type"),
        "Projected Duration": injury.get("projected_duration"),
        "Comments": comments_str if comments_str else "—",
    }

    with st.container(border=True):
        items = list(details.items())
        for i in range(0, len(items), 2):
            cols = st.columns(2)
            for j, (label, value) in enumerate(items[i:i+2]):
                val = value if value not in (None, "", []) else "—"
                with cols[j]:
                    if label == "Current Status":
                        st.markdown(
                            f"**{label}: {val}**",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"**{label}:** {val}")

# --- helper: convert to datetime and format -----------------------------------

def _fmt_date(value: Any) -> str:
    """Format date or datetime into DD/MM/YYYY string."""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y")
        except Exception:
            return value  # return as-is if not parseable
    return str(value) if value not in (None, "", []) else "—"

# --- main render --------------------------------------------------------------
def render(mongo, user: str):
    st.title(":material/personal_injury: Injury Overview")

    # Team selector (your standard component)
    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    # Player lookup (player_id -> display name)
    players = mongo.get_player_names(team=team, style="LAST_FIRST")
    if not players:
        st.warning("No players found in roster.", icon=":material/warning:")
        return
    id_to_name = {p["player_id"]: p["display_name"] for p in players}

    # Fetch injuries for the team
    repo = InjuryRepository(mongo.db)
    try:
        injuries = repo.list_injuries_by_team(team)
    except DatabaseError as e:
        st.error(str(e))
        return

    if not injuries:
        st.info("No injuries registered for this team.", icon=":material/info:")
        return

    st.caption(f"Showing {len(injuries)} injuries — last updated first")

    # Render each injury in an expander
    for inj in injuries:
        player_name = id_to_name.get(inj.get("player_id"), f"#{inj.get('player_id')}")
        desc = inj.get("description") or "—"
        latest_status = repo.latest_status(inj)

        header = (
            f"**{player_name}** · {desc} · {latest_status}"
        )

        with st.expander(header, expanded=False):
            # Combine comments list into string for details
            raw_comments = inj.get("comments", [])
            if isinstance(raw_comments, list):
                comments_str = "\n".join([str(c) for c in raw_comments]) if raw_comments else ""
            else:
                comments_str = str(raw_comments) if raw_comments else ""

            # Format key injury dates before rendering
            if inj.get("injury_date"):
                inj["injury_date"] = _fmt_date(inj["injury_date"])
            if inj.get("doctor_visit_date"):
                inj["doctor_visit_date"] = _fmt_date(inj["doctor_visit_date"])

            st.subheader(":material/assist_walker: Injury Details")
            _render_injury_details_two_col(inj, comments_str=comments_str)

            # Treatment sessions
            st.subheader(":material/history: Treatment Sessions")
            sessions: List[Dict[str, Any]] = inj.get("treatment_sessions", []) or []
            if not sessions:
                st.write("_No treatment sessions recorded yet._")
            else:
                try:
                    sessions = sorted(sessions, key=lambda s: s.get("session_date", ""), reverse=True)
                except Exception:
                    pass

                for s in sessions:
                    sd = _fmt_date(s.get("session_date", "—"))
                    author = s.get("created_by", "—")
                    comment = s.get("comment", "—")
                    status_after = s.get("status_after")
                    status_html = (
                        f" · {status_after}"
                        if status_after else ""
                    )
                    with st.expander(f"{sd} — {author}{status_html}", expanded=False):
                        st.markdown(comment or "—")