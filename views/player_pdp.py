import streamlit as st
import pandas as pd
from datetime import datetime
from copy import deepcopy
from streamlit.column_config import TextColumn, SelectboxColumn, CheckboxColumn

from utils.ui_utils import get_table_height
from utils.team_selector import team_selector
from utils.constants import TEAMS  # e.g., ["U18", "U21"]

from db.errors import DatabaseError, ApplicationError  # if you surface errors

def render(mongo, user):
    st.title(":material/portrait: Create New Player PDP")

    # --- TEAM SELECTOR ---
    team = team_selector(TEAMS, widget_key="pdp_team_selector", session_key="pdp_selected_team")
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    # --- Load roster (standardized) ---
    try:
        roster = mongo.get_player_names(team=team, style="LAST_FIRST", include_inactive=True)
    except (DatabaseError, ApplicationError) as e:
        st.error(f"Failed to load roster: {e}")
        return

    if not roster:
        st.warning(f"No players found in roster for {team}.")
        return

    player_lookup = {p["display_name"]: p for p in roster}

    # --- Prepare form session state safely ---
    if "pdp_form_data" not in st.session_state:
        st.session_state["pdp_form_data"] = {}

    form_data = deepcopy(st.session_state["pdp_form_data"])

    col1, col2 = st.columns([4, 2])
    with col1:
        selected_name = st.selectbox("Select player", list(player_lookup.keys()), label_visibility="collapsed")
        player = player_lookup[selected_name]
        player_id = int(player["player_id"])

    with col2:
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("Start fresh", use_container_width=True, icon=":material/add_circle_outline:"):
                st.session_state["pdp_form_data"] = {}
                st.rerun()
        with bcol2:
            if st.button("Load last", use_container_width=True, icon=":material/file_open:"):
                try:
                    latest = mongo.get_latest_pdp_for_player(player_id)
                except (DatabaseError, ApplicationError) as e:
                    st.error(f"Failed to load latest PDP: {e}")
                    latest = None

                if latest and latest.get("payload"):
                    st.session_state["pdp_form_data"] = latest["payload"]
                    st.success("Last PDP loaded as starting point.")
                else:
                    st.info("No previous PDP found.")
                st.rerun()

    # --- Load team PDP structure ---
    try:
        structure_doc = mongo.get_pdp_structure_for_team(team)
    except (DatabaseError, ApplicationError) as e:
        st.error(f"Failed to load PDP structure: {e}")
        return

    if not structure_doc or "structure" not in structure_doc:
        st.error(f"No PDP structure found for team {team}")
        return

    structure = structure_doc["structure"]

    # --- PDP Form ---
    with st.form("pdp_form"):
        tabs = st.tabs(list(structure.keys()))

        for i, category in enumerate(structure):
            with tabs[i]:
                st.subheader(category)

                if category not in form_data:
                    form_data[category] = {}

                # subcategories inside the category
                for subcat, topics in structure[category].items():
                    # only active topics
                    active_topics = [t for t in topics if t.get("active")]
                    if not active_topics:
                        continue

                    st.markdown(f"**{subcat}**")
                    if subcat not in form_data[category]:
                        form_data[category][subcat] = {}

                    # build editable table rows
                    rows = []
                    for topic in active_topics:
                        topic_name = topic["name"]
                        current = form_data[category][subcat].get(
                            topic_name, {"score": 3, "priority": False, "comment": ""}
                        )
                        rows.append({
                            "topic": topic_name,
                            "score": current.get("score", 3),
                            "priority": bool(current.get("priority", False)),
                            "comment": current.get("comment", ""),
                        })

                    # score mapping for UI labels
                    label_to_score = {
                        "1 - Poor": 1,
                        "2 - Fair": 2,
                        "3 - Good": 3,
                        "4 - Very Good": 4,
                        "5 - Excellent": 5,
                    }
                    score_to_label = {v: k for k, v in label_to_score.items()}

                    # present scores as labels in the editor
                    for row in rows:
                        row["score"] = score_to_label.get(row["score"], "3 - Good")

                    df = pd.DataFrame(rows)
                    edited_df = st.data_editor(
                        df,
                        key=f"editor_{team}_{player_id}_{category}_{subcat}",
                        use_container_width=True,
                        column_config={
                            "topic": TextColumn("Topic", disabled=True, width="large"),
                            "score": SelectboxColumn("Score (1–5)", options=list(label_to_score.keys()), width="medium"),
                            "priority": CheckboxColumn("Priority", width="small"),
                            "comment": TextColumn("Comment", width="large"),
                        },
                        height=get_table_height(len(df)),
                        hide_index=True,
                    )

                    # map labels back to numeric
                    edited_df["score"] = edited_df["score"].map(label_to_score)

                    # persist into form_data (session_state-backed)
                    for _, row in edited_df.iterrows():
                        form_data[category][subcat][row["topic"]] = {
                            "score": int(row["score"]),
                            "priority": bool(row["priority"]),
                            "comment": str(row["comment"]).strip(),
                        }

        # --- Save PDP ---
        submitted = st.form_submit_button("Save PDP", type="primary", icon=":material/save:")
        if submitted:
            try:
                now = datetime.utcnow()
                created_by = user if isinstance(user, str) else getattr(user, "name", str(user))

                new_pdp = {
                    "player_id": player_id,
                    "team": team,
                    "created_at": now,
                    "last_updated": now,
                    "created_by": created_by,
                    "last_updated_by": created_by,
                    "payload": form_data,
                }

                _id = mongo.insert_new_pdp(new_pdp)
                st.success(f"PDP saved successfully (id: {_id}).", icon=":material/check_circle:")
                st.session_state["pdp_form_data"] = form_data

            except (DatabaseError, ApplicationError) as e:
                st.error(f"Failed to save PDP: {e}", icon=":material/error_outline:")