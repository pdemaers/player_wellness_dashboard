# --- RPE Dashboard Render Function ---
import streamlit as st
import plotly.express as px
import pandas as pd
from utils.ui_utils import get_table_height
from db.mongo_wrapper import DatabaseError
from utils.team_selector import team_selector
from utils.constants import TEAMS

def render(mongo, user):
    st.title(":material/bar_chart: RPE Dashboard")

    team = team_selector(TEAMS)
    if not team:
        st.info("Select a team to continue.", icon=":material/info:")
        return

    tab1, tab2, tab3 = st.tabs([":material/table_chart: Weekly Load Table", ":material/warning: AC ratio table", ":material/all_inclusive: All Entries"])

    def format_acr_with_risk(acr):
        if pd.isna(acr):
            return ""
        if acr < 0.75 or acr > 1.35:
            return f"🔴 {acr:.2f}"
        elif 0.75 <= acr < 0.85 or 1.25 < acr <= 1.35:
            return f"🟠 {acr:.2f}"
        else:
            return f"🟢 {acr:.2f}"

    # --- Tab 1: Weekly Table ---
    with tab1:
        st.subheader(":material/table_chart: Weekly RPE Load Table")
        try:
            df = mongo.get_rpe_loads(team=team)
            if df.empty:
                st.info("No RPE data available.")
                return

            df_display = df.pivot_table(index='player_name', columns='week', values='load', aggfunc='sum').fillna(0).round(2)
            st.dataframe(df_display, use_container_width=True, height=get_table_height(len(df_display)))

        except Exception as e:
            st.error(f"Error loading RPE data: {e}")

    # --- Tab2: AC ratio table ---
    with tab2:  # or tabs[n] depending on your setup
        st.subheader(":material/warning: Acute/Chronic RPE ratio table")
        try:
            acr_df = mongo.get_rpe_loads(team=team)

            if acr_df.empty:
                st.info("No RPE data available.")
            else:
                pivot_df = acr_df.pivot(index="player_name", columns="week", values="acr")
                display_df = pivot_df.applymap(format_acr_with_risk)

                st.dataframe(display_df, use_container_width=True, height=get_table_height(len(display_df)))

        except Exception as e:
            st.error(f"Error loading AC ratios: {e}")

    # --- Tab 3: Player Comparison ---
    with tab3:
        st.subheader(":material/all_inclusive: All RPE Entries")
        try:
            rpe_pivot = mongo.get_daily_rpe_overview(team=team)
            if rpe_pivot.empty:
                st.info("No roster or RPE data available.")
            else:
                # --- Build ISO week options from pivot columns (which are date strings) ---
                # Make sure pandas is imported as pd at the top of the file
                col_dates = pd.to_datetime(rpe_pivot.columns, errors="coerce")

                # Map each column to an ISO week label like "2025-W32"
                week_labels = []
                for d in col_dates:
                    if pd.isna(d):
                        week_labels.append(None)
                    else:
                        iso = d.isocalendar()  # returns (year, week, weekday)
                        week_labels.append(f"{iso.year}-W{int(iso.week):02d}")

                # Build metadata of columns↔weeks
                meta = pd.DataFrame({
                    "col": rpe_pivot.columns,
                    "date": col_dates,
                    "week": week_labels,
                }).dropna(subset=["week"])

                # Unique week labels in chronological order
                unique_weeks = (
                    meta.sort_values("date")
                        .drop_duplicates(subset=["week"])
                        ["week"].tolist()
                )

                if not unique_weeks:
                    st.dataframe(
                        rpe_pivot,
                        use_container_width=True,
                        height=get_table_height(len(rpe_pivot))
                    )
                else:
                    # Default to last 4 weeks (change to [-1:] for only current week)
                    default_weeks = unique_weeks[-1:] if len(unique_weeks) > 4 else unique_weeks

                    selected_weeks = st.multiselect(
                        "Select week(s) to display",
                        options=unique_weeks,
                        default=default_weeks,
                        help="ISO week numbers (Mon–Sun), e.g. 2025-W32."
                    )

                    if not selected_weeks:
                        st.warning("Select one or more weeks to display data.")
                    else:
                        # Columns that belong to the selected weeks, in chronological order
                        cols_to_show = (
                            meta[meta["week"].isin(selected_weeks)]
                            .sort_values("date")["col"]
                            .tolist()
                        )

                        filtered_df = rpe_pivot[cols_to_show] if cols_to_show else rpe_pivot.iloc[:, :0]

                        st.dataframe(
                            filtered_df,
                            use_container_width=True,
                            height=get_table_height(len(filtered_df))
                        )
        except DatabaseError as e:
            st.error(str(e))