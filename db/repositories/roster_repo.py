# db/repositories/roster_repo.py
from typing import Any, Dict, List, Optional
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