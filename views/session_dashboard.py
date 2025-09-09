import streamlit as st
import pandas as pd
import plotly.express as px
from utils.team_selector import team_selector
from utils.constants import TEAMS

def render(mongo, user):
    st.title(":material/insert_chart: Session RPE Dashboard")

    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    try:
        data = mongo.get_session_rpe_aggregates(team=team)
        if not data:
            st.info("No RPE data found.")
            return

        df = pd.DataFrame(data)
        df["avg_load_per_session"] = df["total_load"] / df["session_count"]
        df["avg_load_per_player"] = df["total_load"] / df["player_count"]
        
        # # Line graph: Total vs Average Player Load per Week
        # weekly_df = df.groupby("week")[["total_load", "avg_load_per_player"]].sum().reset_index()
        # fig1 = px.line(weekly_df, x="week", y=["total_load", "avg_load_per_player"],
        #                markers=True, title="Weekly Load: Total vs Avg Player")
        # st.plotly_chart(fig1, use_container_width=True)

        # Bar graph: Avg Load per Session Type
        type_df = df.groupby("session_type")["avg_load_per_session"].mean().reset_index()
        fig2 = px.bar(type_df, x="session_type", y="avg_load_per_session",
                      title="Average Load per Session Type", color="session_type")
        st.plotly_chart(fig2, use_container_width=True)

        # Stacked bar: Load per Session Type per Week
        stacked_df = df.pivot(index="week", columns="session_type", values="total_load").fillna(0).reset_index()
        fig3 = px.bar(stacked_df, x="week", y=stacked_df.columns[1:], title="Load Distribution by Session Type (per Week)", 
                      labels={"value": "Load", "week": "Week"}, barmode="stack")
        st.plotly_chart(fig3, use_container_width=True)

        # Normalize session type loads as % of weekly total
        stacked_df = df.pivot(index="week", columns="session_type", values="total_load").fillna(0)
        stacked_df["total"] = stacked_df.sum(axis=1)
        stacked_pct_df = stacked_df.div(stacked_df["total"], axis=0).drop(columns="total") * 100
        stacked_pct_df = stacked_pct_df.reset_index().round(1)

        # Melt for plotting
        melted_pct = stacked_pct_df.melt(id_vars="week", var_name="Session Type", value_name="Percentage")

        fig = px.bar(
            melted_pct,
            x="week",
            y="Percentage",
            color="Session Type",
            text="Percentage",
            title="Relative Load Distribution by Session Type per Week (100% Stacked)",
            labels={"week": "Training Week"}
        )

        fig.update_traces(texttemplate="%{text}%", textposition="inside")
        fig.update_layout(barmode="stack", yaxis_title="Percentage (%)")

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading session RPE data: {e}", icon=":material/error:")