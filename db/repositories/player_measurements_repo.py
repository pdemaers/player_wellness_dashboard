"""
Repository: Player Measurements.

Collection: `player_measurements`

Document shape (one per (team, date)):
{
    _id: ObjectId,
    measurement_id: str,   # f"{team}-{date_iso}"
    team: str,
    date: str,             # "YYYY-MM-DD"
    entries: [
        { player_id: str, height_cm: int|None, weight_kg: float|None, absent: bool },
        ...
    ],
    created_by: str,
    created_at: datetime,      # UTC
    updated_by: str,
    updated_at: datetime       # UTC
}

Indexes:
    - Unique compound index on (team, date)
"""

from __future__ import annotations
from datetime import datetime, date as date_type
from typing import List, Dict, Any

from pymongo.errors import PyMongoError
from db.errors import DatabaseError


class PlayerMeasurementsRepository:
    """Repository for player measurement documents."""

    def __init__(self, mongo):
        """
        Args:
            mongo: MongoWrapper instance with `db` attribute (pymongo Database)
        """
        self.mongo = mongo
        self.col = self.mongo.db["player_measurements"]
        self.roster = self.mongo.db["roster"]

    # ---------------- Indexing ----------------

    def ensure_indexes(self) -> None:
        """Create unique index on (team, date)."""
        try:
            self.col.create_index([("team", 1), ("date", 1)], unique=True, name="uniq_team_date")
        except PyMongoError as e:
            raise DatabaseError(f"ensure_indexes failed: {e}") from e

    # ---------------- Reads ----------------

    def get_latest_by_team(self, team: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Optional helper to retrieve recent measurement sessions for a team."""
        try:
            return list(
                self.col.find({"team": team})
                .sort([("date", -1)])
                .limit(int(limit))
            )
        except PyMongoError as e:
            raise DatabaseError(f"get_latest_by_team failed: {e}") from e

    # ---------------- Writes ----------------

    def upsert_measurement_session(
        self,
        team: str,
        measurement_date: date_type,
        entries: List[Dict[str, Any]],
        user: str,
    ) -> str:
        """
        UPSERT a measurement document for (team, date).

        Args:
            team: Team code (e.g., "U18", "U21")
            measurement_date: Python date object
            entries: List of row dicts (player_id, player_name, height_cm, weight_kg, absent)
            user: Username (audit)

        Returns:
            The document's _id as a string.

        Raises:
            ValueError: if inputs are invalid
            DatabaseError: on MongoDB errors
        """
        if not team:
            raise ValueError("team is required")
        if not isinstance(measurement_date, date_type):
            raise ValueError("measurement_date must be a date")
        if not isinstance(entries, list) or not all(isinstance(x, dict) for x in entries):
            raise ValueError("entries must be a list[dict]")

        # Normalize & validate
        date_iso = measurement_date.isoformat()

        norm_entries: List[Dict[str, Any]] = []
        for e in entries:
            pid = str(e["player_id"]).strip()
            pname = str(e["player_name"]).strip()
            absent = bool(e.get("absent", False))

            height_cm = e.get("height_cm", None)
            weight_kg = e.get("weight_kg", None)

            # Type normalize
            if height_cm is not None:
                try:
                    height_cm = int(height_cm)
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid height for player_id={pid}")

            if weight_kg is not None:
                try:
                    weight_kg = round(float(weight_kg), 1)
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid weight for player_id={pid}")

            if absent:
                height_cm, weight_kg = None, None

            norm_entries.append(
                {
                    "player_id": pid,
                    "player_name": pname,
                    "height_cm": height_cm,
                    "weight_kg": weight_kg,
                    "absent": absent,
                }
            )

        now = datetime.utcnow()
        date_iso = measurement_date.isoformat()
        measurement_id = f"{team}-{date_iso}"

        doc_filter = {"team": team, "date": date_iso}
        doc_update = {
            "$set": {
                "measurement_id": measurement_id,
                "team": team,
                "date": date_iso,
                "entries": norm_entries,
                "updated_at": now,
                "updated_by": user,
            },
            "$setOnInsert": {
                "created_at": now,
                "created_by": user,
            },
        }

        try:
            self.col.update_one(doc_filter, doc_update, upsert=True)
            doc = self.col.find_one(doc_filter, {"_id": 1})
            return str(doc["_id"])
        except PyMongoError as e:
            raise DatabaseError(f"upsert_measurement_session failed: {e}") from e