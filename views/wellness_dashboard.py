import streamlit as st
import plotly.express as px
from utils.ui_utils import get_table_height
from datetime import datetime, date
import pandas as pd

def render(mongo, user):
    st.title(":material/monitor_heart: Wellness Dashboard")

    team_filter = st.selectbox("Filter by Team", ["All", "U18", "U21"])
    team = None if team_filter == "All" else team_filter

    tab1, tab2, tab3 = st.tabs([":material/today: Today's Check", ":material/date_range: Weekly Averages", ":material/all_inclusive: All entries"])

# --- TAB 1: Pre training check ---
    with tab1:
        try:
            st.subheader(":material/calendar_today: Today's Wellness Check")

            # Use global team value
            if team is None:
                st.info("Please select a team to view today's wellness entries.")
            else:
                # Get wellness entries (player filtering is done inside the wrapper)
                wellness_entries = mongo.get_today_wellness_entries(team)

                # Get roster (only for display mapping)
                roster = mongo.get_roster_players(team=team)
                player_map = {
                    int(p["player_id"]): f"{p['player_last_name']}, {p['player_first_name']}"
                    for p in roster
                }

                # Build DataFrame
                rows = []
                for entry in wellness_entries:
                    pid = entry["player_id"]
                    name = player_map.get(pid, "Unknown")
                    wellness = entry.get("feeling")
                    sleep = entry.get("sleep_hours")
                    timestamp = entry.get("timestamp")

                    # Icons
                    if wellness == 1:
                        w_icon = "🔴"
                    elif wellness in [2, 3]:
                        w_icon = "🟠"
                    elif wellness in [4, 5]:
                        w_icon = "🟢"
                    else:
                        w_icon = "❓"

                    if sleep is None:
                        s_icon = "❓"
                    elif sleep < 5:
                        s_icon = "🔴"
                    elif 5 <= sleep <= 7:
                        s_icon = "🟠"
                    else:
                        s_icon = "🟢"

                    rows.append({
                        "Player": name,
                        "Wellness": f"{w_icon} {wellness}",
                        "Sleep Hours": f"{s_icon} {sleep}",
                        "Submitted At": timestamp.strftime("%H:%M") if timestamp else "—"
                    })

                df = pd.DataFrame(rows)
                if df.empty:
                    st.info("No wellness entries submitted yet today for this team.")
                else:
                    st.dataframe(df, use_container_width=True, height=get_table_height(len(df)))

        except Exception as e:
            st.error(f":material/error: Error loading today's wellness tab: {e}")

    # --- TAB 2: Weekly Matrix ---
    with tab2:
        try:
            df = mongo.get_wellness_matrix(team=team)
            if df.empty:
                st.info("No wellness data found.")
                st.stop()
            df = df.round(2)
            st.dataframe(df, use_container_width=True, height=get_table_height(len(df)), hide_index=True)
        except Exception as e:
            st.error(f":material/error: Error loading wellness data: {e}")

    # --- TAB 3: Daily overview ---
    with tab3:
        st.subheader("📅 Daily Wellness Entry Overview")

        try:
            pivot_df = mongo.get_daily_wellness_overview(team=team)
            if pivot_df.empty:
                st.info("No wellness entries available.")
            else:
                # --- Build ISO week options from pivot columns (which are date strings) ---
                # Parse columns to dates
                col_dates = pd.to_datetime(pivot_df.columns, errors="coerce")

                # Build week labels like "2025-W32" (ISO weeks: Mon–Sun)
                week_labels = []
                for d in col_dates:
                    if pd.isna(d):
                        week_labels.append(None)
                    else:
                        iso = d.isocalendar()  # (year, week, weekday)
                        week_labels.append(f"{iso.year}-W{int(iso.week):02d}")

                # Map columns to week labels
                meta = pd.DataFrame({
                    "col": pivot_df.columns,
                    "date": col_dates,
                    "week": week_labels,
                }).dropna(subset=["week"])

                # Unique weeks ordered by date
                unique_weeks = (
                    meta.sort_values("date")
                        .drop_duplicates(subset=["week"])
                        ["week"].tolist()
                )

                if not unique_weeks:
                    st.info("No dated columns to filter.")
                else:
                    # Default: last 4 weeks (or all if fewer)
                    default_weeks = unique_weeks[-4:] if len(unique_weeks) > 4 else unique_weeks

                    selected_weeks = st.multiselect(
                        "Select week(s) to display",
                        options=unique_weeks,
                        default=default_weeks,
                        help="ISO week numbers (Mon–Sun), e.g. 2025-W32."
                    )

                    if not selected_weeks:
                        st.warning("Select one or more weeks to display data.")
                    else:
                        # Columns belonging to the selected weeks, keep chronological order
                        cols_to_show = meta[meta["week"].isin(selected_weeks)] \
                            .sort_values("date")["col"].tolist()

                        # Slice pivot to selected columns
                        filtered_df = pivot_df[cols_to_show] if cols_to_show else pivot_df.iloc[:, :0]

                        st.dataframe(
                            filtered_df,
                            use_container_width=True,
                            height=get_table_height(len(filtered_df))
                        )

        except Exception as e:
            st.error(str(e))
