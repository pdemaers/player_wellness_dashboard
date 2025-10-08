# db/repositories/roster_repo.py
from typing import Any, Dict, List, Optional
import pandas as pd
from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError

from utils.constants import NameStyle

class RosterRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "roster")



    def _format_player_name(
        self,
        doc: Dict[str, Any],
        style: NameStyle = "LAST_FIRST",
    ) -> str:
        """Format a roster doc into a display name.

        Styles:
            - "LAST_FIRST" (default): "DOE, John"
            - "First Last": "John Doe"
            - "LAST FirstInitial.": "DOE J."
        """
        first = str(doc.get("player_first_name") or doc.get("first_name") or "").strip()
        last  = str(doc.get("player_last_name")  or doc.get("last_name")  or "").strip()

        if style == "First Last":
            return " ".join(p for p in [first, last] if p)
        if style == "LAST FirstInitial.":
            fi = f"{first[:1].upper()}." if first else ""
            return " ".join(p for p in [last.upper(), fi] if p).strip()
        # default: LAST, First
        return ", ".join([last.upper(), first]).strip(", ").replace(" ,", ",")



    def get_player_names(
        self,
        team: str,
        style: NameStyle = "LAST_FIRST",
        include_inactive: bool = False,
        sort_by_name: bool = True,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return players with normalized ids and display names.

        Args:
            team: "U18" | "U21".
            style: Display style for names.
            include_inactive: If your roster has an `active` flag, include inactive too.
            sort_by_name: Sort by the rendered display name.
            fields: Extra fields to include from roster.

        Returns:
            [{"player_id": int, "display_name": str, ...}, ...]

        Raises:
            DatabaseError: If the underlying MongoDB query fails.
            ApplicationError: If roster data is malformed (e.g., invalid `player_id`).
        """
        try:
            q: Dict[str, Any] = {"team": team}
            if not include_inactive:
                q.update({"$or": [{"active": True}, {"active": {"$exists": False}}]})

            projection = {
                "_id": 0, "player_id": 1,
                "player_first_name": 1, "player_last_name": 1,
                "first_name": 1, "last_name": 1,
            }
            if fields:
                for f in fields:
                    projection[f] = 1

            docs = list(self.find_safe(q, projection))

            out: List[Dict[str, Any]] = []
            for d in docs:
                try:
                    pid = int(d.get("player_id"))
                except Exception:
                    continue
                display_name = self._format_player_name(d, style=style)
                item = {"player_id": pid, "display_name": display_name}
                if fields:
                    for f in fields:
                        if f in d:
                            item[f] = d[f]
                out.append(item)

            if sort_by_name:
                out.sort(key=lambda x: (x["display_name"], x["player_id"]))
            return out
        
        except DatabaseError:
            # re-raise DB errors unchanged
            raise
        except ApplicationError:
            # re-raise app errors unchanged
            raise
        except Exception as e:
            # catch-all safety net
            raise ApplicationError(f"Unexpected error in get_player_names: {e}") from e



    def get_roster_df(self, team: Optional[str] = None) -> pd.DataFrame:
        """Return the roster as a pandas DataFrame (excluding `_id`). Optionally filter by team.

        Returns:
            pandas.DataFrame: One row per roster document.

        Raises:
            DatabaseError: If the MongoDB query fails.
        """
        try:
            filt: Dict[str, Any] = {}
            if team:
                filt["team"] = team
            docs = self.find_safe(filt, {"_id": 0})
            return pd.DataFrame(docs)
        except DatabaseError:
            raise
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_roster_df: {e}") from e



    def save_roster_df(self, *, team: str, df: pd.DataFrame) -> bool:
        """Replace the roster for a single team with `df` rows.

        Notes:
            - Destructive for that team only: delete_many({'team': team}) then insert.
            - Ensures every row has the correct `team` value.

        Args:
            df: DataFrame containing roster documents (dict-like rows).

        Returns:
            True if the operation succeeded.

        Raises:
            ApplicationError: If `df` is not a DataFrame or rows are invalid.
            DatabaseError: If MongoDB operations fail.
        """
        # --- Application-level validation ---
        if not isinstance(df, pd.DataFrame):
            raise ApplicationError("save_roster_df: `df` must be a pandas DataFrame.")
        # Convert *before* deleting collection, to fail fast on data issues.
        try:
            records = df.to_dict("records")  # type: List[Dict[str, Any]]
        except Exception as e:
            raise ApplicationError(f"save_roster_df: cannot convert DataFrame to records: {e}") from e

        # Enforce team on all rows
        for r in records:
            r["team"] = team
        
        # Optional safety: prevent accidental wipe if the new data is empty.
        # Comment this out if you *do* want to allow clearing the roster.
        if len(records) == 0:
            raise ApplicationError("save_roster_df: refusing to replace with an empty DataFrame.")

        # --- DB operations ---
        try:
            # Replace only this team's roster
            self.col.delete_many({"team": team})
            self.col.insert_many(records, ordered=True)
            return True
        except Exception as e:
            raise DatabaseError(f"save_roster_team_df failed: {e}") from e