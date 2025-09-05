import streamlit as st
from datetime import datetime
from copy import deepcopy
import pandas as pd
import uuid
from utils.ui_utils import get_table_height
from utils.team_selector import team_selector
from utils.constants import TEAMS

def render(mongo, user):
    st.title(":material/fact_check: PDP Structure Management")
    st.subheader("Edit the Personal Development Plan (PDP) structure per team.")

    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    structure_doc = mongo.get_pdp_structure_for_team(team)
    if not structure_doc:
        st.warning(f"No structure found for {team}. Initializing empty structure.")
        structure_doc = {
            "_id": f"{team}_structure",
            "version": 1,
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "structure": {}
        }

    structure = deepcopy(structure_doc["structure"])

    # Ensure topic_id exists for all topics
    for cat in structure:
        for subcat in structure[cat]:
            for topic in structure[cat][subcat]:
                if "topic_id" not in topic:
                    topic["topic_id"] = str(uuid.uuid4())

    selected_category = st.selectbox("Select category", list(structure.keys()) or ["—"])
    if selected_category and selected_category != "—":
        selected_subcategory = st.selectbox(
            "Select subcategory", list(structure[selected_category].keys()) or ["—"]
        )

        if selected_subcategory and selected_subcategory != "—":
            st.subheader(f":material/edit_note: Manage topics in **{selected_subcategory}**")

            current_topics = structure[selected_category][selected_subcategory]

            # Build map of name -> topic_id
            id_map = {t["name"]: t["topic_id"] for t in current_topics}

            # Show only name and active in UI
            df = pd.DataFrame([
                {
                    "name": t["name"],
                    "active": t["active"]
                } for t in current_topics
            ])

            edited_df = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "name": st.column_config.TextColumn("Topic name"),
                    "active": st.column_config.CheckboxColumn("Active")
                },
                height=get_table_height(len(df)),
                hide_index=True,
                key="topic_editor"
            )

            # Detect hard deletes and convert to soft deletes
            old_topic_names = {t["name"] for t in current_topics}
            new_topic_names = set(edited_df["name"])

            updated_topics = []
            for _, row in edited_df.iterrows():
                name = row["name"].strip()
                topic_id = id_map.get(name, str(uuid.uuid4()))
                updated_topics.append({
                    "topic_id": topic_id,
                    "name": name,
                    "active": bool(row["active"])
                })

            # Soft-delete removed topics
            removed_names = old_topic_names - new_topic_names
            for t in current_topics:
                if t["name"] in removed_names:
                    updated_topics.append({
                        "topic_id": t["topic_id"],
                        "name": t["name"],
                        "active": False
                    })

            structure[selected_category][selected_subcategory] = updated_topics

    #st.markdown("---")

    if st.button("Save PDP Structure", type="primary", icon=":material/save:"):
        updated_doc = {
            **structure_doc,
            "structure": structure,
            "version": structure_doc.get("version", 1) + 1,
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        success = mongo.update_pdp_structure_for_team(team, updated_doc)
        if success:
            st.success("Structure updated successfully!", icon=":material/check_circle:")
        else:
            st.error("Failed to update structure.", icon=":material/error:")