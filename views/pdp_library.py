import streamlit as st
from datetime import datetime
from utils.pdf_utils import generate_pdp_pdf
from utils.team_selector import team_selector
from utils.constants import TEAMS
from db.mongo_wrapper import DatabaseError

def render(mongo, user):
    st.title(":material/folder: PDP Archive")

    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return
    
    # --- Load roster ---
    players = mongo.get_player_names(team=team, style="LAST_FIRST")
    if not players:
        st.warning("No players found in roster.")
        return

    # --- Player selection ---
    player_lookup = {p["display_name"]: p for p in players}
    selected_name = st.selectbox("Select a player", list(player_lookup.keys()))
    player = player_lookup[selected_name]
    player_id = player["player_id"]

    # --- Fetch PDPs from DB ---
    pdps = mongo.get_all_pdps_for_player(player_id)

    if not pdps:
        st.info("No PDPs found for this player.")
        return

    # --- Sort by creation date descending ---
    pdps = sorted(pdps, key=lambda x: x["created"], reverse=True)

    # --- Display PDPs ---
    st.markdown(f"### PDPs for {selected_name}")

    for i, pdp in enumerate(pdps):
        created_dt = datetime.fromisoformat(pdp["created"])
        created_by = pdp.get("created_by", "Unknown")
        pdf_buffer = generate_pdp_pdf(pdp, selected_name)

        with st.expander(f"📄 {created_dt.strftime('%Y-%m-%d')} — by {created_by}"):
            st.download_button(
                label=":material/download: Download as PDF",
                data=pdf_buffer,
                file_name=f"PDP_{selected_name.replace(', ', '_')}_{created_dt.date()}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            for category, subcats in pdp["data"].items():
                st.subheader(category)
                for subcat, topics in subcats.items():
                    st.markdown(f"**{subcat}**")
                    rows = []
                    for topic, details in topics.items():
                        rows.append({
                            "Topic": topic,
                            "Score": details["score"],
                            "Priority": "✅" if details["priority"] else "",
                            "Comment": details.get("comment", "")
                        })
                    st.dataframe(rows, use_container_width=True, hide_index=True)