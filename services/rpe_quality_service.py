# services/rpe_quality_service.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
import pandas as pd

def _get_exempt_ids(override: Optional[List[str]] = None) -> List[str]:
    if override is not None:
        return [str(x) for x in override]
    try:
        from utils.constants import EXEMPT
        return [str(x) for x in (EXEMPT or [])]
    except Exception:
        return []

def season_rpe_quality(
    mongo,  # db.mongo_wrapper.MongoWrapper
    team: str,
    exempt_player_ids: Optional[List[str]] = None,
    timestamp_window_days: int = 1,
) -> Dict[str, Any]:
    """Season-wide RPE data quality for a team.

    Checks:
      - Compliance per player (expected = # team sessions)
      - Duplicates: (player_id + session_id) and (player_id + date) if session_id missing
      - Anomalies: missing_session_id, orphan_session_id, timestamp_out_of_window
      - Weekly team cumulative compliance trend
    """
    exempt = set(_get_exempt_ids(exempt_player_ids))

    # --- Load base tables
    sessions = mongo.get_sessions_df(team=team).copy()
    if not sessions.empty:
        sessions["date"] = pd.to_datetime(sessions["date"], errors="coerce")
        if "weeknumber" not in sessions.columns or sessions["weeknumber"].isna().any():
            sessions["weeknumber"] = sessions["date"].dt.isocalendar().week.astype(int)
    n_sessions = 0 if sessions.empty else len(sessions)

    roster = mongo.get_roster_df()
    roster = roster[roster["team"] == team].copy()
    if roster.empty:
        roster = pd.DataFrame(columns=["player_id", "player_name"])
    else:
        roster["player_id"] = roster["player_id"].astype(str)
        roster["player_name"] = (
            roster["player_last_name"].astype(str).str.strip() + ", " +
            roster["player_first_name"].astype(str).str.strip()
        ).str.strip(", ")

    rpe = mongo.get_player_rpe_df()
    if not rpe.empty:
        rpe["player_id"] = rpe["player_id"].astype(str)
        for col in ("date", "timestamp"):
            if col in rpe.columns:
                rpe[col] = pd.to_datetime(rpe[col], errors="coerce")

    # --- Join RPE ↔ sessions (left) to add team/date/week
    if not rpe.empty and not sessions.empty:
        sess_join = sessions[["session_id", "date", "weeknumber", "team"]].rename(
            columns={"date": "session_date", "team": "session_team"}
        )
        rpe = rpe.merge(sess_join, on="session_id", how="left")
    elif not rpe.empty:
        rpe["session_date"] = pd.NaT
        rpe["weeknumber"] = pd.NA
        rpe["session_team"] = pd.NA

    # Team-only RPE (exclude orphans for compliance)
    rpe_team = pd.DataFrame(columns=rpe.columns) if rpe.empty else rpe[rpe["session_team"] == team].copy()

    # --- Compliance per player
    if rpe_team.empty:
        actuals = pd.DataFrame(columns=["player_id", "actual"])
    else:
        actuals = rpe_team.groupby("player_id").size().rename("actual").reset_index()

    players = roster[["player_id", "player_name"]].drop_duplicates()
    if players.empty and not actuals.empty:
        players = actuals[["player_id"]].copy()
        players["player_name"] = players["player_id"]

    compliance = players.copy()
    compliance["expected"] = n_sessions
    compliance = compliance.merge(actuals, on="player_id", how="left")
    compliance["actual"] = compliance["actual"].fillna(0).astype(int)
    compliance.loc[compliance["player_id"].isin(exempt), "expected"] = 0

    def pct(e, a):
        if e > 0:
            return round(100.0 * a / e, 1)
        return 100.0 if a == 0 else 0.0

    compliance["compliance_pct"] = [pct(e, a) for e, a in zip(compliance["expected"], compliance["actual"])]
    compliance_df = compliance[["player_id", "player_name", "expected", "actual", "compliance_pct"]]\
        .sort_values(["compliance_pct", "actual"], ascending=[True, True]).reset_index(drop=True)

    mask_expected = compliance_df["expected"] > 0
    team_comp = float(compliance_df.loc[mask_expected, "compliance_pct"].mean()) if mask_expected.any() else 100.0

    # --- Duplicates (on all RPE, including orphans)
    dup_frames = []
    if not rpe.empty:
        has_sid = rpe["session_id"].notna() & (rpe["session_id"].astype(str) != "")
        if has_sid.any():
            d1 = rpe.loc[has_sid].groupby(["player_id", "session_id"]).size().rename("count").reset_index()
            d1 = d1[d1["count"] > 1]
            if not d1.empty:
                d1["key_type"] = "player_id+session_id"
                d1["date"] = pd.NaT
                dup_frames.append(d1[["key_type", "player_id", "session_id", "date", "count"]])
        no_sid = ~has_sid
        if no_sid.any() and "date" in rpe.columns:
            tmp = rpe.loc[no_sid].copy()
            tmp["date_only"] = pd.to_datetime(tmp["date"], errors="coerce").dt.date
            d2 = tmp.groupby(["player_id", "date_only"]).size().rename("count").reset_index()
            d2 = d2.rename(columns={"date_only": "date"})
            d2 = d2[d2["count"] > 1]
            if not d2.empty:
                d2["key_type"] = "player_id+date"
                d2["session_id"] = None
                dup_frames.append(d2[["key_type", "player_id", "session_id", "date", "count"]])

    duplicates_df = pd.concat(dup_frames, ignore_index=True) if dup_frames else \
        pd.DataFrame(columns=["key_type", "player_id", "session_id", "date", "count"])
    n_duplicates = int(duplicates_df["count"].sum()) if not duplicates_df.empty else 0

    # --- Anomalies (minimal)
    if rpe.empty:
        anomalies_df = pd.DataFrame(columns=[
            "player_id","session_id","date","timestamp",
            "missing_session_id","orphan_session_id","timestamp_out_of_window"
        ])
        n_anomalies = 0
    else:
        A = rpe.copy()
        A["missing_session_id"] = A["session_id"].isna() | (A["session_id"].astype(str) == "")
        A["orphan_session_id"] = (~A["missing_session_id"]) & (A["session_date"].isna())

        def ts_out(row) -> bool:
            sd, ts = row.get("session_date"), row.get("timestamp")
            if pd.notna(sd) and pd.notna(ts):
                sd = pd.to_datetime(sd).normalize()
                lo = sd - pd.Timedelta(days=timestamp_window_days)
                hi = sd + pd.Timedelta(days=timestamp_window_days, hours=23, minutes=59, seconds=59)
                return not (lo <= ts <= hi)
            return False

        A["timestamp_out_of_window"] = A.apply(ts_out, axis=1)

        anomalies_df = A[[
            "player_id","session_id","date","timestamp",
            "missing_session_id","orphan_session_id","timestamp_out_of_window"
        ]].reset_index(drop=True)
        n_anomalies = int(
            anomalies_df[["missing_session_id","orphan_session_id","timestamp_out_of_window"]].any(axis=1).sum()
        )

    # --- Weekly cumulative team compliance trend
    if sessions.empty:
        weekly_team = pd.DataFrame(columns=["weeknumber", "team_compliance_pct"])
    else:
        weeks = sorted(sessions["weeknumber"].dropna().astype(int).unique())
        sess_per_week = sessions.groupby("weeknumber").size().rename("sessions_in_week")
        cum_expected = sess_per_week.reindex(weeks, fill_value=0).cumsum()

        if rpe_team.empty:
            actual_pw = pd.DataFrame(columns=["player_id", "weeknumber", "actual_in_week"])
        else:
            rpe_team["weeknumber"] = rpe_team["weeknumber"].astype("Int64")
            miss = rpe_team["weeknumber"].isna()
            if miss.any():
                rpe_team.loc[miss, "weeknumber"] = rpe_team.loc[miss, "session_date"].dt.isocalendar().week.astype("Int64")
            actual_pw = (
                rpe_team.dropna(subset=["weeknumber"])
                .assign(weeknumber=lambda d: d["weeknumber"].astype(int))
                .groupby(["player_id", "weeknumber"]).size().rename("actual_in_week").reset_index()
            )

        players_idx = players["player_id"].unique().tolist()
        grid = pd.MultiIndex.from_product([players_idx, weeks], names=["player_id", "weeknumber"])
        tmp = pd.DataFrame(index=grid).reset_index()
        tmp = tmp.merge(actual_pw, on=["player_id", "weeknumber"], how="left")
        tmp["actual_in_week"] = tmp["actual_in_week"].fillna(0)
        tmp["actual_cum"] = tmp.groupby("player_id")["actual_in_week"].cumsum()
        tmp = tmp.merge(cum_expected.rename("expected_cum").reset_index(), on="weeknumber", how="left")

        tmp["expected_cum"] = tmp.apply(lambda r: 0 if r["player_id"] in exempt else r["expected_cum"], axis=1)

        def c_pct(e, a):
            if e > 0:
                return round(100.0 * a / e, 1)
            return 100.0 if a == 0 else 0.0

        tmp["compliance_pct"] = [c_pct(e, a) for e, a in zip(tmp["expected_cum"], tmp["actual_cum"])]

        weekly_team = (
            tmp[tmp["expected_cum"] > 0]
            .groupby("weeknumber")["compliance_pct"]
            .mean()
            .rename("team_compliance_pct")
            .reset_index()
            .sort_values("weeknumber")
        )

    summary = {
        "team_compliance_pct": round(team_comp, 1),
        "n_sessions_in_season": int(n_sessions),
        "n_duplicates": int(n_duplicates),
        "n_anomalies": int(n_anomalies),
        "season_weeks": weekly_team["weeknumber"].tolist() if not weekly_team.empty else [],
    }

    return {
        "compliance_df": compliance_df,
        "duplicates_df": duplicates_df,
        "anomalies_df": anomalies_df,
        "weekly_team_compliance_df": weekly_team,
        "summary": summary,
    }