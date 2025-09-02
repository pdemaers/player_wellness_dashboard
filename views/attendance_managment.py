"""Attendance Management view.

Provides a coach interface to:
- Register player attendance (present + absent reasons) in one step.
- Select session by date (dd/mm/yyyy); each team has max one session per day.

Data flow:
    - Session dates loaded via `MongoWrapper.get_recent_sessions(team=...)` (dedup by date).
    - Rosters retrieved from `MongoWrapper.get_roster_players(team=...)`.
    - Full attendance saved via `MongoWrapper.upsert_attendance_full()`.

Import safety:
    - This module must be import-safe for mkdocstrings; avoid side effects at import time.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Any, List
from utils.team_selector import team_selector

import streamlit as st

from utils.constants import TEAMS, ABSENCE_REASONS

def _ddmmyyyy(d: date | datetime | str) -> str:
    """Render a date-like field as dd/mm/yyyy (best-effort)."""
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    # string fallback
    try:
        parsed = datetime.fromisoformat(str(d)).date()
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return str(d)


def _to_date(d: date | datetime | str) -> date:
    """Parse a date-like field to a date; fallback to today on failure."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    try:
        return datetime.fromisoformat(str(d)).date()
    except Exception:
        return date.today()


def render(mongo, user):
    """Render attendance page with one-step present/absent registration."""
    st.title(":material/groups_2: Attendance")

    # --- TEAM ---------------------------------------------------------------
    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.")
        return

    # --- SESSIONS (DATE-ONLY) ----------------------------------------------
    try:
        recent_sessions = mongo.get_recent_sessions(team=team, limit=12, up_to_date=date.today())
    except Exception as e:
        st.error(f"Unable to load sessions: {e}")
        return

    if not recent_sessions:
        st.warning("No sessions found for this team.")
        return

    # Deduplicate by date (desc), map date -> session_id (first occurrence is the latest that day)
    seen_dates: set[date] = set()
    date_to_session: Dict[date, Dict[str, Any]] = {}
    for s in sorted(recent_sessions, key=lambda x: _to_date(x.get("date")), reverse=True):
        d = _to_date(s.get("date"))
        if d not in seen_dates:
            seen_dates.add(d)
            date_to_session[d] = s
        if len(date_to_session) >= 6:  # today + last 5
            break

    if not date_to_session:
        st.warning("No usable session dates found.")
        return

    all_dates_desc = sorted(date_to_session.keys(), reverse=True)
    # Default to today if present; otherwise the most recent date
    default_idx = 0
    if date.today() in date_to_session:
        default_idx = all_dates_desc.index(date.today())

    date_labels = [_ddmmyyyy(d) for d in all_dates_desc]
    selected_label = st.selectbox("Session date (dd/mm/yyyy)", options=date_labels, index=default_idx)
    selected_date = all_dates_desc[date_labels.index(selected_label)]
    session = date_to_session[selected_date]
    session_id = session.get("session_id")

    # --- ROSTER -------------------------------------------------------------
    try:
        roster = mongo.get_roster_players(team=team)
    except Exception as e:
        st.error(f"Unable to load roster: {e}")
        return

    if not roster:
        st.warning("No players found for this team.")
        return

    # Normalize and sort players for stable UI
    players = []
    for p in roster:
        pid = p.get("player_id")
        try:
            pid = int(pid)
        except Exception:
            pass
        name = f"{p.get('player_last_name', p.get('last_name','')).upper()}, {p.get('player_first_name', p.get('first_name',''))}".strip(", ")
        players.append({"player_id": pid, "name": name})
    players.sort(key=lambda x: x["name"])

    # --- PRESENTS SELECTION (PILLS) -----------------------------------------
    st.subheader(":material/group_add: Mark Presents")

    player_labels = [p["name"] for p in players]
    id_by_label = {p["name"]: p["player_id"] for p in players}

    selected_labels: List[str] = st.pills(
        "Players (present)",
        options=player_labels,
        selection_mode="multi",
        default=[],
        key=f"present_pills_{session_id}"
    )

    present_ids = [id_by_label[lbl] for lbl in selected_labels]
    present_set = set(present_ids)

    # --- ABSENTEES (dynamic from selection) ---------------------------------
    absentees = [p for p in players if p["player_id"] not in present_set]

    st.divider()
    st.subheader(":material/group_off: Absentees & Reasons")
    st.caption("Choose a reason for each player not selected as present.")

    absentee_reasons: Dict[int, str] = {}
    for p in absentees:
        with st.container(border=True, vertical_alignment="center"):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.write(f"**{p['name']}**")   # 👈 only name now
            with c2:
                absentee_reasons[p["player_id"]] = st.selectbox(
                    "Reason",
                    ABSENCE_REASONS,
                    index=0,
                    key=f"abs_{session_id}_{p['player_id']}",
                    label_visibility="collapsed"
                )

    # --- SAVE (ONE STEP) ----------------------------------------------------
    if st.button("Save attendance", type="primary", icon=":material/save:"):
        absent_items = [{"player_id": int(pid), "reason": reason} for pid, reason in absentee_reasons.items()]
        try:
            mongo.upsert_attendance_full(
                session_id=session_id,
                team=team,
                present_ids=[int(x) for x in present_ids],
                absent_items=absent_items,
                user=user if isinstance(user, str) else getattr(user, "name", str(user))
            )
            # selected_label is the dd/mm/yyyy string from the session date dropdown
            st.success(f"Attendance saved for {selected_label} — {team}.", icon=":material/check_box:")
        except Exception as e:
            st.error(f"Failed to save attendance: {e}", icon=":material/error_outline:")