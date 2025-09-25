# db/repositories/player_pdp_repo.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError


class PlayerPdpRepository(BaseRepository):
    """
    Repository for player PDP documents.
    Collection: 'player_pdp'
    Recommended fields:
      - player_id: int
      - team: str (optional but useful)
      - created_at: datetime
      - last_updated: datetime
      - author: str (who created/updated)
      - status: str (e.g., 'draft' | 'final')
      - payload: dict (the PDP content)
    """

    def __init__(self, db):
        super().__init__(db, "player_pdp")



    # ---- Read ----
    def get_latest_pdp_for_player(self, *, player_id: int) -> Optional[Dict[str, Any]]:
        """Return the most recent PDP for a player (by last_updated desc)."""
        if player_id is None:
            raise ApplicationError("get_latest_pdp_for_player: 'player_id' is required.")
        try:
            return self.col.find_one({"player_id": int(player_id)}, sort=[("last_updated", -1)])
        except Exception as e:
            raise DatabaseError(f"Failed to fetch latest PDP for player {player_id}: {e}") from e
        


    def get_all_pdps_for_player(self, *, player_id: int) -> List[Dict[str, Any]]:
        """Return all PDPs for a player, sorted by last_updated desc."""
        if player_id is None:
            raise ApplicationError("get_all_pdps_for_player: 'player_id' is required.")
        try:
            docs = list(self.col.find({"player_id": int(player_id)}).sort("last_updated", -1))
            return docs
        except Exception as e:
            raise DatabaseError(f"Failed to fetch all PDPs for player {player_id}: {e}") from e
        
        

    # ---- Write ----
    def insert_new_pdp(self, *, pdp_data: Dict[str, Any]) -> Any:
        """Insert a new PDP document. Fills timestamps if missing.

        Returns:
            The inserted _id

        Raises:
            ApplicationError: if required fields are missing/invalid.
            DatabaseError: on Mongo failure.
        """
        if not isinstance(pdp_data, dict):
            raise ApplicationError("insert_new_pdp: 'pdp_data' must be a dict.")

        # Minimal required fields
        required = ["player_id", "payload"]
        missing = [k for k in required if k not in pdp_data]
        if missing:
            raise ApplicationError(f"insert_new_pdp: missing fields: {', '.join(missing)}")

        doc = dict(pdp_data)
        # normalize/ensure timestamps
        now = datetime.utcnow()
        doc.setdefault("created_at", now)
        doc.setdefault("last_updated", now)

        try:
            res = self.col.insert_one(doc)
            return res.inserted_id
        except Exception as e:
            raise DatabaseError(f"Failed to insert new PDP: {e}") from e