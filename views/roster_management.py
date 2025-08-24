import streamlit as st
import pandas as pd
from datetime import datetime
from db.mongo_wrapper import DatabaseError
from utils.ui_utils import get_table_height

# Constants
POSITIONS = ["GK", "CB", "FB", "DMF", "AMF", "HMF", "RW", "LW", "RF", "LF", "CF"]
TEAMS = ["U18", "U21"]

def render(mongo, user):
    st.title(":material/people: Team Roster Editor")
    try:
        # Editor with player_id locked
        df = mongo.get_roster_df()

        edited = st.data_editor(
            df,
            column_config={
                "player_id": st.column_config.NumberColumn("Player ID", required=True, format="%i", disabled=True),
                "player_last_name": st.column_config.TextColumn("Last Name", required=True),
                "player_first_name": st.column_config.TextColumn("First Name", required=True),
                "team": st.column_config.SelectboxColumn("Team", options=TEAMS, required=True)
                # "date_of_birth": st.column_config.DateColumn(
                #     "Date of Birth",
                #     format="DD/MM/YYYY",
                #     min_value=datetime(2000, 1, 1)
                # ),
                # "shirt_nr": st.column_config.NumberColumn("Shirt #", min_value=1, max_value=99),
                # "position": st.column_config.SelectboxColumn("Position", options=POSITIONS),
                # "preferred_foot": st.column_config.SelectboxColumn("Preferred Foot", options=["Left", "Right"])
            },
            height=get_table_height(len(df)), 
            num_rows="dynamic", 
            use_container_width=True)
    except DatabaseError as e :
        st.error(str(e))

    if st.button("Save changes", icon=":material/save:"):
        if mongo.save_roster_df(edited):
            st.success("Roster updated.")
        else:
            st.error(":material/error: Failed to save roster.")