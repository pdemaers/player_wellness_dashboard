# db/repositories/wellness_repo.py
from __future__ import annotations
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

import pandas as pd
from pymongo.errors import PyMongoError

from ..base import BaseRepository
from ..errors import DatabaseError, ApplicationError


class WellnessDashboardRepository(BaseRepository):
    """
    Repository for wellness entries (collection: 'player_wellness') and
    the derived wellness views used by dashboards.
    """

    def __init__(self, db):
        super().__init__(db, "player_wellness")
        # We also read from 'roster' for joins
        self.roster = db["roster"]

    # ------------------ TODAY ENTRIES ------------------
    def get_today_wellness_entries(self, *, team: str, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Returns wellness entries for the given day for players in `team`."""
        if not team:
            raise ApplicationError("get_today_wellness_entries: 'team' is required.")
        if target_date is None:
            target_date = date.today()

        start_ts = datetime.combine(target_date, time.min)
        end_ts = datetime.combine(target_date, time.max)

        try:
            # fetch player_ids for team (minimal projection)
            player_ids = [int(d["player_id"]) for d in self.roster.find({"team": team}, {"_id": 0, "player_id": 1})]
            if not player_ids:
                return []

            return list(
                self.col.find(
                    {"player_id": {"$in": player_ids}, "timestamp": {"$gte": start_ts, "$lte": end_ts}},
                    {"_id": 0},
                )
            )
        except PyMongoError as e:
            raise DatabaseError(f"Failed to fetch today's wellness entries: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_today_wellness_entries: {e}") from e

    # ------------------ WEEKLY MATRIX (datatable) ------------------
    def get_wellness_matrix(self, *, team: Optional[str] = None) -> pd.DataFrame:
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
            wellness_docs = list(self.col.find({}, {"_id": 0}))
            wellness_df = pd.DataFrame(wellness_docs)
            if wellness_df.empty:
                return pd.DataFrame(columns=["player_name"])

            # Normalize types
            wellness_df["player_id"] = wellness_df["player_id"].astype(str)
            wellness_df["date"] = pd.to_datetime(wellness_df["date"], errors="coerce")

            # Get season start (import lazy to avoid repo↔utils coupling at import time)
            try:
                from utils.constants import REGISTRATION_START_DATE
                season_start = pd.to_datetime(REGISTRATION_START_DATE)
            except Exception:
                # fallback: August 1st current year
                season_start = pd.to_datetime(f"{datetime.now().year}-08-01")

            # Compute 0-based season week
            wellness_df["season_week"] = ((wellness_df["date"] - season_start).dt.days // 7).astype("Int64")

            # Weekly means
            weekly_avg = (
                wellness_df.groupby(["player_id", "season_week"], dropna=True)
                .agg(avg_feeling=("feeling", "mean"), avg_sleeping=("sleep_hours", "mean"))
                .reset_index()
            )

            if weekly_avg.empty:
                return pd.DataFrame(columns=["player_name"])

            weekly_avg["combined"] = weekly_avg.apply(
                lambda r: f"{r['avg_feeling']:.1f} | {r['avg_sleeping']:.1f}", axis=1
            )

            # Load roster & join
            roster_docs = list(self.roster.find({}, {"_id": 0, "player_id": 1, "player_first_name": 1, "player_last_name": 1, "team": 1}))
            roster_df = pd.DataFrame(roster_docs)
            if roster_df.empty:
                return pd.DataFrame(columns=["player_name"])

            roster_df["player_id"] = roster_df["player_id"].astype(str)
            roster_df["player_name"] = roster_df["player_last_name"].astype(str) + ", " + roster_df["player_first_name"].astype(str)

            if team:
                roster_df = roster_df[roster_df["team"] == team]

            merged = weekly_avg.merge(roster_df[["player_id", "player_name"]], on="player_id", how="inner")
            merged["week_label"] = "W" + merged["season_week"].astype(str).str.zfill(2)

            compact_df = merged.pivot(index="player_name", columns="week_label", values="combined")
            return compact_df.reset_index().sort_values("player_name")

        except PyMongoError as e:
            raise DatabaseError(f"Failed to build compact wellness table: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_wellness_matrix: {e}") from e

    # ------------------ DAILY OVERVIEW (pivot) ------------------
    def get_daily_wellness_overview(self, *, team: Optional[str] = None) -> pd.DataFrame:
        """Return pivot: rows players, columns dates, values 'feeling | sleep_hours'."""
        try:
            wellness_docs = list(self.col.find({}, {"_id": 0}))
            roster_docs = list(self.roster.find({}, {"_id": 0}))

            if not roster_docs:
                return pd.DataFrame()

            wellness_df = pd.DataFrame(wellness_docs)
            roster_df = pd.DataFrame(roster_docs)

            roster_df["player_id"] = pd.to_numeric(roster_df["player_id"], errors="coerce").astype("Int64")

            if not wellness_df.empty:
                wellness_df["player_id"] = pd.to_numeric(wellness_df["player_id"], errors="coerce").astype("Int64")
                wellness_df["date"] = pd.to_datetime(wellness_df["date"], errors="coerce").dt.date
                wellness_df["entry"] = wellness_df["feeling"].astype(str) + " | " + wellness_df["sleep_hours"].astype(str)

                roster_df["player_name"] = roster_df["player_last_name"].astype(str) + ", " + roster_df["player_first_name"].astype(str)
                merged = wellness_df.merge(roster_df[["player_id", "player_name", "team"]], on="player_id", how="left")

                if team:
                    merged = merged[merged["team"] == team]

                pivot = merged.pivot_table(index="player_name", columns="date", values="entry", aggfunc="first")
            else:
                pivot = pd.DataFrame()

            roster_df["player_name"] = roster_df["player_last_name"].astype(str) + ", " + roster_df["player_first_name"].astype(str)
            if team:
                roster_df = roster_df[roster_df["team"] == team]

            full_players = roster_df[["player_name"]].drop_duplicates().set_index("player_name")
            full_overview = full_players.join(pivot, how="left").fillna("–")
            full_overview = full_overview.sort_index(axis=0).sort_index(axis=1)
            full_overview.columns = full_overview.columns.astype(str)
            full_overview.index.name = None

            return full_overview

        except PyMongoError as e:
            raise DatabaseError(f"Failed to generate wellness overview: {e}") from e
        except Exception as e:
            raise ApplicationError(f"Unexpected error in get_daily_wellness_overview: {e}") from e