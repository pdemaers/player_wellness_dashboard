from __future__ import annotations
from typing import Any, Dict, List
from pymongo.database import Database
from pymongo.errors import PyMongoError

from db.errors import DatabaseError, ApplicationError

class InjuryRepoError(Exception):
    pass

class InjuryRepo:
    def __init__(self, db: Database, collection: str = "player_injuries") -> None:
        self.col = db[collection]

    def list_injuries_by_team(self, team: str) -> List[Dict[str, Any]]:
        try:
            docs = list(self.col.find({"team": team}))
            docs.sort(key=lambda d: (str(d.get("updated_at") or ""), str(d.get("injury_date") or "")), reverse=True)
            return docs
        except PyMongoError as e:
            raise InjuryRepoError(f"Failed to fetch team injuries: {e}")

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