import streamlit as st
import pandas as pd
from datetime import date

from utils.team_selector import team_selector
from utils.constants import TEAMS

from db.repositories.session_dashboard_repo import (
    get_session_rpe_aggregates_df,
    get_rpe_joined_per_session_df,
    DatabaseError,
)
from charts.session_dashboard_graphs import (
    rpe_boxplot_per_session,
    rpe_outliers_table,
    bar_avg_load_per_type,
    stacked_load_per_week,
    stacked_pct_load_per_week,
)


# ✅ Underscore the unhashable argument here
@st.cache_data(show_spinner=False)
def _load_aggregates(_mongo, team: str) -> pd.DataFrame:
    return get_session_rpe_aggregates_df(_mongo, team)


@st.cache_data(show_spinner=False)
def _load_rpe_per_session(_mongo, team: str, use_range: bool, dt_from: date | None, dt_to: date | None) -> pd.DataFrame:
    return get_rpe_joined_per_session_df(_mongo, team, dt_from if use_range else None, dt_to if use_range else None)


def render(mongo, user):
    st.title(":material/timer: Session RPE Dashboard")

    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        use_range = st.toggle("Filter by date range", value=False)
    with c2:
        dt_from = st.date_input("From", value=date.today(), disabled=not use_range)
    with c3:
        dt_to = st.date_input("To", value=date.today(), disabled=not use_range)

    try:
        # ✅ You still call with `mongo` here
        agg_df = _load_aggregates(mongo, team)
        rpe_df = _load_rpe_per_session(mongo, team, use_range, dt_from, dt_to)
    except DatabaseError as e:
        st.error(str(e), icon=":material/error:")
        return
    except Exception as e:
        st.error(f"Unexpected error: {e}", icon=":material/error:")
        return

    # ---- Charts: Boxplot (new) --------------------------------------------
    st.subheader(":material/stacked_bar_chart: RPE Distribution per Session")
    if rpe_df.empty:
        st.info("No per-session RPE data for the selected filters.")
    else:
        st.plotly_chart(
            rpe_boxplot_per_session(rpe_df, title=f"RPE Distribution per Session ({team})"),
            use_container_width=True
        )

    # ---- Charts: your existing KPIs ---------------------------------------
    st.subheader(":material/bar_chart: Average Load per Session Type")
    if agg_df.empty:
        st.info("No aggregate data found.")
        return

    st.plotly_chart(
        bar_avg_load_per_type(agg_df, title="Average Load per Session Type"),
        use_container_width=True
    )

    st.subheader(":material/stacked_bar_chart: Load Distribution by Session Type (per Week)")
    st.plotly_chart(
        stacked_load_per_week(agg_df, title="Load Distribution by Session Type (per Week)"),
        use_container_width=True
    )

    st.subheader(":material/percent: Relative Load Distribution by Session Type per Week (100% Stacked)")
    st.plotly_chart(
        stacked_pct_load_per_week(agg_df, title="Relative Load Distribution by Session Type per Week (100% Stacked)"),
        use_container_width=True
    )

    # ---- Outliers table ----------------------------------------------------
    st.subheader(":material/flag: RPE Outliers per Session (IQR × 1.5)")
    if rpe_df.empty:
        st.info("No outliers to display.")
    else:
        out = rpe_outliers_table(rpe_df, iqr_k=1.5)
        if out.empty:
            st.success("No outliers detected.")
        else:
            st.dataframe(
                out.sort_values(["date", "session_type", "session_id", "player_id"]),
                use_container_width=True,
                height=400
            )