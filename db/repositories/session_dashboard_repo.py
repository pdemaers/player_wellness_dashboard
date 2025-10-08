# db/repositories/sessions_dashboard_repo.py
"""
Session Dashboard Repository.

Centralizes read-only DB access patterns for the session dashboards.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple
from datetime import date as date_cls, datetime, timedelta
import warnings
import pandas as pd
from pymongo.errors import PyMongoError
from db.errors import DatabaseError  # your central error type


def _date_bounds(
    date_from: Optional[date_cls],
    date_to: Optional[date_cls],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert date range to ISO strings for Mongo match (inclusive start, exclusive end).

    Returns:
        (start_iso, end_iso) where end_iso is the day *after* date_to.
    """
    start = datetime.combine(date_from, datetime.min.time()).date().isoformat() if date_from else None
    end = (datetime.combine(date_to, datetime.min.time()) + timedelta(days=1)).date().isoformat() if date_to else None
    return start, end


class SessionsDashboardRepository:
    """
    Read-only queries that power the Sessions dashboard.

    Args:
        mongo: Your MongoWrapper (or compatible) instance. Must expose:
               - .db[<collection>] to access Mongo collections
               - get_session_rpe_aggregates(team=...)  (existing helper)
    """

    def __init__(self, mongo: any):
        self.mongo = mongo

    def get_session_rpe_aggregates_df(self, team: str) -> pd.DataFrame:
        """
        Fetch weekly/session-type aggregates.

        Returns:
            DataFrame with at least: week, session_type, total_load, session_count, player_count
        """
        try:
            data = self.mongo.get_session_rpe_aggregates(team=team)
            df = pd.DataFrame(data or [])
            if df.empty:
                return df
            for col in ("total_load", "session_count", "player_count"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        except Exception as e:
            raise DatabaseError(f"Failed to fetch session aggregates: {e}") from e

    def get_rpe_joined_per_session_df(
        self,
        team: str,
        date_from: Optional[date_cls] = None,
        date_to: Optional[date_cls] = None,
    ) -> pd.DataFrame:
        """
        Per-player RPE rows joined to sessions via session_id.

        Returns:
            DataFrame columns (when available):
            session_id, date, team, session_type, duration, player_id, rpe, training_minutes, timestamp
        """
        try:
            pipeline: List[Dict[str, Any]] = [
                {"$lookup": {
                    "from": "sessions",
                    "localField": "session_id",
                    "foreignField": "session_id",
                    "as": "session"
                }},
                {"$unwind": "$session"},
            ]

            if team:
                pipeline.append({"$match": {"session.team": team}})

            date_match: Dict[str, Any] = {}
            if date_from is not None:
                date_match["$gte"] = pd.to_datetime(date_from)
            if date_to is not None:
                date_match["$lte"] = pd.to_datetime(date_to) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            if date_match:
                pipeline.append({"$match": {"session.date": date_match}})

            pipeline += [
                {"$project": {
                    "_id": 0,
                    "player_id": 1,
                    "rpe": {"$ifNull": ["$rpe_score", "$rpe"]},
                    "training_minutes": 1,
                    "timestamp": 1,
                    "session_id": "$session.session_id",
                    "date": "$session.date",
                    "team": "$session.team",
                    "session_type": "$session.session_type",
                    "duration": "$session.duration"
                }},
                {"$match": {"rpe": {"$ne": None}, "date": {"$ne": None}}}
            ]

            rows = list(self.mongo.db["player_rpe"].aggregate(pipeline))
            df = pd.DataFrame(rows)
            if df.empty:
                return df

            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["rpe"] = pd.to_numeric(df["rpe"], errors="coerce")
            if "training_minutes" in df.columns:
                df["training_minutes"] = pd.to_numeric(df["training_minutes"], errors="coerce")

            df = df.dropna(subset=["date", "rpe"])

            cols = [
                "session_id", "date", "team", "session_type", "duration",
                "player_id", "rpe", "training_minutes", "timestamp"
            ]
            return df[[c for c in cols if c in df.columns]]

        except PyMongoError as e:
            raise DatabaseError(f"Failed to fetch per-session RPE distribution: {e}") from e


# -----------------------------
# Backwards-compatible shims
# -----------------------------
def get_session_rpe_aggregates_df(mongo, team: str) -> pd.DataFrame:
    """
    DEPRECATED: use SessionsDashboardRepo(mongo).get_session_rpe_aggregates_df(team)
    """
    warnings.warn(
        "get_session_rpe_aggregates_df() is deprecated; use SessionsDashboardRepo.get_session_rpe_aggregates_df()",
        DeprecationWarning,
        stacklevel=2,
    )
    return SessionsDashboardRepo(mongo).get_session_rpe_aggregates_df(team)


def get_rpe_joined_per_session_df(
    mongo,
    team: str,
    date_from: Optional[date_cls] = None,
    date_to: Optional[date_cls] = None,
) -> pd.DataFrame:
    """
    DEPRECATED: use SessionsDashboardRepo(mongo).get_rpe_joined_per_session_df(team, date_from, date_to)
    """
    warnings.warn(
        "get_rpe_joined_per_session_df() is deprecated; use SessionsDashboardRepo.get_rpe_joined_per_session_df()",
        DeprecationWarning,
        stacklevel=2,
    )
    return SessionsDashboardRepo(mongo).get_rpe_joined_per_session_df(team, date_from, date_to)