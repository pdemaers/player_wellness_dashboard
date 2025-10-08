from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import PyMongoError

from db.errors import DatabaseError, ApplicationError

# You can keep this alias for backwards-compat logs if you want
class InjuryRepoError(Exception):
    pass


def _as_oid(maybe_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(maybe_id)
    except Exception:
        return None


def _as_datetime(d: Any) -> datetime:
    """Accept datetime|date|iso-string -> naive UTC datetime (ok for Mongo)."""
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    if isinstance(d, str):
        # try simple ISO parse; tolerate trailing 'Z'
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
    raise ApplicationError(f"Invalid date/datetime value: {d!r}")


class InjuryRepository:
    """Repository for player injuries (collection: 'player_injuries')."""

    def __init__(self, db: Database, collection: str = "player_injuries") -> None:
        self.col = db[collection]

    # -------------------- READ (existing) --------------------
    def list_injuries_by_team(self, team: str) -> List[Dict[str, Any]]:
        try:
            docs = list(self.col.find({"team": team}))
            # Sort by updated_at (fallback: injury_date) DESC
            docs.sort(
                key=lambda d: (
                    str(d.get("updated_at") or ""),
                    str(d.get("injury_date") or ""),
                ),
                reverse=True,
            )
            return docs
        except PyMongoError as e:
            raise DatabaseError(f"Failed to fetch team injuries: {e}") from e

    @staticmethod
    def latest_status(injury: Dict[str, Any]) -> str:
        if injury.get("current_status"):
            return injury["current_status"]
        sessions = injury.get("treatment_sessions") or []
        if not sessions:
            return "—"
        try:
            sessions.sort(key=lambda s: s.get("session_date", ""), reverse=True)
        except Exception:
            pass
        return sessions[0].get("status_after", "—")

    # -------------------- CREATE --------------------
    def insert_player_injury(self, *, injury_doc: Dict[str, Any]) -> str:
        """Insert a new injury and return inserted _id (as str)."""
        if not isinstance(injury_doc, dict):
            raise ApplicationError("insert_player_injury: 'injury_doc' must be a dict.")

        doc = dict(injury_doc)
        now = datetime.utcnow()
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        doc.setdefault("last_updated", now)          # if you use this elsewhere
        doc.setdefault("current_status", "open")
        doc.setdefault("treatment_sessions", [])     # embedded sessions array
        doc.setdefault("comments", [])               # optional free comments stream

        # Normalize optional injury_date if present
        if "injury_date" in doc:
            doc["injury_date"] = _as_datetime(doc["injury_date"])

        try:
            res = self.col.insert_one(doc)
            return str(res.inserted_id)
        except PyMongoError as e:
            raise DatabaseError(f"Failed to insert injury: {e}") from e

    # -------------------- READ: player history --------------------
    def get_player_injuries(self, *, player_id: int, sort_desc: bool = True) -> List[Dict[str, Any]]:
        """All injuries for a player, sorted by created_at."""
        sort_order = -1 if sort_desc else 1
        try:
            return list(self.col.find({"player_id": int(player_id)}).sort("created_at", sort_order))
        except PyMongoError as e:
            raise DatabaseError(f"Failed to load injuries for player {player_id}: {e}") from e

    # -------------------- READ: by id --------------------
    def get_injury_by_id(self, *, injury_id: str) -> Optional[Dict[str, Any]]:
        """Fetch by Mongo _id (hex) or by custom injury_id string field."""
        filt: Dict[str, Any]
        oid = _as_oid(injury_id)
        filt = {"_id": oid} if oid else {"injury_id": injury_id}
        try:
            return self.col.find_one(filt)
        except PyMongoError as e:
            raise DatabaseError(f"Failed to fetch injury: {e}") from e

    # -------------------- UPDATE: add embedded treatment session --------------------
    def add_treatment_session(
        self,
        *,
        injury_id: str,
        treatment_session: Dict[str, Any],
        current_status: str,
        updated_by: str,
    ) -> bool:
        """Append a treatment session and update current_status/audit fields."""
        if not isinstance(treatment_session, dict):
            raise ApplicationError("add_treatment_session: 'treatment_session' must be a dict.")
        if not current_status:
            raise ApplicationError("add_treatment_session: 'current_status' is required.")
        if not updated_by:
            raise ApplicationError("add_treatment_session: 'updated_by' is required.")

        ts = dict(treatment_session)
        # normalize & enforce required fields
        if "session_date" not in ts:
            raise ApplicationError("add_treatment_session: missing 'session_date'.")
        ts["session_date"] = _as_datetime(ts["session_date"])
        ts["created_at"] = ts.get("created_at") or datetime.utcnow()
        if not ts.get("created_by"):
            raise ApplicationError("add_treatment_session: missing 'created_by'.")
        # default status_after if not provided
        ts.setdefault("status_after", current_status)
        # normalize comment
        if "comment" in ts and isinstance(ts["comment"], str):
            ts["comment"] = ts["comment"].strip()

        # filter (by _id or injury_id)
        oid = _as_oid(injury_id)
        filt = {"_id": oid} if oid else {"injury_id": injury_id}

        update = {
            "$push": {"treatment_sessions": ts},
            "$set": {
                "current_status": current_status,
                "updated_by": updated_by,
                "updated_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
            },
        }

        try:
            res = self.col.update_one(filt, update)
            if res.matched_count == 0:
                raise DatabaseError("Injury not found.")
            return res.modified_count > 0
        except PyMongoError as e:
            raise DatabaseError(f"Could not add treatment session: {e}") from e

    # -------------------- UPDATE: optional free comment stream --------------------
    def add_injury_comment(self, *, injury_id: str, text: str, author_email: str) -> bool:
        """Append a free-form comment in 'comments' (separate from treatment_sessions)."""
        if not text or not text.strip():
            raise ApplicationError("add_injury_comment: 'text' is required.")
        if not author_email:
            raise ApplicationError("add_injury_comment: 'author_email' is required.")

        comment = {"ts": datetime.utcnow(), "author": author_email, "text": text.strip()}

        oid = _as_oid(injury_id)
        filt = {"_id": oid} if oid else {"injury_id": injury_id}

        try:
            res = self.col.update_one(
                filt,
                {"$push": {"comments": comment}, "$set": {"last_updated": datetime.utcnow(), "updated_at": datetime.utcnow()}},
            )
            if res.matched_count == 0:
                raise DatabaseError("Injury not found.")
            return res.modified_count > 0
        except PyMongoError as e:
            raise DatabaseError(f"Could not add comment: {e}") from e