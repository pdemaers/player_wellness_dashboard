import streamlit as st
from datetime import datetime
from copy import deepcopy
import pandas as pd
from streamlit.column_config import TextColumn, SelectboxColumn, CheckboxColumn
from utils.ui_utils import get_table_height

def render(mongo, user):
    st.title(":material/portrait: Create New Player PDP")

    # --- Load roster ---
    roster = mongo.get_roster_players("U18")
    if not roster:
        st.warning("No players found in roster.")
        return

    player_lookup = {f"{p['player_last_name']}, {p['player_first_name']}": p for p in roster}
    # selected_name = st.selectbox("Select a player", list(player_lookup.keys()))
    # player = player_lookup[selected_name]
    # player_id = player["player_id"]
    # team = player["team"]

    # --- Prepare form data safely ---
    if "pdp_form_data" not in st.session_state:
        st.session_state["pdp_form_data"] = {}

    form_data = deepcopy(st.session_state["pdp_form_data"])

    col1, col2, col3 = st.columns([4, 1, 1])

    with col1:
        selected_name = st.selectbox("Select a player", list(player_lookup.keys()))
        player = player_lookup[selected_name]
        player_id = player["player_id"]
        team = player["team"]

    with col2:
        st.write("")  # lightweight spacer for alignment
        if st.button("Start fresh", icon=":material/add_circle_outline:"):
            st.session_state["pdp_form_data"] = {}
            st.rerun()

    with col3:
        st.write("")  # lightweight spacer for alignment
        if st.button("Load last", icon=":material/file_open:"):
            latest = mongo.get_latest_pdp_for_player(player_id)
            if latest:
                st.session_state["pdp_form_data"] = latest["data"]
                st.success("Last PDP loaded as starting point.")
            else:
                st.info("No previous PDP found.")
            st.rerun()

    # --- Load team PDP structure ---
    structure_doc = mongo.get_pdp_structure_for_team(team)
    if not structure_doc:
        st.error(f"No PDP structure found for team {team}")
        return

    structure = structure_doc["structure"]

    # --- Form rendering ---
    with st.form("pdp_form"):
        tabs = st.tabs(list(structure.keys()))

        for i, category in enumerate(structure):
            with tabs[i]:
                st.subheader(category)

                if category not in form_data:
                    form_data[category] = {}

                for subcat, topics in structure[category].items():
                    active_topics = [t for t in topics if t["active"]]
                    if not active_topics:
                        continue

                    st.markdown(f"**{subcat}**")

                    if subcat not in form_data[category]:
                        form_data[category][subcat] = {}

                    rows = []
                    for topic in active_topics:
                        topic_name = topic["name"]
                        current = form_data[category][subcat].get(topic_name, {"score": 3, "priority": False, "comment": ""})
                        rows.append({
                            "topic": topic_name,
                            "score": current["score"],
                            "priority": current["priority"],
                            "comment": current.get("comment", "")
                        })

                    label_to_score = {
                        "1 - Poor": 1,
                        "2 - Fair": 2,
                        "3 - Good": 3,
                        "4 - Very Good": 4,
                        "5 - Excellent": 5
                    }
                    score_to_label = {v: k for k, v in label_to_score.items()}

                    for row in rows:
                        row["score"] = score_to_label.get(row["score"], "3 - Good")

                    df = pd.DataFrame(rows)
                    edited_df = st.data_editor(
                        df,
                        key=f"editor_{category}_{subcat}",
                        use_container_width=True,
                        column_config={
                            "topic": TextColumn("Topic", disabled=True, width="large"),
                            "score": SelectboxColumn("Score (1–5)", options=list(label_to_score.keys()), width="medium"),
                            "priority": CheckboxColumn("Priority", width="small"),
                            "comment": TextColumn("Comment", width="large")
                        },
                        height=get_table_height(len(df)),
                        hide_index=True
                    )

                    edited_df["score"] = edited_df["score"].map(label_to_score)

                    for _, row in edited_df.iterrows():
                        form_data[category][subcat][row["topic"]] = {
                            "score": int(row["score"]),
                            "priority": bool(row["priority"]),
                            "comment": row["comment"].strip()
                        }

        # --- Save PDP ---
        submitted = st.form_submit_button("Save PDP")
        if submitted:
            now = datetime.now().isoformat()
            new_pdp = {
                "player_id": player_id,
                "team": team,
                "created": now,
                "last_updated": now,
                "created_by": user,
                "last_updated_by": user,
                "data": form_data
            }
            mongo.insert_new_pdp(new_pdp)
            st.success("✅ PDP saved successfully.")
            st.session_state["pdp_form_data"] = form_data