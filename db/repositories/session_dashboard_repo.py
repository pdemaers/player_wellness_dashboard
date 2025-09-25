"""
Session Dashboard Repository
Centralizes DB access for the session dashboard.

Collections assumed:
- sessions: {_id, date (ISO string), team, session_type, duration, ...}
- player_rpe: {_id, player_id, session_id, rpe_score|rpe, training_minutes, timestamp, ...}
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import date as date_cls
import pandas as pd
from pymongo.errors import PyMongoError
from db.errors import DatabaseError  # your central error type


# Optional: align with your existing custom error
try:
    from db.mongo_wrapper import DatabaseError
except Exception:  # fallback if not present
    class DatabaseError(RuntimeError):
        """Generic DB error wrapper for the dashboard."""


def _date_bounds(
    date_from: Optional[date_cls],
    date_to: Optional[date_cls],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert date range to ISO strings for Mongo match (inclusive start, exclusive end).
    """
    if date_from:
        start = datetime.combine(date_from, datetime.min.time()).date().isoformat()
    else:
        start = None
    if date_to:
        end = (datetime.combine(date_to, datetime.min.time()) + timedelta(days=1)).date().isoformat()
    else:
        end = None
    return start, end


def get_session_rpe_aggregates_df(mongo, team: str) -> pd.DataFrame:
    """
    Use your existing MongoWrapper method to fetch weekly/session-type aggregates.
    Returns a DataFrame with at least:
        week, session_type, total_load, session_count, player_count
    """
    try:
        data = mongo.get_session_rpe_aggregates(team=team)  # ← your existing method
        df = pd.DataFrame(data or [])
        if df.empty:
            return df
        # Defensive: ensure numeric columns
        for col in ("total_load", "session_count", "player_count"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        raise DatabaseError(f"Failed to fetch session aggregates: {e}") from e


def get_rpe_joined_per_session_df(
    _mongo,
    team: str,
    date_from: Optional[date_cls] = None,
    date_to: Optional[date_cls] = None,
) -> pd.DataFrame:
    """
    Per-player RPE rows joined to sessions via session_id (same as get_rpe_loads).
    Returns columns:
        session_id, date (datetime64), session_type, player_id, rpe, training_minutes, duration
    """
    try:
        # --- Build aggregation pipeline mirroring get_rpe_loads join logic ---
        pipeline: List[Dict[str, Any]] = [
            # Join player_rpe → sessions ON session_id (not _id)
            {"$lookup": {
                "from": "sessions",
                "localField": "session_id",
                "foreignField": "session_id",
                "as": "session"
            }},
            {"$unwind": "$session"},
        ]

        # Optional team filter (same as your get_rpe_loads)
        if team:
            pipeline.append({"$match": {"session.team": team}})

        # Optional date filter on session.date (your get_rpe_loads uses $isoWeek on a Date,
        # so we assume sessions.date is a proper BSON Date)
        date_match: Dict[str, Any] = {}
        if date_from is not None:
            # include from
            date_match["$gte"] = pd.to_datetime(date_from)
        if date_to is not None:
            # include to (end of day)
            date_match["$lte"] = pd.to_datetime(date_to) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        if date_match:
            pipeline.append({"$match": {"session.date": date_match}})

        # Shape the fields we need for a boxplot
        pipeline.extend([
            {"$project": {
                "_id": 0,
                "player_id": 1,
                # prefer rpe_score, fall back to rpe
                "rpe": {"$ifNull": ["$rpe_score", "$rpe"]},
                "training_minutes": 1,
                "timestamp": 1,
                "session_id": "$session.session_id",
                "date": "$session.date",
                "team": "$session.team",
                "session_type": "$session.session_type",
                "duration": "$session.duration"
            }},
            # drop records with missing rpe or date
            {"$match": {"rpe": {"$ne": None}, "date": {"$ne": None}}}
        ])

        rows = list(_mongo.db["player_rpe"].aggregate(pipeline))
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Normalize types
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["rpe"] = pd.to_numeric(df["rpe"], errors="coerce")
        if "training_minutes" in df.columns:
            df["training_minutes"] = pd.to_numeric(df["training_minutes"], errors="coerce")

        # Final clean
        df = df.dropna(subset=["date", "rpe"])

        # Keep tidy column order
        cols = [
            "session_id", "date", "team", "session_type", "duration",
            "player_id", "rpe", "training_minutes", "timestamp"
        ]
        return df[[c for c in cols if c in df.columns]]

    except PyMongoError as e:
        raise DatabaseError(f"Failed to fetch per-session RPE distribution: {e}") from e