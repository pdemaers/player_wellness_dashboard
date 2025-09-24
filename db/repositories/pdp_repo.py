# db/repositories/pdp_repo.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError


class PdpRepository(BaseRepository):
    """
    Repository for team PDP structures.
    Collection: `pdp_structure`
    Documents are keyed by `_id = "<TEAM>_structure"`.
    """

    def __init__(self, db):
        super().__init__(db, "pdp_structure")



    def get_pdp_structure_for_team(self, *, team: str) -> Optional[Dict[str, Any]]:
        """Fetch the PDP structure for a given team.

        Args:
            team: Team code (e.g. "U21").

        Returns:
            The PDP structure document without any changes, or None if not found.

        Raises:
            DatabaseError: On MongoDB error.
            ApplicationError: If team is empty.
        """
        if not team:
            raise ApplicationError("get_pdp_structure_for_team: 'team' is required.")
        try:
            return self.col.find_one({"_id": f"{team}_structure"})
        except Exception as e:
            raise DatabaseError(f"Failed to load PDP structure for {team}: {e}") from e
        


    def update_pdp_structure_for_team(self, *, team: str, updated_doc: Dict[str, Any]) -> bool:
        """Insert or replace the PDP structure for a team (upsert).

        Args:
            team: Team code.
            updated_doc: PDP structure document (will be stored verbatim).

        Returns:
            True if a document was upserted or modified.

        Raises:
            DatabaseError: On MongoDB error.
            ApplicationError: If inputs are invalid.
        """
        if not team:
            raise ApplicationError("update_pdp_structure_for_team: 'team' is required.")
        if not isinstance(updated_doc, dict):
            raise ApplicationError("update_pdp_structure_for_team: 'updated_doc' must be a dict.")

        try:
            updated_doc = dict(updated_doc)  # shallow copy
            updated_doc["_id"] = f"{team}_structure"
            result = self.col.replace_one({"_id": updated_doc["_id"]}, updated_doc, upsert=True)
            return (result.modified_count or 0) > 0 or (result.upserted_id is not None)
        except Exception as e:
            raise DatabaseError(f"Failed to update PDP structure for {team}: {e}") from e
        
        

    def list_all_team_structures(self) -> List[str]:
        """List all team-specific PDP structure IDs (e.g., 'U21_structure')."""
        try:
            return [doc["_id"] for doc in self.col.find({}, {"_id": 1})]
        except Exception as e:
            raise DatabaseError(f"Failed to list PDP structures: {e}") from e