"""Injury Management

Tabs:
- Register Injury
- Register Treatment Session

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

from utils.constants import TEAMS, IMAGERY_TYPES, INJURY_DURATION_UNITS, INJURY_STATUS

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

    # --- Tabs ---
    tab1, tab2 = st.tabs([":material/assist_walker: Register New Injury", ":material/healing: Treatment sessions"])

    with tab1:
        st.subheader(":material/assist_walker: Register New Injury")

        with st.form("register_injury_form", clear_on_submit=True):
            injury_date = st.date_input("Date of Injury", value=date.today(), width=200)

            # Description and Diagnostic side by side
            col1, col2 = st.columns(2)
            with col1:
                description = st.text_area("Description of Injury")
            with col2:
                diagnostic = st.text_area("Diagnostic of Injury")

            # Doctor visit date, doctor name, imagery type side by side
            col3, col4, col5 = st.columns(3)
            with col3:
                doctor_visit_date = st.date_input("Date of Doctor Visit (optional)", value=None)
            with col4:
                doctor_name = st.text_input("Name of Doctor Visited (optional)")
            with col5:
                imagery_type = st.selectbox("Type of Imagery Done (optional)", IMAGERY_TYPES)

            # Projected duration split into value and unit
            col6, col7 = st.columns([2, 1])
            with col6:
                projected_duration_value = st.number_input("Projected Duration Value", min_value=0, step=1)
            with col7:
                projected_duration_unit = st.selectbox("Unit", INJURY_DURATION_UNITS)

            comments = st.text_area("Comments")

            submitted = st.form_submit_button(":material/save: Save injury", type="primary")
            if submitted:
                # normalize optional fields
                initial_comments = []
                if comments and str(comments).strip():
                    initial_comments.append({
                        "ts": datetime.utcnow(),
                        "author": user,
                        "text": str(comments).strip(),
                    })

                injury_doc = {
                    "player_id": int(player_id),
                    "team": team,
                    "injury_date": injury_date,                   # <-- pass date, repo normalizes
                    "description": str(description).strip(),
                    "diagnostic": str(diagnostic).strip(),
                    "doctor_visit_date": doctor_visit_date or None,  # <-- pass date/None
                    "doctor_name": str(doctor_name).strip() or None,
                    "imagery_type": imagery_type or None,
                    "projected_duration": (
                        f"{projected_duration_value} {projected_duration_unit}"
                        if projected_duration_value else None
                    ),
                    "comments": initial_comments,                 # <-- list of {ts, author, text}
                    # audit fields (repo also sets defaults, but fine to include)
                    "created_by": user,
                    "created_at": datetime.utcnow(),
                    "updated_by": user,
                    "updated_at": datetime.utcnow(),
                    # optional defaults the repo ensures:
                    # "current_status": "open",
                    # "treatment_sessions": [],
                }

                try:
                    mongo.insert_player_injury(injury_doc)
                    st.success("Injury registered successfully.", icon=":material/check_circle:")
                except Exception as e:
                    st.error(f"Failed to save injury: {e}", icon=":material/error_outline")


    with tab2:
        #st.subheader(":material/healing: Register a treatment session")

        # Fetch injuries for selected player, newest first
        injuries = mongo.get_player_injuries(player_id)

        if not injuries:
            st.info("No injuries registered for this player.", icon=":material/info:")
        else:
            # --- Injury selection -------------------------------------------------
            def _label(injury: dict) -> str:
                d = injury.get("injury_date")
                if isinstance(d, datetime):
                    ds = d.strftime("%Y-%m-%d")
                else:
                    ds = str(d) if d else "—"
                desc = (injury.get("description") or "")[:40]
                return f"{ds} - {desc}"

            injury_options = [_label(i) for i in injuries]
            selected_idx = st.selectbox("Select an injury to add a treatment session",
                                        options=range(len(injury_options)),
                                        format_func=lambda i: injury_options[i])
            
            selected_injury = injuries[selected_idx]

            # --- Existing comments (plain text list -> single string) ------------
            comments = selected_injury.get("comments", [])
            if isinstance(comments, list):
                comments_str = "\n".join([str(c) for c in comments]) if comments else ""
            else:
                comments_str = str(comments) if comments is not None else ""

            # --- Details (two-column layout) -------------------------------------
            st.subheader(":material/assist_walker: Injury Details")

            details = {
                "Date": selected_injury.get("injury_date"),
                "Current Status": selected_injury.get("current_status"),   # <- new
                "Description": selected_injury.get("description"),
                "Diagnostic": selected_injury.get("diagnostic"),
                "Doctor Visit": selected_injury.get("doctor_visit_date"),
                "Doctor Name": selected_injury.get("doctor_name"),
                "Imagery": selected_injury.get("imagery_type"),
                "Projected Duration": selected_injury.get("projected_duration"),
                "Comments": comments_str if comments_str else "—",
            }

 
            # Show fields two per row in a container
            with st.container(border=True):
                items = list(details.items())
                for i in range(0, len(items), 2):
                    cols = st.columns(2)
                    for j, (label, value) in enumerate(items[i:i+2]):
                        with cols[j]:
                            # --- format dates nicely ---
                            if isinstance(value, (datetime, date)):
                                value = value.strftime("%d/%m/%Y")
                            elif isinstance(value, str):
                                # Handle ISO strings if MongoDB returns them that way
                                try:
                                    value = datetime.fromisoformat(value).strftime("%d/%m/%Y")
                                except Exception:
                                    pass
                            st.markdown(f"**{label}:** {value if value not in (None, '', []) else '—'}")

                # Optional: show previous treatment sessions (if you store them)
                prior_sessions = selected_injury.get("treatment_sessions", [])
                if prior_sessions:
                    st.subheader(":material/history: Previous Treatment Sessions")

                    def _to_dt(x):
                        # handle datetime, date, ISO string gracefully
                        if isinstance(x, datetime):
                            return x
                        try:
                            return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
                        except Exception:
                            return None

                    prior_sessions = sorted(
                        prior_sessions,
                        key=lambda s: (_to_dt(s.get("session_date")) or datetime.min),
                        reverse=True,
                    )

                    for s in prior_sessions:
                        sd = _to_dt(s.get("session_date"))
                        sd_label = sd.strftime("%Y-%m-%d") if sd else "—"
                        author = s.get("created_by", "—")
                        txt = s.get("comment", "—")
                        with st.expander(f"{sd_label} — {author}"):
                            st.markdown(txt if txt else "—")
                            st.caption(f"Status after: {s.get('status_after', '—')}")

            # --- Add new treatment session/comment -------------------------------
            st.subheader(":material/healing: Add Treatment Session")
            with st.form("add_treatment_session_form", clear_on_submit=True):

                # Two columns: date (left) + current status (right)
                c1, c2 = st.columns(2)
                with c1:
                    treatment_session_date = st.date_input("Treatment Session Date", value=date.today())

                with c2:
                    # Preselect current status if present on the injury, else the first option
                    _current = selected_injury.get("current_status")
                    if _current in INJURY_STATUS:
                        _idx = INJURY_STATUS.index(_current)
                    else:
                        _idx = 0
                    current_injury_status = st.selectbox("Current Injury Status", INJURY_STATUS, index=_idx)

                treatment_session_comment = st.text_area(
                    "Treatment Session Comments",
                    placeholder="Treatment details, response, next steps…",
                    height=140,
                )

                submitted = st.form_submit_button(":material/save: Add Treatment Session", type="primary")

                if submitted:
                    if not str(treatment_session_comment).strip():
                        st.warning("Please enter a session comment.", icon=":material/warning:")
                    else:
                        treatment_session = {
                            "session_date": treatment_session_date,           # date|datetime|ISO ok
                            "comment": treatment_session_comment.strip(),
                            "status_after": current_injury_status,            # optional; repo defaults it anyway
                            "created_by": user,
                            "created_at": datetime.utcnow(),
                        }

                        ok = mongo.add_treatment_session(
                            injury_id=str(selected_injury["_id"]),            # or selected_injury["injury_id"]
                            treatment_session=treatment_session,
                            current_status=current_injury_status,
                            updated_by=user,
                        )

                        if ok:
                            st.success("Treatment session added.", icon=":material/check_circle:")
                            st.rerun()
                        else:
                            st.warning("No changes applied.", icon=":material/warning:")