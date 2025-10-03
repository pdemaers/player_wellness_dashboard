# db/repositories/rpe_repo.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
from pymongo.errors import PyMongoError

from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError


class RpeDashboardRepository(BaseRepository):
    """Repository for RPE reads/aggregations (collection: 'player_rpe')."""

    def __init__(self, db):
        super().__init__(db, "player_rpe")
        self.sessions = db["sessions"]
        self.roster = db["roster"]



    # ---------------- Aggregate weekly loads + A:C ratio ----------------
    def get_rpe_loads(self, *, team: Optional[str] = None) -> pd.DataFrame:
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
        try:
            pipeline: List[Dict[str, Any]] = [
                {"$lookup": {
                    "from": "sessions",
                    "localField": "session_id",
                    "foreignField": "session_id",
                    "as": "session"
                }},
                {"$unwind": "$session"},
            ]

            if team:
                pipeline.append({"$match": {"session.team": team}})

            pipeline.extend([
                {"$lookup": {
                    "from": "roster",
                    "localField": "player_id",
                    "foreignField": "player_id",
                    "as": "player"
                }},
                {"$unwind": "$player"},
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
                {"$group": {
                    "_id": {
                        "player_id": "$player_id",
                        "player_name": "$player_name",
                        "team": "$session.team",
                        "week": "$week"
                    },
                    "load": {"$sum": "$load"}
                }},
                {"$project": {
                    "_id": 0,
                    "player_id": "$_id.player_id",
                    "player_name": "$_id.player_name",
                    "team": "$_id.team",
                    "week": "$_id.week",
                    "load": 1
                }},
                {"$sort": {"player_name": 1, "week": 1}}
            ])

            df = pd.DataFrame(list(self.col.aggregate(pipeline)))
            if df.empty:
                return df

            # Rolling metrics (per player, ordered by week)
            df = df.sort_values(by=["player_name", "week"])
            df["acute"] = df.groupby("player_name")["load"].transform(lambda x: x.rolling(1, min_periods=1).mean())
            df["chronic"] = df.groupby("player_name")["load"].transform(lambda x: x.shift().rolling(4, min_periods=1).mean())
            df["acr"] = (df["acute"] / df["chronic"]).round(2)

            return df

        except PyMongoError as e:
            raise DatabaseError(f"Failed to fetch RPE loads: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_rpe_loads: {e}") from e



    # ---------------- Daily overview pivot ----------------
    def get_daily_rpe_overview(self, *, team: Optional[str] = None) -> pd.DataFrame:
        """
        Returns a pivot table with one row per player (from roster),
        one column per date, and cell text "rpe_score | training_minutes".
        - Players with no entries are still shown.
        - If multiple entries exist for the same player/day, the latest by timestamp wins.
        - training_minutes defaults to the session's duration when missing/zero.
        """
        try:
            rpe_data = list(self.col.find({}, {"_id": 0}))
            roster_data = list(self.roster.find({}, {"_id": 0}))
            sessions_data = list(self.sessions.find({}, {"_id": 0, "session_id": 1, "duration": 1}))

            if not roster_data:
                return pd.DataFrame()

            rpe_df = pd.DataFrame(rpe_data)
            roster_df = pd.DataFrame(roster_data)
            sessions_df = pd.DataFrame(sessions_data)

            # roster normalization
            roster_df["player_id"] = pd.to_numeric(roster_df["player_id"], errors="coerce").astype("Int64")
            roster_df["player_name"] = roster_df["player_last_name"].astype(str) + ", " + roster_df["player_first_name"].astype(str)
            if team:
                roster_df = roster_df[roster_df["team"] == team]

            if rpe_df.empty:
                # Return player index (no date cols)
                return roster_df[["player_name"]].drop_duplicates().set_index("player_name")

            # rpe normalization
            rpe_df["player_id"] = pd.to_numeric(rpe_df["player_id"], errors="coerce").astype("Int64")
            rpe_df["date"] = pd.to_datetime(rpe_df["date"], errors="coerce").dt.date

            def _to_ts(x):
                if isinstance(x, dict) and "$date" in x:
                    return pd.to_datetime(x["$date"], errors="coerce")
                return pd.to_datetime(x, errors="coerce")

            rpe_df["timestamp"] = rpe_df.get("timestamp", pd.NaT).apply(_to_ts)

            # sessions for default minutes
            if sessions_df.empty:
                sessions_df = pd.DataFrame(columns=["session_id", "duration"])
                sessions_df["duration"] = pd.Series(dtype="Int64")
            else:
                sessions_df["duration"] = pd.to_numeric(sessions_df["duration"], errors="coerce").fillna(0).astype(int)

            rpe_df = rpe_df.merge(sessions_df, on="session_id", how="left", suffixes=("", "_session"))

            # effective minutes: prefer training_minutes>0 else session duration
            if "training_minutes" not in rpe_df.columns:
                rpe_df["training_minutes"] = pd.NA
            rpe_df["training_minutes"] = pd.to_numeric(rpe_df["training_minutes"], errors="coerce").fillna(0)

            rpe_df["effective_minutes"] = rpe_df.apply(
                lambda row: int(row["training_minutes"]) if row["training_minutes"] > 0
                else int(row["duration"]) if pd.notna(row["duration"]) and row["duration"] > 0
                else 0,
                axis=1
            )

            # keep latest per (player_id, date)
            rpe_df = rpe_df.sort_values(["player_id", "date", "timestamp"])
            rpe_latest = rpe_df.drop_duplicates(subset=["player_id", "date"], keep="last")

            rpe_latest["entry"] = rpe_latest["rpe_score"].astype(str) + " | " + rpe_latest["effective_minutes"].astype(int).astype(str)

            merged = rpe_latest.merge(roster_df[["player_id", "player_name"]], on="player_id", how="right")

            pivot = merged.pivot_table(index="player_name", columns="date", values="entry", aggfunc="first")

            # ensure all players appear
            full_players = roster_df[["player_name"]].drop_duplicates().set_index("player_name")
            full_overview = full_players.join(pivot, how="left").fillna("–")

            # sort rows/cols and tidy
            full_overview = full_overview.sort_index(axis=0)
            if full_overview.shape[1] > 0:
                full_overview = full_overview.sort_index(axis=1)
                full_overview.columns = full_overview.columns.astype(str)
            full_overview.index.name = None

            return full_overview

        except PyMongoError as e:
            raise DatabaseError(f"Failed to generate RPE overview: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_daily_rpe_overview: {e}") from e



    # ---------------- Raw RPE df ----------------
    def get_player_rpe_df(self) -> pd.DataFrame:
        """Return all RPE registrations (projected columns)."""
        try:
            proj = {
                "_id": 0,
                "player_id": 1,
                "session_id": 1,
                "date": 1,
                "rpe_score": 1,
                "training_minutes": 1,
                "timestamp": 1,
            }
            return pd.DataFrame(list(self.col.find({}, proj)))
        except PyMongoError as e:
            raise DatabaseError(f"Failed to load RPE: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_player_rpe_df: {e}") from e
        


    # ---------------- Session dashboard aggregates ----------------
    def get_session_rpe_aggregates(self, *, team: str | None = None) -> list[dict]:
        """
        Aggregates RPE data for the session dashboard.

        Returns a list of dicts with:
          - week (int)
          - session_type (str)
          - total_load (float)
          - session_count (int)
          - player_count (int)
        """
        try:
            pipeline: list[dict] = [
                {
                    "$lookup": {
                        "from": "sessions",
                        "localField": "session_id",
                        "foreignField": "session_id",
                        "as": "session",
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
                                        "else": "$session.duration",
                                    }
                                },
                            ]
                        },
                        "weeknumber": "$session.weeknumber",
                        "session_type": "$session.session_type",
                        "session_id": "$session.session_id",
                        "player_id": 1,
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "week": "$weeknumber",
                            "session_type": "$session_type",
                        },
                        "total_load": {"$sum": "$load"},
                        "sessions": {"$addToSet": "$session_id"},
                        "players": {"$addToSet": "$player_id"},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "week": "$_id.week",
                        "session_type": "$_id.session_type",
                        "total_load": 1,
                        "session_count": {"$size": "$sessions"},
                        "player_count": {"$size": "$players"},
                    }
                },
                {"$sort": {"week": 1, "session_type": 1}},
            ]

            return list(self.col.aggregate(pipeline))

        except PyMongoError as e:
            from ..errors import DatabaseError
            raise DatabaseError(f"Failed to fetch session RPE aggregates: {e}") from e
        except Exception as e:
            from ..errors import ApplicationError
            raise ApplicationError(f"Unexpected error in get_session_rpe_aggregates: {e}") from e