# db/repositories/attendance_repo.py
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Set, Union

from pymongo.errors import PyMongoError

from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError


class AttendanceRepository(BaseRepository):
    """
    Repository for:
      - listing recent sessions
      - upserting session attendance
      - saving per-match minutes (write-once)
    Collections used: 'sessions', 'attendance', 'match_minutes'
    """

    def __init__(self, db):
        super().__init__(db, "attendance")   # default col for BaseRepository methods
        self.sessions = db["sessions"]
        self.minutes = db["match_minutes"]

    # ---------------- Recent sessions ----------------
    def get_recent_sessions(
        self,
        *,
        team: str,
        limit: Optional[int] = 6,
        up_to_date: Optional[date] = None,
        session_type: Union[str, List[str], None] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent sessions for a team (date DESC).

        Args:
            team: "U18" | "U21".
            limit: Max number of sessions to fetch. If None or <=0, no limit is applied.
            up_to_date: Include sessions on or before this date.
            session_type: Filter by a single type (e.g., "M") or by multiple types (e.g., ["T1","T2","T3","T4"]).
        """
        if not team:
            raise ApplicationError("get_recent_sessions: 'team' is required.")

        try:
            q: Dict[str, Any] = {"team": team}
            if up_to_date:
                end = datetime.combine(up_to_date, time.max)
                q["date"] = {"$lte": end}

            if session_type:
                if isinstance(session_type, list):
                    q["session_type"] = {"$in": session_type}
                else:
                    q["session_type"] = session_type

            cur = self.sessions.find(q, {"_id": 0}).sort([("date", -1)])

            # Apply limit, with a small buffer as in original code
            if isinstance(limit, int) and limit > 0:
                cur = cur.limit(limit * 2)

            records = list(cur)

            # Stable sort that copes with date/datetime/iso
            def _key(s):
                d = s.get("date")
                if isinstance(d, datetime):
                    return d
                if isinstance(d, date):
                    return datetime.combine(d, time.min)
                try:
                    return datetime.fromisoformat(str(d))
                except Exception:
                    return datetime.min

            records.sort(key=_key, reverse=True)

            if isinstance(limit, int) and limit > 0:
                return records[: (limit * 2)]
            return records

        except PyMongoError as e:
            raise DatabaseError(f"Failed to fetch recent sessions: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_recent_sessions: {e}") from e

    # ---------------- Upsert attendance (present + absent) ----------------
    def upsert_attendance_full(
        self,
        *,
        session_id: str,
        team: str,
        present_ids: List[int],
        absent_items: List[Dict[str, Any]],
        user: str,
    ) -> None:
        """Insert or update full attendance (present + absent) for a session.

        Args:
            session_id: Session identifier (e.g., "20250901U21").
            team: "U18" | "U21".
            present_ids: Player IDs marked present (deduped + sorted in this method).
            absent_items: List of {"player_id": int, "reason": str} where `reason` is an ID
                from the canonical set (e.g., "injury", "individual", "physio_internal",
                "physio_external", "school", "holiday", "illness", "awol", "other_team").
            user: Display name or identifier of the editor.

        Notes:
            - Overwrites both `present` and `absent` arrays atomically.
            - Validates/normalizes absence reasons against the canonical set.
            (Spaces → underscores, case-insensitive; e.g., "Other team" -> "other_team")
            - Temporarily allows deprecated legacy ID "excused" for backward compatibility.
        """
        if not session_id or not team:
            raise ApplicationError("upsert_attendance_full: 'session_id' and 'team' are required.")
        if user is None or str(user).strip() == "":
            raise ApplicationError("upsert_attendance_full: 'user' is required.")

        # Try to import canonical absence reasons from utils; fall back to a static set.
        try:
            from utils.constants import ABSENCE_REASONS as ABSENCE_META  # [{"id","label","emoji"}, ...]
            VALID_IDS: Set[str] = {str(r["id"]) for r in ABSENCE_META}
        except Exception:
            VALID_IDS = {
                "injury", "individual", "physio_internal", "physio_external",
                "school", "holiday", "illness", "awol", "other_team",
            }
        DEPRECATED_IDS: Set[str] = {"excused"}  # temporary compatibility

        def _norm_reason(reason: str) -> str:
            return str(reason).strip().lower().replace(" ", "_")

        try:
            # Clean & dedupe present IDs
            present_clean = sorted(set(int(pid) for pid in present_ids))

            # Validate & normalize absentees
            absent_clean: List[Dict[str, Any]] = []
            for item in absent_items:
                pid = int(item["player_id"])
                norm = _norm_reason(item["reason"])
                if norm not in VALID_IDS and norm not in DEPRECATED_IDS:
                    raise ApplicationError(
                        f"Invalid absence reason '{item['reason']}' (normalized '{norm}') for player_id {pid}"
                    )
                absent_clean.append({"player_id": pid, "reason": norm})

            now = datetime.utcnow()
            # Use BaseRepository's default collection ('attendance') via self.col
            self.col.update_one(
                {"session_id": session_id},
                {
                    "$setOnInsert": {
                        "session_id": session_id,
                        "team": team,
                        "created": now,
                    },
                    "$set": {
                        "present": present_clean,
                        "absent": absent_clean,
                        "last_updated": now,
                        "user": user,
                    },
                },
                upsert=True,
            )
        except PyMongoError as e:
            raise DatabaseError(f"Failed to upsert attendance: {e}") from e

    # ---------------- Save match minutes (write-once) ----------------
    def save_match_minutes_once(
        self,
        *,
        session_id: str,
        team: str,
        minutes_items: List[Dict[str, Any]],
        user: str,
    ) -> None:
        """Create match minutes for a session exactly once.

        - Inserts a new document for session_id; raises if it already exists.
        - Normalizes minutes to int and clamps to [0, 120].
        """
        if not session_id or not team:
            raise ApplicationError("save_match_minutes_once: 'session_id' and 'team' are required.")
        if user is None or str(user).strip() == "":
            raise ApplicationError("save_match_minutes_once: 'user' is required.")

        try:
            existing = self.minutes.find_one({"session_id": session_id}, {"_id": 1})
            if existing:
                raise DatabaseError("Match minutes already saved for this session (immutable by design).")

            cleaned: List[Dict[str, int]] = []
            for item in minutes_items:
                pid = int(item["player_id"])
                mins = max(0, min(120, int(item.get("minutes", 0))))
                cleaned.append({"player_id": pid, "minutes": mins})

            now = datetime.utcnow()
            doc = {
                "session_id": session_id,
                "team": team,
                "minutes": cleaned,
                "created": now,
                "last_updated": now,
                "user": user,
            }
            self.minutes.insert_one(doc)
        except PyMongoError as e:
            raise DatabaseError(f"Failed to save match minutes: {e}") from e