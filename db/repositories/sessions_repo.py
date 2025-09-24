# db/repositories/sessions_repo.py
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, List, Optional
import pandas as pd

from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError


def _as_datetime(d: date | datetime) -> datetime:
    """Normalize a date or datetime to a datetime (midnight if date)."""
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime.combine(d, time.min)
    raise ApplicationError(f"Invalid 'date' type: {type(d)}")


class SessionsRepository(BaseRepository):
    """DB access for training sessions and matches (collection: 'sessions')."""

    def __init__(self, db):
        super().__init__(db, "sessions")

    # ---------- Write ----------
    def add_session(self, *, session_data: Dict[str, Any]) -> bool:
        """Insert a new session or match.

        Required keys in session_data:
            - date: datetime | date
            - team: str (e.g., "U18", "U21")
            - session_type: str ("T1", "T2", "T3" or "T4" for training, "M" for match)
            - duration: int (minutes) — optional but recommended

        Side-effects:
            - Normalizes `date` to datetime.
            - Sets `weeknumber` (ISO week).
            - Generates `session_id` as YYYYMMDD + team (e.g., 20250115U18).

        Raises:
            ApplicationError: if required keys are missing/invalid.
            DatabaseError: on MongoDB failure (e.g., duplicate session_id).
        """
        try:
            required = ["date", "team", "session_type"]
            missing = [k for k in required if k not in session_data]
            if missing:
                raise ApplicationError(f"add_session: missing fields: {', '.join(missing)}")

            dt = _as_datetime(session_data["date"])
            team = str(session_data["team"])
            if not team:
                raise ApplicationError("add_session: 'team' cannot be empty.")

            session_id = dt.strftime("%Y%m%d") + team
            session_doc = dict(session_data)  # shallow copy
            session_doc["date"] = dt
            session_doc["weeknumber"] = dt.isocalendar().week
            session_doc["session_id"] = session_id

            self.insert_one_safe(session_doc)  # raises DatabaseError on failure
            return True

        except DatabaseError:
            raise
        except Exception as e:
            raise ApplicationError(f"Unexpected error in add_session: {e}") from e

    # ---------- Read ----------
    def get_sessions_df(
        self,
        *,
        team: Optional[str] = None,
        session_type: Optional[str] = None,
        date_from: Optional[date | datetime] = None,
        date_to: Optional[date | datetime] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> pd.DataFrame:
        """Return sessions as a DataFrame, with optional filters.

        Args:
            team: Filter by team (e.g., "U18"). If None, return all teams.
            session_type: ("T1", "T2", "T3" or "T4" for training, "M" for match)
            date_from: inclusive lower bound on `date`.
            date_to: exclusive upper bound on `date` (use end-of-day if you pass a date).

        Returns:
            pandas.DataFrame without `_id`.

        Raises:
            DatabaseError: on MongoDB failure.
            ApplicationError: on parameter errors.
        """
        q: Dict[str, Any] = {}
        if team:
            q["team"] = team
        if session_type:
            q["session_type"] = session_type

        if date_from or date_to:
            dr: Dict[str, Any] = {}
            if date_from:
                dr["$gte"] = _as_datetime(date_from)
            if date_to:
                # if a plain date is provided, treat as end-of-day exclusive
                if isinstance(date_to, date) and not isinstance(date_to, datetime):
                    date_to = datetime.combine(date_to, time.max)
                dr["$lt"] = _as_datetime(date_to)
            q["date"] = dr

        proj = {"_id": 0}
        if projection:
            proj.update(projection)

        try:
            docs: List[Dict[str, Any]] = self.find_safe(q, proj)
            return pd.DataFrame(docs)
        except DatabaseError:
            raise
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_sessions_df: {e}") from e