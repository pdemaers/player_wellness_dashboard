# views/admin_data_quality_rpe.py
import streamlit as st
from services.rpe_quality_service import season_rpe_quality

def render(mongo):
    """
    Render the **RPE Data Quality** admin view in the Streamlit app.

    This page is only meant for users with **admin access**.
    It provides tools to evaluate the data quality of RPE registrations
    across the entire season for a selected team.

    Key features:
        - **Team selector**: Switch between U18 / U21 squads.
        - **Exempt players**: Automatically excludes long-term injured or absent
          players based on the constants.EXEMPT list. Trainers can override this
          list manually from the UI if needed.
        - **Summary metrics**: Displays the overall compliance rate, the number
          of team sessions, duplicates, and anomaly rows.
        - **Compliance analysis**:
            * Player-level compliance table (expected vs. actual RPE entries).
            * Cumulative team compliance trend per training week.
        - **Data quality checks**:
            * Duplicate RPE entries per player (based on session_id or date).
            * Anomalies such as missing session links, orphan session IDs, or
              timestamps that fall outside the allowed session window.
        - **Exports**: Admins can download compliance, duplicates, and anomaly
          tables as CSV for reporting or offline analysis.

    Args:
        mongo (MongoWrapper):
            Database wrapper instance used to fetch roster, sessions, and
            player RPE registrations. Passed down from the app entrypoint.

    Raises:
        StreamlitAPIException:
            If called outside a Streamlit context.
        DatabaseError:
            If underlying database queries fail.

    Example:
        >>> from db.mongo_wrapper import MongoWrapper
        >>> mongo = MongoWrapper()
        >>> render(mongo)
    """
    st.header("🧹 Data Quality — RPE (Season)")
    team = st.segmented_control("Team", ["U18", "U21"], default="U21", key="dq_team")

    use_override = st.checkbox("Override EXEMPT list?", value=False)
    override = st.text_input("Exempt player IDs (comma separated)", value="") if use_override else ""
    exempt_ids = [x.strip() for x in override.split(",") if x.strip()] if use_override else None

    res = season_rpe_quality(mongo, team=team, exempt_player_ids=exempt_ids)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Team Compliance %", res["summary"]["team_compliance_pct"])
    c2.metric("# Sessions (season)", res["summary"]["n_sessions_in_season"])
    c3.metric("# Duplicates", res["summary"]["n_duplicates"])
    c4.metric("# Anomaly Rows", res["summary"]["n_anomalies"])

    st.subheader("Cumulative Compliance Trend (Team)")
    wk = res["weekly_team_compliance_df"]
    st.line_chart(wk.set_index("weeknumber")["team_compliance_pct"]) if not wk.empty else st.info("No sessions yet.")

    st.subheader("Player Compliance")
    st.dataframe(res["compliance_df"], use_container_width=True, hide_index=True)

    st.subheader("Duplicates")
    st.dataframe(res["duplicates_df"], use_container_width=True, hide_index=True) if not res["duplicates_df"].empty else st.success("No duplicates 🎉")

    st.subheader("Anomalies")
    st.dataframe(res["anomalies_df"], use_container_width=True, hide_index=True) if not res["anomalies_df"].empty else st.success("No anomaly rows 🎉")

    # CSV exports
    st.download_button("Download Compliance (CSV)", res["compliance_df"].to_csv(index=False), file_name=f"rpe_compliance_{team}_season.csv", mime="text/csv")
    st.download_button("Download Duplicates (CSV)", res["duplicates_df"].to_csv(index=False), file_name=f"rpe_duplicates_{team}_season.csv", mime="text/csv")
    st.download_button("Download Anomalies (CSV)", res["anomalies_df"].to_csv(index=False), file_name=f"rpe_anomalies_{team}_season.csv", mime="text/csv")