"""MongoDB wrapper for the Player Wellness Dashboard.

This module defines:
- `MongoWrapper`: typed access layer for collections (`roster`, `player_wellness`, `player_rpe`, `sessions`, `pdp_structure`).
- `DatabaseError`: custom error wrapper around pymongo exceptions.

Notes:
    - Timestamps are stored in UTC; display uses Europe/Brussels.
    - This module must be import-safe (no DB side effects on import).
    - All pymongo exceptions are re-raised as `DatabaseError`.
"""

from pymongo import MongoClient
import pandas as pd
from datetime import datetime, date, time
from typing import List, Dict, Any, Optional, Set
#from pymongo.collection import Collection
#from pymongo import ASCENDING, DESCENDING

class DatabaseError(Exception):
    """Lightweight DB error to surface user-friendly messages in the UI."""
    pass

class MongoWrapper:
    """Typed access layer for MongoDB collections.

    Collections:
        - roster: player metadata
        - player_wellness: daily wellness entries
        - player_rpe: RPE post-session entries
        - sessions: training sessions and matches
        - pdp_structure: Personal Development Plan topic structures

    Responsibilities:
        - Provide pandas DataFrames for dashboards
        - Normalize types (`player_id`, dates, timestamps)
        - Compute derived fields (weeknumber, session_id, effective_minutes)
        - Wrap pymongo errors as DatabaseError

    Indexes (recommended):
        - roster: {player_id: 1}
        - player_wellness: {timestamp: 1}, {player_id: 1, timestamp: 1}
        - player_rpe: {session_id: 1}, {player_id: 1}, {timestamp: 1}
        - sessions: {session_id: 1} (unique), {team: 1, weeknumber: 1}
    """

    # --------------------
    # Database connection
    # --------------------

    def __init__(self, secrets: dict):
        username = secrets["mongo_username"]
        password = secrets["mongo_password"]
        cluster_url = secrets["mongo_cluster_url"]
        db_name = secrets["database_name"]

        # Construct the connection URI
        uri = f"mongodb+srv://{username}:{password}@{cluster_url}/?retryWrites=true&w=majority"

        # Connect to the client and database
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    # -----------------------
    # Roster data management
    # -----------------------

    def get_roster_df(self) -> pd.DataFrame:
        """Return the full roster as a pandas DataFrame.

        Returns:
            DataFrame: All players with fields `_id` excluded.

        Raises:
            DatabaseError: If the query fails.
        """
        try:
            data = list(self.db.roster.find({}, {"_id": 0}))
            return pd.DataFrame(data)
        except Exception as e:
            raise DatabaseError(f"Failed to load roster: {e}")
        
    def save_roster_df(self, df: pd.DataFrame) -> bool:
        """Replace the roster collection with a new DataFrame.

        Args:
            df: DataFrame with roster documents.

        Returns:
            True if the operation succeeded.

        Raises:
            DatabaseError: On MongoDB error.
        """
        try:
            self.db.roster.delete_many({})
            self.db.roster.insert_many(df.to_dict("records"))
            return True
        except Exception as e:
            raise DatabaseError(f"Failed to save roster: {e}")
        
    # -------------------------
    # PDP structure management
    # -------------------------

    def get_pdp_structure_for_team(self, team: str) -> dict:
        """Fetch the PDP structure for a given team.

        Args:
            team: Team code (e.g. "U21").

        Returns:
            dict: The PDP structure document, or None if not found.
        """
        try:
            return self.db["pdp_structure"].find_one({"_id": f"{team}_structure"})
        except Exception as e:
            raise DatabaseError(f"Failed to load PDP structure for {team}: {e}")

    def update_pdp_structure_for_team(self, team: str, updated_doc: dict) -> bool:
        """Save or update the PDP structure for a team.

        Args:
            team: Team code.
            updated_doc: Updated PDP structure document.

        Returns:
            True if the document was updated or inserted.
        """
        try:
            updated_doc["_id"] = f"{team}_structure"
            result = self.db["pdp_structure"].replace_one(
            {"_id": updated_doc["_id"]},
            updated_doc,
            upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            raise DatabaseError(f"Failed to update PDP structure for {team}: {e}")

    def list_all_team_structures(self) -> list:
        """List all available team-specific PDP structure IDs."""
        try:
            return [doc["_id"] for doc in self.db["pdp_structure"].find({}, {"_id": 1})]
        except Exception as e:
            raise DatabaseError(f"Failed to list PDP structures: {e}")

    # -------------------------    
    # Sessions data management
    # -------------------------

    def add_session(self, session_data: dict) -> bool:
        """Insert a new training session or match.

        Args:
            session_data: Dict with at least `date`, `team`, `session_type`, `duration`.

        Returns:
            True if insertion succeeded.

        Raises:
            DatabaseError: On MongoDB error.

        Notes:
            - `session_id` is generated as YYYYMMDD + team.
            - `weeknumber` is derived from ISO week of `date`.
        """
        try:
            # Ensure datetime format for MongoDB
            raw_date = session_data["date"]
            dt = raw_date if isinstance(raw_date, datetime) else datetime.combine(raw_date, datetime.min.time())
            session_data["date"] = dt

            # Compute additional fields
            session_data["weeknumber"] = dt.isocalendar().week
            session_data["session_id"] = dt.strftime("%Y%m%d") + session_data["team"]

            self.db.sessions.insert_one(session_data)
            return True
        except Exception as e:
            raise DatabaseError(f"Failed to save session: {e}")

    def get_sessions_df(self, team: str | None = None) -> pd.DataFrame:
        """Return all sessions, optionally filtered by team."""
        try:
            query = {"team": team} if team else {}
            docs = list(self.db.sessions.find(query, {"_id": 0}))
            return pd.DataFrame(docs)
        except Exception as e:
            raise DatabaseError(f"Failed to load sessions: {e}")

    # -------------------    
    # Wellness dashboard
    # -------------------

    # Get the data for the datatable view 
    def get_wellness_matrix(self, team: str | None = None) -> pd.DataFrame:
        """Return weekly average wellness per player in pivot form.

        Args:
            team: Optional filter ("U18" or "U21").

        Returns:
            DataFrame with player_name as rows and weeks as columns. 
            Cell values formatted as "avg_feeling | avg_sleeping".

        Raises:
            DatabaseError: On MongoDB error.

        Notes:
            - Season start hard-coded as first Monday of August 2025.
            - Week labels formatted as "W00", "W01", ...
        """
        try:
            # Load wellness entries
            wellness_docs = list(self.db.player_wellness.find({}, {"_id": 0}))
            wellness_df = pd.DataFrame(wellness_docs)
            wellness_df["player_id"] = wellness_df["player_id"].astype(str)
            wellness_df["date"] = pd.to_datetime(wellness_df["date"])

            # Set custom season start date (first Monday of August)
            season_start = pd.to_datetime("2025-08-04")  # Adjust if needed

            # Calculate season week number (0-based)
            wellness_df["season_week"] = ((wellness_df["date"] - season_start).dt.days // 7).astype(int)

            # Compute weekly averages
            weekly_avg = wellness_df.groupby(["player_id", "season_week"]).agg(
                avg_feeling=("feeling", "mean"),
                avg_sleeping=("sleep_hours", "mean")
            ).reset_index()

            # Round and format
            weekly_avg["combined"] = weekly_avg.apply(
                lambda row: f"{row['avg_feeling']:.1f} | {row['avg_sleeping']:.1f}", axis=1
            )

            # Load roster
            roster_docs = list(self.db.roster.find({}, {"_id": 0}))
            roster_df = pd.DataFrame(roster_docs)
            roster_df["player_id"] = roster_df["player_id"].astype(str)
            roster_df["player_name"] = roster_df["player_last_name"] + ", " + roster_df["player_first_name"]

            if team:
                roster_df = roster_df[roster_df["team"] == team]

            # Merge and pivot
            merged = pd.merge(
                weekly_avg,
                roster_df[["player_id", "player_name"]],
                on="player_id",
                how="inner"
            )

            # Use custom week labels like "W00", "W01", ..., "W39"
            merged["week_label"] = "W" + merged["season_week"].astype(str).str.zfill(2)

            compact_df = merged.pivot(index="player_name", columns="week_label", values="combined")
            return compact_df.reset_index()

        except Exception as e:
            raise DatabaseError(f"Failed to build compact wellness table: {e}")

    
    def get_today_wellness_entries(self, team: str, target_date: date = None):
        """Returns wellness entries for a given day (based on submission timestamp)."""
        if target_date is None:
            target_date = date.today()

        start_ts = datetime.combine(target_date, time.min)
        end_ts = datetime.combine(target_date, time.max)

        roster = self.get_roster_players(team=team)
        player_ids = [int(p["player_id"]) for p in roster]

        return list(self.db["player_wellness"].find({
            "player_id": {"$in": player_ids},
            "timestamp": {"$gte": start_ts, "$lte": end_ts}
        }))
    
    def get_daily_wellness_overview(self, team=None) -> pd.DataFrame:
        """Return pivot table with one row per player and one column per day showing 'feeling | sleep_hours'."""
        try:
            wellness_data = list(self.db.player_wellness.find())
            roster_data = list(self.db.roster.find())

            if not roster_data:
                return pd.DataFrame()

            wellness_df = pd.DataFrame(wellness_data)
            roster_df = pd.DataFrame(roster_data)

            # Ensure consistent types
            roster_df["player_id"] = roster_df["player_id"].astype(int)
            if not wellness_df.empty:
                wellness_df["player_id"] = wellness_df["player_id"].astype(int)
                wellness_df["date"] = pd.to_datetime(wellness_df["date"]).dt.date
                wellness_df["entry"] = wellness_df["feeling"].astype(str) + " | " + wellness_df["sleep_hours"].astype(str)

                # Merge with player names
                roster_df["player_name"] = roster_df["player_last_name"] + ", " + roster_df["player_first_name"]
                merged = wellness_df.merge(roster_df[["player_id", "player_name", "team"]], on="player_id", how="left")

                if team:
                    merged = merged[merged["team"] == team]

                # Pivot only available entries
                pivot = merged.pivot_table(
                    index="player_name",
                    columns="date",
                    values="entry",
                    aggfunc="first"
                )
            else:
                # No wellness entries yet
                pivot = pd.DataFrame()

            # --- Merge with full player list ---
            roster_df["player_name"] = roster_df["player_last_name"] + ", " + roster_df["player_first_name"]
            if team:
                roster_df = roster_df[roster_df["team"] == team]

            full_players = roster_df[["player_name"]].drop_duplicates().set_index("player_name")

            # Ensure all players are shown, even if they had no entries
            full_overview = full_players.join(pivot, how="left")
            full_overview = full_overview.fillna("–")  # or use "" for blanks

            # Final formatting
            full_overview = full_overview.sort_index(axis=0).sort_index(axis=1)
            full_overview.columns = full_overview.columns.astype(str)
            full_overview.index.name = None

            return full_overview

        except Exception as e:
            raise DatabaseError(f"Failed to generate wellness overview: {e}")
    
    # -------------------    
    # RPE fetchers
    # -------------------

    def get_rpe_loads(self, team: str | None = None) -> pd.DataFrame:
        """Aggregate weekly RPE loads per player.

        Args:
            team: Optional team filter.

        Returns:
            DataFrame with columns: player_id, player_name, team, week, load, acute, chronic, acr.

        Raises:
            DatabaseError: On MongoDB errors.

        Pipeline:
            - Lookup sessions and roster
            - Compute effective_minutes
            - Compute load = RPE * minutes
            - Group by player/week
            - Add rolling acute:chronic ratio
        """
        pipeline = [
            # Join with sessions collection
            {"$lookup": {
                "from": "sessions",
                "localField": "session_id",
                "foreignField": "session_id",
                "as": "session"
            }},
            {"$unwind": "$session"},

            # Optional team filter
            *([{"$match": {"session.team": team}}] if team else []),

            # Join with roster collection
            {"$lookup": {
                "from": "roster",
                "localField": "player_id",
                "foreignField": "player_id",
                "as": "player"
            }},
            {"$unwind": "$player"},

            # Add computed fields
            {"$addFields": {
                "player_name": {
                    "$concat": ["$player.player_last_name", ", ", "$player.player_first_name"]
                },
                "week": {"$isoWeek": "$session.date"},
                "effective_minutes": {
                    "$cond": {
                        "if": {"$gt": ["$training_minutes", 0]},
                        "then": "$training_minutes",
                        "else": "$session.duration"
                    }
                },
                "load": {
                    "$multiply": [
                        "$rpe_score",
                        {
                            "$cond": {
                                "if": {"$gt": ["$training_minutes", 0]},
                                "then": "$training_minutes",
                                "else": "$session.duration"
                            }
                        }
                    ]
                }
            }},

            # Group by player/week
            {"$group": {
                "_id": {
                    "player_id": "$player_id",
                    "player_name": "$player_name",
                    "team": "$session.team",
                    "week": "$week"
                },
                "load": {"$sum": "$load"}
            }},

            # Final shape
            {"$project": {
                "_id": 0,
                "player_id": "$_id.player_id",
                "player_name": "$_id.player_name",
                "team": "$_id.team",
                "week": "$_id.week",
                "load": 1
            }},
            {"$sort": {"player_name": 1, "week": 1}}
        ]

        df = pd.DataFrame(list(self.db.player_rpe.aggregate(pipeline)))

        if df.empty:
            return df

        # Calculate rolling metrics
        df = df.sort_values(by=["player_name", "week"])
        df["acute"] = df.groupby("player_name")["load"].transform(lambda x: x.rolling(1, min_periods=1).mean())
        df["chronic"] = df.groupby("player_name")["load"].transform(lambda x: x.shift().rolling(4, min_periods=1).mean())
        df["acr"] = (df["acute"] / df["chronic"]).round(2)

        return df
    
    def get_daily_rpe_overview(self, team: str | None = None) -> pd.DataFrame:
        """
        Returns a pivot table with one row per player (from roster),
        one column per date, and cell text "rpe_score | training_minutes".
        - Players with no entries are still shown.
        - If multiple entries exist for the same player/day, the latest by timestamp wins.
        - training_minutes defaults to the session's duration when missing/zero.
        """
        try:
            rpe_data = list(self.db.player_rpe.find())
            roster_data = list(self.db.roster.find())
            sessions_data = list(self.db.sessions.find())  # join target for default minutes

            if not roster_data:
                return pd.DataFrame()

            rpe_df = pd.DataFrame(rpe_data)
            roster_df = pd.DataFrame(roster_data)
            sessions_df = pd.DataFrame(sessions_data)

            # Ensure roster types and names
            roster_df["player_id"] = pd.to_numeric(roster_df["player_id"], errors="coerce").astype("Int64")
            roster_df["player_name"] = roster_df["player_last_name"] + ", " + roster_df["player_first_name"]

            # Apply optional team filter on the roster side
            if team:
                roster_df = roster_df[roster_df["team"] == team]

            # If no RPE yet, just return the player list (no date cols)
            if rpe_df.empty:
                return roster_df[["player_name"]].drop_duplicates().set_index("player_name")

            # Normalize RPE df
            rpe_df["player_id"] = pd.to_numeric(rpe_df["player_id"], errors="coerce").astype("Int64")
            rpe_df["date"] = pd.to_datetime(rpe_df["date"], errors="coerce").dt.date
            # Normalize timestamp (handles dict {"$date": ...} or strings)
            def _to_ts(x):
                if isinstance(x, dict) and "$date" in x:
                    return pd.to_datetime(x["$date"], errors="coerce")
                return pd.to_datetime(x, errors="coerce")
            rpe_df["timestamp"] = rpe_df.get("timestamp", pd.NaT).apply(_to_ts)

            # Normalize sessions df for default minutes
            if not sessions_df.empty:
                sessions_df = sessions_df[["session_id", "duration"]].copy()
                sessions_df["duration"] = pd.to_numeric(sessions_df["duration"], errors="coerce").fillna(0).astype(int)
            else:
                sessions_df = pd.DataFrame(columns=["session_id", "duration"])

            # Attach session duration to RPE
            rpe_df = rpe_df.merge(sessions_df, on="session_id", how="left", suffixes=("", "_session"))

            # training_minutes: prefer user-entered value if > 0, else session duration
            if "training_minutes" not in rpe_df.columns:
                rpe_df["training_minutes"] = pd.NA
            rpe_df["training_minutes"] = pd.to_numeric(rpe_df["training_minutes"], errors="coerce")
            rpe_df["training_minutes"] = rpe_df["training_minutes"].fillna(0)

            # Effective minutes
            rpe_df["effective_minutes"] = rpe_df.apply(
                lambda row: int(row["training_minutes"]) if row["training_minutes"] > 0
                else int(row["duration"]) if pd.notna(row["duration"]) and row["duration"] > 0
                else 0,
                axis=1
            )

            # De-duplicate by latest timestamp per (player_id, date)
            rpe_df = rpe_df.sort_values(["player_id", "date", "timestamp"], ascending=[True, True, True])
            rpe_latest = rpe_df.drop_duplicates(subset=["player_id", "date"], keep="last")

            # Build entry string
            rpe_latest["entry"] = rpe_latest["rpe_score"].astype(str) + " | " + rpe_latest["effective_minutes"].astype(int).astype(str)

            # Keep only players from roster (right join to show players with no entries)
            merged = rpe_latest.merge(
                roster_df[["player_id", "player_name"]],
                on="player_id",
                how="right"
            )

            # Pivot
            pivot = merged.pivot_table(
                index="player_name",
                columns="date",
                values="entry",
                aggfunc="first"
            )

            # Ensure all players appear
            full_players = roster_df[["player_name"]].drop_duplicates().set_index("player_name")
            full_overview = full_players.join(pivot, how="left")

            # Format
            full_overview = full_overview.fillna("–").sort_index(axis=0)
            if full_overview.shape[1] > 0:
                full_overview = full_overview.sort_index(axis=1)
                full_overview.columns = full_overview.columns.astype(str)
            full_overview.index.name = None

            return full_overview

        except Exception as e:
            raise DatabaseError(f"Failed to generate RPE overview: {e}")
        
    def get_player_rpe_df(self) -> pd.DataFrame:
        """Return all RPE registrations (current season stored in DB)."""
        try:
            proj = {"_id": 0, "player_id": 1, "session_id": 1, "date": 1,
                    "rpe_score": 1, "training_minutes": 1, "timestamp": 1}
            return pd.DataFrame(list(self.db.player_rpe.find({}, proj)))
        except Exception as e:
            raise DatabaseError(f"Failed to load RPE: {e}")

    # -------------------    
    # Session dashboard
    # -------------------
    
    def get_session_rpe_aggregates(self, team=None):
        """
        Aggregates RPE data for the session dashboard.
        Returns weekly total load, average player load, and per-session-type distributions.
        """
        pipeline = [
            {
                "$lookup": {
                    "from": "sessions",
                    "localField": "session_id",
                    "foreignField": "session_id",
                    "as": "session"
                }
            },
            {"$unwind": "$session"},
        ]

        if team:
            pipeline.append({"$match": {"session.team": team}})

        pipeline += [
            {
                "$project": {
                    "load": {
                        "$multiply": [
                            "$rpe_score",
                            {
                                "$cond": {
                                    "if": {"$gt": ["$training_minutes", 0]},
                                    "then": "$training_minutes",
                                    "else": "$session.duration"
                                }
                            }
                        ]
                    },
                    "weeknumber": "$session.weeknumber",
                    "session_type": "$session.session_type",
                    "session_id": "$session.session_id",
                    "player_id": 1,
                    "team": "$session.team"
                }
            },
            {
                "$group": {
                    "_id": {
                        "week": "$weeknumber",
                        "session_type": "$session_type"
                    },
                    "total_load": {"$sum": "$load"},
                    "sessions": {"$addToSet": "$session_id"},
                    "players": {"$addToSet": "$player_id"}
                }
            },
            {
                "$project": {
                    "week": "$_id.week",
                    "session_type": "$_id.session_type",
                    "total_load": 1,
                    "session_count": {"$size": "$sessions"},
                    "player_count": {"$size": "$players"},
                    "_id": 0
                }
            },
            {"$sort": {"week": 1, "session_type": 1}}
        ]

        return list(self.db["player_rpe"].aggregate(pipeline))
    
    # ---------------------
    # Player PDP functions
    # ---------------------

    def get_roster_players(self, team=None):
        """Return all players, optionally filtered by team."""
        try:
            query = {"team": team} if team else {}
            return list(self.db["roster"].find(query))
        except Exception as e:
            raise DatabaseError(f"Failed to fetch roster players: {e}")

    def get_latest_pdp_for_player(self, player_id):
        """Get the most recent PDP for a given player."""
        try:
            return self.db["player_pdp"].find_one(
                {"player_id": player_id},
                sort=[("last_updated", -1)]
            )
        except Exception as e:
            raise DatabaseError(f"Failed to fetch latest PDP for player {player_id}: {e}")

    def insert_new_pdp(self, pdp_data):
        """Insert a new PDP document into the collection."""
        try:
            return self.db["player_pdp"].insert_one(pdp_data).inserted_id
        except Exception as e:
            raise DatabaseError(f"Failed to insert new PDP: {e}")

    def get_all_pdps_for_player(self, player_id: str):
        """
        Returns all PDP documents for a given player_id, sorted by creation time (descending).
        """
        try:
            collection = self.db["player_pdp"]
            results = list(collection.find({"player_id": player_id}))
            return results
        except Exception as e:
            raise DatabaseError(f"Failed to fetch all PDPs for player {player_id}: {e}")

    # -----------------------------
    # Session attendance functions
    # -----------------------------

    def get_recent_sessions(
        self,
        team: str,
        limit: Optional[int] = 6,
        up_to_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Return recent sessions for a team (date DESC).

        Args:
            team: "U18" | "U21".
            limit: Max number of sessions to fetch; if None or <=0, no limit is applied.
            up_to_date: Optional cutoff date (include sessions on or before this date).

        Notes:
            - When `up_to_date` is provided, results are restricted to that day or earlier.
            - Callers can deduplicate by date after retrieval (e.g., keep latest per day).
            - When `limit` is provided, we fetch a bit extra (×2) to allow for date-dedup.
        """
        try:
            q: Dict[str, Any] = {"team": team}
            if up_to_date:
                end = datetime.combine(up_to_date, time.max)
                q["date"] = {"$lte": end}

            cur = (
                self.db["sessions"]
                .find(q, {"_id": 0})
                .sort([("date", -1)])  # DESC
            )

            # Apply limit only when requested
            if isinstance(limit, int) and limit > 0:
                cur = cur.limit(limit * 2)  # fetch extra for date-dedup

            records = list(cur)

            # Stable sort (handles string/iso dates as well)
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
            # No limit requested → return all
            return records

        except Exception as e:
            raise DatabaseError(f"Failed to fetch recent sessions: {e}") from e

    def get_roster_players(self, team: str) -> List[Dict[str, Any]]:
        """Return all players for a team from `roster`."""
        try:
            return list(self.db["roster"].find({"team": team}, {"_id": 0}))
        except Exception as e:
            raise DatabaseError(f"Failed to fetch roster: {e}") from e

    def upsert_attendance_full(
        self,
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
        # Prefer to derive valid IDs from the single source of truth in `constants`.
        try:
            from constants import ABSENCE_REASONS as ABSENCE_META  # [{"id","label","icon"}, ...]
            VALID_IDS: Set[str] = {r["id"] for r in ABSENCE_META}
        except Exception:
            # Fallback if constants cannot be imported (tests, tooling, etc.)
            VALID_IDS = {
                "injury",
                "individual",
                "physio_internal",
                "physio_external",
                "school",
                "holiday",
                "illness",
                "awol",
                "other_team",
            }

        # Optional: keep legacy IDs allowed for now to avoid breaking old callers.
        DEPRECATED_IDS: Set[str] = {"excused"}  # consider migrating or removing later

        def _norm_reason(reason: str) -> str:
            """Normalize a human-entered/old value to an ID-like form."""
            r = str(reason).strip().lower().replace(" ", "_")
            return r

        try:
            # Clean & dedupe present IDs
            present_clean = sorted(set(int(pid) for pid in present_ids))

            # Validate/normalize absentees
            absent_clean = []
            for item in absent_items:
                pid = int(item["player_id"])
                norm = _norm_reason(item["reason"])
                if norm not in VALID_IDS and norm not in DEPRECATED_IDS:
                    raise ValueError(f"Invalid absence reason '{item['reason']}' (normalized '{norm}') for player_id {pid}")
                absent_clean.append({"player_id": pid, "reason": norm})

            now = datetime.utcnow()
            self.db["attendance"].update_one(
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
        except Exception as e:
            raise DatabaseError(f"Failed to upsert attendance: {e}") from e