"""Attendance Management view.

Tabs:
- Register attendance (present + absence reasons in one go)
- Overview (player × session matrix with emojis)
- Match minutes (one-and-done entry per match)

Assumes:
    - NameStyle & ABSENCE_REASONS in `constants`
    - get_player_names(), get_recent_sessions(), upsert_attendance_full(),
      save_match_minutes_once() in `mongo_wrapper`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Any, List
from utils.team_selector import team_selector

import streamlit as st
import pandas as pd

from utils.ui_utils import get_table_height

from utils.constants import TEAMS, ABSENCE_REASONS, PRESENT_EMOJI, UNKNOWN_EMOJI

# Emojies used in the overview
EMOJI_BY_REASON_ID = {r["id"]: r["emoji"] for r in ABSENCE_REASONS}

# --- Module helpers ------------------------------------------------------------

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
    
# def icon_html(icon: str) -> str:
#     return f"<span class='material-icons'>{icon}</span>"

def _to_short_label(full_str: str) -> str:
    """Return 'dd/mm' from 'dd/mm/yyyy' (safe)."""
    try:
        dt = datetime.strptime(str(full_str), "%d/%m/%Y")
        return dt.strftime("%d/%m")
    except Exception:
        return str(full_str)

def _safe_legend(absence_reasons) -> str:
    """Legend string built robustly from constants.ABSENCE_REASONS."""
    parts = []
    for r in absence_reasons:
        emoji = r.get("emoji", "")
        label = r.get("label", "")
        parts.append(f"{emoji} {label}".strip())
    middle = "  ·  ".join(map(str, parts))
    return f"Legend: {PRESENT_EMOJI} present  ·  {middle}  ·  {UNKNOWN_EMOJI} no entry"

def _pad_center(x: str) -> str:
    """Cheap visual centering for st.data_editor (adds spacing)."""
    return f" {x} "

def _select_session_by_date(
    mongo,
    team: str,
    title: str,
    *,
    show_all: bool,
    max_dates: int,
    up_to: date,
    session_type: str | None,   # "M" for matches, None for trainings/all
):
    """Render a date-only selectbox and return (session_dict, selected_label)."""
    fetch_limit = None if show_all else max_dates
    recent = mongo.get_recent_sessions(
        team=team,
        limit=fetch_limit,
        up_to_date=up_to,
        session_type=session_type,
    )

    # De-duplicate by date (keep latest per day)
    seen_dates = set()
    date_to_session: Dict[date, Dict[str, Any]] = {}
    for s in sorted(recent, key=lambda x: _to_date(x.get("date")), reverse=True):
        d = _to_date(s.get("date"))
        if d not in seen_dates:
            seen_dates.add(d)
            date_to_session[d] = s
        if not show_all and len(date_to_session) >= max_dates:
            break

    if not date_to_session:
        return None, None

    all_dates_desc = sorted(date_to_session.keys(), reverse=True)
    default_idx = all_dates_desc.index(date.today()) if date.today() in date_to_session else 0
    labels = [_ddmmyyyy(d) for d in all_dates_desc]

    selected_label = st.selectbox(title, options=labels, index=default_idx, width=200)
    selected_date = all_dates_desc[labels.index(selected_label)]
    session = date_to_session[selected_date]
    return session, selected_label
    
def build_attendance_overview_df(
    mongo,
    team: str,
    up_to: date | None = None,
    limit: int | None = None,
    absence_meta: List[Dict[str, str]] | None = None,
) -> pd.DataFrame:
    """
    Build a player x session-date matrix with Material icons for attendance status.

    Cell values:
      - :material-check_circle:  if present
      - :material-<reason_icon>: if absent with reason
      - :material-help:          if no attendance data recorded for that player/session

    Args:
        mongo: MongoWrapper
        team: "U18" | "U21"
        up_to: include sessions on or before this date (defaults to today)
        limit: cap number of session dates after de-duplication (None = no cap)
        absence_meta: list of {"id","label","icon"} to map reasons to icons

    Returns:
        pandas.DataFrame with index = player names, columns = dd/mm/yyyy strings.
    """
    up_to = up_to or date.today()

    # --- fetch sessions (dedup by date, latest per day) ---
    sessions = mongo.get_recent_sessions(team=team, limit=None, up_to_date=up_to, session_type=["T1", "T2", "T3", "T4"])
    sessions_sorted = sorted(sessions, key=lambda s: _to_date(s.get("date")), reverse=False)

    seen = set()
    by_date: Dict[date, Dict[str, Any]] = {}
    for s in sessions_sorted:
        d = _to_date(s.get("date"))
        if d not in seen:
            seen.add(d)
            by_date[d] = s
    session_dates = sorted(by_date.keys())  # oldest -> newest
    if isinstance(limit, int) and limit > 0:
        session_dates = session_dates[-limit:]

    # --- fetch roster ---
    roster = mongo.get_roster_players(team=team)
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

    # --- build icon maps ---
    absence_meta = absence_meta or []
    # reason_icon_by_id = {r["id"]: r["icon"] for r in absence_meta}

    # --- pull all attendance docs for these session_ids in one go ---
    session_ids = [by_date[d]["session_id"] for d in session_dates]
    docs = list(mongo.db["attendance"].find({"session_id": {"$in": session_ids}}, {"_id": 0}))
    att_by_session: Dict[str, Dict[str, Any]] = {doc["session_id"]: doc for doc in docs}

    # quick lookup helpers
    def _present_set(doc) -> set[int]:
        return set(int(x) for x in (doc.get("present") or []))

    def _absent_map(doc) -> Dict[int, str]:
        out = {}
        for a in (doc.get("absent") or []):
            try:
                out[int(a["player_id"])] = str(a["reason"])
            except Exception:
                continue
        return out

    # precompute maps per session_id
    pres_by_sid: Dict[str, set[int]] = {}
    absc_by_sid: Dict[str, Dict[int, str]] = {}
    for sid, doc in att_by_session.items():
        pres_by_sid[sid] = _present_set(doc)
        absc_by_sid[sid] = _absent_map(doc)

    # --- assemble DataFrame (icons as strings like ":material-xyz:") ---
    col_labels = [_ddmmyyyy(d) for d in session_dates]
    matrix: Dict[str, List[str]] = {col: [] for col in col_labels}

    for player in players:
        pid = player["player_id"]
        for d, col in zip(session_dates, col_labels):
            sid = by_date[d]["session_id"]
            if sid in pres_by_sid and pid in pres_by_sid[sid]:
                matrix[col].append(PRESENT_EMOJI)
            elif sid in absc_by_sid and pid in absc_by_sid[sid]:
                reason_id = absc_by_sid[sid][pid]
                matrix[col].append(EMOJI_BY_REASON_ID.get(reason_id, UNKNOWN_EMOJI))
            else:
                matrix[col].append(UNKNOWN_EMOJI)

    df = pd.DataFrame(matrix, index=[p["name"] for p in players])
    return df

# --- Main render function ---------------------------------------------------

def render(mongo, user):
    """Render attendance page with one-step present/absent and match minutes registration."""
    
    st.title(":material/how_to_reg: Attendance & Match Minutes")
             
    # --- TEAM ---------------------------------------------------------------
    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([":material/groups_2: Register training attendance", ":material/table_chart: Training attendance overview", ":material/timer: Register match minutes", ":material/table_chart: Match minutes overview"])

    with tab1:

        # --- SESSIONS (DATE-ONLY) ----------------------------------------------

        st.subheader(":material/groups_2: Register Attendance")

        show_all = st.toggle(
            "Show all session dates",
            value=False,
            help="Temporarily list all sessions to backfill absences."
        )

        session, selected_label = _select_session_by_date(
            mongo=mongo,
            team=team,
            title="Session date (dd/mm/yyyy)",
            show_all=show_all,
            max_dates=6,
            up_to=date.today(),
            session_type=["T1", "T2", "T3", "T4"],  # ✅ only trainings
        )
        if not session:
            st.warning("No usable session dates found.")
            st.stop()

        session_id = session.get("session_id")

        # Fetch players from the new helper; it returns {"player_id", "display_name", ...}
        players_raw = mongo.get_player_names(team=team, style="LAST_FIRST")

        # Normalize so the rest of the UI can use p["name"]
        players = [{"player_id": p["player_id"], "name": p.get("display_name") or p.get("name", "")}
                for p in players_raw]

        # Safety: drop any entries that somehow still lack a name
        players = [p for p in players if p["name"]]

        # Sort (stable)
        players.sort(key=lambda x: (x["name"], x["player_id"]))
        
        # st.subheader(":material/groups_2: Register Attendance")

        # show_all = st.toggle(
        #     "Show all session dates",
        #     value=False,
        #     help="Temporarily list all sessions to backfill absences."
        # )

        # fetch_limit = None if show_all else 6  # None => no cap

        # recent_sessions = mongo.get_recent_sessions(
        #     team=team,
        #     limit=fetch_limit,
        #     up_to_date=date.today()
        # )

        # # Deduplicate by date (keep the latest per day)
        # seen_dates = set()
        # date_to_session = {}
        # for s in sorted(recent_sessions, key=lambda x: _to_date(x.get("date")), reverse=True):
        #     d = _to_date(s.get("date"))
        #     if d not in seen_dates:
        #         seen_dates.add(d)
        #         date_to_session[d] = s
        #     if not show_all and len(date_to_session) >= 6:
        #         break

        # if not date_to_session:
        #     st.warning("No usable session dates found.")
        #     return

        # all_dates_desc = sorted(date_to_session.keys(), reverse=True)
        # # Default to today if present; otherwise the most recent date
        # default_idx = 0
        # if date.today() in date_to_session:
        #     default_idx = all_dates_desc.index(date.today())

        # date_labels = [_ddmmyyyy(d) for d in all_dates_desc]
        # selected_label = st.selectbox("Session date (dd/mm/yyyy)", options=date_labels, index=default_idx, width=200)
        # selected_date = all_dates_desc[date_labels.index(selected_label)]
        # session = date_to_session[selected_date]
        # session_id = session.get("session_id")

        # # --- ROSTER -------------------------------------------------------------
        # try:
        #     roster = mongo.get_roster_players(team=team)
        # except Exception as e:
        #     st.error(f"Unable to load roster: {e}")
        #     return

        # if not roster:
        #     st.warning("No players found for this team.")
        #     return

        # # Normalize and sort players for stable UI
        # players = []
        # for p in roster:
        #     pid = p.get("player_id")
        #     try:
        #         pid = int(pid)
        #     except Exception:
        #         pass
        #     name = f"{p.get('player_last_name', p.get('last_name','')).upper()}, {p.get('player_first_name', p.get('first_name',''))}".strip(", ")
        #     players.append({"player_id": pid, "name": name})
        # players.sort(key=lambda x: x["name"])

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
        st.subheader(":material/person_off: Absentees & Reasons")
        st.caption("Pick a reason for each player not selected as present.")

        absentee_reasons: Dict[int, str] = {}
        reason_labels = [r["label"] for r in ABSENCE_REASONS]
        by_label = {r["label"]: r for r in ABSENCE_REASONS}

        if absentees:
            for p in absentees:
                pid = p["player_id"]
                # Use the player's name as the label for a compact UI
                absentee_reasons[pid] = st.selectbox(
                    label=p["name"],
                    options=reason_labels,
                    index=0,
                    key=f"abs_{session_id}_{pid}",
                    width=200
                )
        else:
            st.info("All players are marked present. No absentees to register.")

        # --- SAVE (ONE STEP) ----------------------------------------------------
        if st.button("Save attendance", type="primary", icon=":material/save:"):
            absent_items = [{"player_id": int(pid), "reason": reason} for pid, reason in absentee_reasons.items()]
            try:
                mongo.upsert_attendance_full(
                    session_id=session_id,
                    team=team,
                    present_ids=[int(x) for x in present_ids],
                    absent_items = [
                        {"player_id": int(pid), "reason": by_label[label]["id"]}
                        for pid, label in absentee_reasons.items()
                    ],
                    user=user if isinstance(user, str) else getattr(user, "name", str(user))
                )
                # selected_label is the dd/mm/yyyy string from the session date dropdown
                st.success(f"Attendance saved for {selected_label} — {team}.", icon=":material/check_box:")
            except Exception as e:
                st.error(f"Failed to save attendance: {e}", icon=":material/error_outline:")

    with tab2:
        st.subheader(":material/table_chart: Attendance Overview")

        # Controls (optional): show all dates or cap to last N
        col_a, col_b = st.columns([1, 1])
        with col_a:
            show_all = st.toggle("Show all session dates", value=False)
        with col_b:
            last_n = st.number_input("Limit to last N dates (ignored if 'Show all' is on)", min_value=1, max_value=52, value=12, step=1)

        limit = None if show_all else int(last_n)

        try:
            df_overview = build_attendance_overview_df(
                mongo=mongo,
                team=team,
                up_to=date.today(),
                limit=limit,
                absence_meta=ABSENCE_REASONS,
            )

            if df_overview.empty:
                st.info("No attendance found yet.")
            else:
                # Map full date -> short label "dd/mm", keep year in tooltip (help)
                def _to_short_label(full_str: str) -> str:
                    try:
                        dt = datetime.strptime(full_str, "%d/%m/%Y")
                        return dt.strftime("%d/%m")
                    except Exception:
                        # Fallback: if the column wasn't a full date string for some reason
                        return full_str

                column_config = {
                    col: st.column_config.Column(
                        label=_to_short_label(col),  # shown label (dd/mm)
                        help=col,                    # tooltip keeps dd/mm/yyyy
                        width="small",
                        #align="center",              # center the emoji in the cell
                    )
                    for col in df_overview.columns
                }

                st.data_editor(
                    df_overview,
                    use_container_width=True,
                    height=get_table_height(len(df_overview)),
                    column_config=column_config,
                    disabled=True,
                )

                st.caption(
                    "Legend: "
                    f"{PRESENT_EMOJI} present  ·  "
                    + "  ·  ".join([f"{r.get('emoji','')} {r['label']}" for r in ABSENCE_REASONS])
                    + f"  ·  {UNKNOWN_EMOJI} no entry"
                )

        except Exception as e:
            st.error(f"Failed to build overview: {e}")

    with tab3:
        st.subheader(":material/timer: Register Match Minutes")

        # Always list all matches for simplicity
        match_session, match_label = _select_session_by_date(
            mongo=mongo,
            team=team,
            title="Match date",
            show_all=True,
            max_dates=999,
            up_to=date.today(),
            session_type="M",
        )
        if not match_session:
            st.info("No matches found for this team.")
            return

        match_session_id = match_session.get("session_id")

        # Fetch players from the new helper; it returns {"player_id", "display_name", ...}
        players_raw = mongo.get_player_names(team=team, style="LAST_FIRST")

        # Normalize so the rest of the UI can use p["name"]
        players = [{"player_id": p["player_id"], "name": p.get("display_name") or p.get("name", "")}
                for p in players_raw]

        # Safety: drop any entries that somehow still lack a name
        players = [p for p in players if p["name"]]

        # Sort (stable)
        players.sort(key=lambda x: (x["name"], x["player_id"]))

        st.caption("Enter minutes played for each player in the selected match.")
        col_left, col_right = st.columns(2)
        minutes_input: Dict[int, int] = {}
        for i, pl in enumerate(players):
            container = col_left if i % 2 == 0 else col_right
            with container:
                minutes_input[pl["player_id"]] = st.number_input(
                    label=pl["name"],
                    min_value=0, max_value=120,
                    value=0, step=1,
                    key=f"mm_{match_session_id}_{pl['player_id']}"
                )

        if st.button("Save match minutes", type="primary", icon=":material/save:"):
            payload = [{"player_id": int(pid), "minutes": int(val)} for pid, val in minutes_input.items()]
            try:
                mongo.save_match_minutes_once(
                    session_id=match_session_id,
                    team=team,
                    minutes_items=payload,
                    user=user if isinstance(user, str) else getattr(user, "name", str(user))
                )
                st.success(f"Match minutes saved for {match_label} — {team}.")
            except Exception as e:
                st.error(f"Failed to save match minutes: {e}")

    with tab4:
        st.subheader(":material/table_chart: Match Minutes Overview")

        st.write("Under construction... coming soon!")  