from pymongo import MongoClient
import pandas as pd
from datetime import datetime, date, time

class DatabaseError(Exception):
    pass

class MongoWrapper:

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
        try:
            data = list(self.db.roster.find({}, {"_id": 0}))
            return pd.DataFrame(data)
        except Exception as e:
            raise DatabaseError(f"Failed to load roster: {e}")
        
    def save_roster_df(self, df: pd.DataFrame) -> bool:
        """Replace the full roster collection with updated DataFrame."""
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
        """Fetch the PDP structure for a given team (e.g. 'U21')."""
        return self.db["pdp_structure"].find_one({"_id": f"{team}_structure"})

    def update_pdp_structure_for_team(self, team: str, updated_doc: dict) -> bool:
        """Save or overwrite the PDP structure for a given team."""
        updated_doc["_id"] = f"{team}_structure"
        result = self.db["pdp_structure"].replace_one(
            {"_id": updated_doc["_id"]},
            updated_doc,
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    def list_all_team_structures(self) -> list:
        """List all available team-specific PDP structure IDs."""
        return [doc["_id"] for doc in self.db["pdp_structure"].find({}, {"_id": 1})]

    # -------------------------    
    # Sessions data management
    # -------------------------

    def add_session(self, session_data: dict) -> bool:
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
    # RPE dashboard
    # -------------------

    def get_rpe_loads(self, team=None):
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
        query = {"team": team} if team else {}
        return list(self.db["roster"].find(query))

    def get_latest_pdp_for_player(self, player_id):
        """Get the most recent PDP for a given player."""
        return self.db["player_pdp"].find_one(
            {"player_id": player_id},
            sort=[("last_updated", -1)]
        )

    def insert_new_pdp(self, pdp_data):
        """Insert a new PDP document into the collection."""
        return self.db["player_pdp"].insert_one(pdp_data).inserted_id
    

    def get_all_pdps_for_player(self, player_id: str):
        """
        Returns all PDP documents for a given player_id, sorted by creation time (descending).
        """
        collection = self.db["player_pdp"]
        results = list(collection.find({"player_id": player_id}))
        return results
