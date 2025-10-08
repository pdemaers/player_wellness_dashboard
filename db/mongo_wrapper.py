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
from typing import List, Dict, Any, Optional, Set, Union
#from pymongo.collection import Collection
#from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from .errors import DatabaseError, ApplicationError
from .connection import get_db
from .repositories.roster_repo import RosterRepository
from .repositories.sessions_repo import SessionsRepository
from .repositories.pdp_repo import PdpRepository
from .repositories.player_pdp_repo import PlayerPdpRepository
from .repositories.injury_repo import InjuryRepository
from .repositories.wellness_dash_repo import WellnessDashboardRepository
from .repositories.rpe_dashboard_repo import RpeDashboardRepository
from .repositories.attendance_repo import AttendanceRepository
from .repositories.session_dashboard_repo import SessionsDashboardRepository



from utils.constants import NameStyle

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

    def __init__(self, secrets: Dict[str, Any]):
        self.db = get_db(secrets)
        # compose repos as you add them
        self.roster_repo = RosterRepository(self.db)
        self.sessions_repo = SessionsRepository(self.db)
        self.pdp_repo = PdpRepository(self.db)
        self.player_pdp_repo = PlayerPdpRepository(self.db)
        self.injury_repo = InjuryRepository(self.db)
#        self.session_dashboard_repo = SessionsRepository(self.db)  # reuse sessions repo for session dashboard      
        self.wellness_dash_repo = WellnessDashboardRepository(self.db)  # wellness dashboard repo
        self.rpe_dash_repo = RpeDashboardRepository(self.db)  # RPE dashboard repo
        self.attendance_repo = AttendanceRepository(self.db)  # attendance repo
        self.session_dashboard_repo = SessionsDashboardRepository(self.db)  # session dashboard repo



    # -----------------------
    # Roster data management
    # -----------------------

    def get_roster_df(self, team: Optional[str] = None) -> pd.DataFrame:
        """Pass-through to RosterRepository.get_roster_df()."""
        try:
            return self.roster_repo.get_roster_df(team=team)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.get_roster_df unexpected error: {e}") from e


        
    def save_roster_df(self, df: pd.DataFrame, *, team: str) -> bool:
        """Replace ONLY the selected team's roster with df."""
        try:
            if not team:
                raise ApplicationError("save_roster_df: 'team' is required in the team-scoped workflow.")
            return self.roster_repo.save_roster_df(df=df, team=team)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.save_roster_df unexpected error: {e}") from e



    def get_player_names(
        self,
        team: str,
        style: NameStyle = "LAST_FIRST",
        include_inactive: bool = False,
        sort_by_name: bool = True,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Pass-through to :py:meth:`db.repositories.roster_repo.RosterRepository.get_player_names`.

        Notes:
            This wrapper is kept for backward compatibility while migrating call sites.
            Prefer using the repository/service directly in new code.
        """
        try:
            return self.roster_repo.get_player_names(
                team=team,
                style=style,
                include_inactive=include_inactive,
                sort_by_name=sort_by_name,
                fields=fields,
            )
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.get_player_names unexpected error: {e}") from e



    # -------------------------    
    # Session data management
    # -------------------------

    def add_session(self, session_data: dict) -> bool:
        """Pass-through to SessionsRepository.add_session."""
        try:
            return self.sessions_repo.add_session(session_data=session_data)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.add_session unexpected error: {e}") from e
    


    def get_sessions_df(self, team: Optional[str] = None) -> pd.DataFrame:
        """Pass-through to SessionsRepository.get_sessions_df (team-only filter to match old behavior)."""
        try:
            return self.sessions_repo.get_sessions_df(team=team)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.get_sessions_df unexpected error: {e}") from e



    # -------------------------
    # PDP structure management
    # -------------------------

    def get_pdp_structure_for_team(self, team: str) -> dict:
        try:
            return self.pdp_repo.get_pdp_structure_for_team(team=team)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.get_pdp_structure_for_team unexpected error: {e}") from e




    def update_pdp_structure_for_team(self, team: str, updated_doc: dict) -> bool:
        try:
            return self.pdp_repo.update_pdp_structure_for_team(team=team, updated_doc=updated_doc)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.update_pdp_structure_for_team unexpected error: {e}") from e
        


    def list_all_team_structures(self) -> list[str]:
        try:
            return self.pdp_repo.list_all_team_structures()
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.list_all_team_structures unexpected error: {e}") from e




    # -------------------    
    # Wellness dashboard
    # -------------------

    # Get the data for the datatable view 
    def get_wellness_matrix(self, team: str | None = None) -> pd.DataFrame:
        try:
            return self.wellness_dash_repo.get_wellness_matrix(team=team)
        except (DatabaseError, ApplicationError):
            raise



    def get_today_wellness_entries(self, team: str, target_date: date = None):
        try:
            return self.wellness_dash_repo.get_today_wellness_entries(team=team, target_date=target_date)
        except (DatabaseError, ApplicationError):
            raise
    


    def get_daily_wellness_overview(self, team=None) -> pd.DataFrame:
        try:
            return self.wellness_dash_repo.get_daily_wellness_overview(team=team)
        except (DatabaseError, ApplicationError):
            raise
    
    # -------------------    
    # RPE dashboard
    # -------------------

    def get_rpe_loads(self, team: str | None = None) -> pd.DataFrame:
        try:
            return self.rpe_dash_repo.get_rpe_loads(team=team)
        except (DatabaseError, ApplicationError):
            raise
    

    def get_daily_rpe_overview(self, team: str | None = None) -> pd.DataFrame:
        try:
            return self.rpe_dash_repo.get_daily_rpe_overview(team=team)
        except (DatabaseError, ApplicationError):
            raise
        

    def get_player_rpe_df(self) -> pd.DataFrame:
        try:
            return self.rpe_dash_repo.get_player_rpe_df()
        except (DatabaseError, ApplicationError):
            raise

    # -------------------    
    # Session dashboard
    # -------------------
    
    def get_session_rpe_aggregates(self, team=None):
        try:
            return self.rpe_dash_repo.get_session_rpe_aggregates(team=team)
        except (DatabaseError, ApplicationError):
            raise
            
    # ---------------------
    # Player PDP functions
    # ---------------------

    def get_latest_pdp_for_player(self, player_id):
        try:
            return self.player_pdp_repo.get_latest_pdp_for_player(player_id=player_id)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.get_latest_pdp_for_player unexpected error: {e}") from e



    def insert_new_pdp(self, pdp_data: dict):
        try:
            return self.player_pdp_repo.insert_new_pdp(pdp_data=pdp_data)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.insert_new_pdp unexpected error: {e}") from e



    def get_all_pdps_for_player(self, player_id: int):
        try:
            return self.player_pdp_repo.get_all_pdps_for_player(player_id=player_id)
        except (DatabaseError, ApplicationError):
            raise
        except Exception as e:
            raise ApplicationError(f"mongo_wrapper.get_all_pdps_for_player unexpected error: {e}") from e


    # -----------------------------
    # Session attendance functions
    # -----------------------------

    def get_recent_sessions(
        self,
        team: str,
        limit: Optional[int] = 6,
        up_to_date: Optional[date] = None,
        session_type: Union[str, List[str], None] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent sessions for a team (date DESC).

        Args:
            team: "U18" | "U21".
            limit: Max number of sessions to fetch. If None or <=0, no limit is applied.
            up_to_date: Include sessions on or before this date.
            session_type: Filter by a single type (e.g., "M") or by multiple types (e.g., ["T1","T2","T3","T4"]).
        """
        try:
            return self.attendance_repo.get_recent_sessions(
                team=team, limit=limit, up_to_date=up_to_date, session_type=session_type
            )
        except (DatabaseError, ApplicationError):
            raise



    def upsert_attendance_full(
        self,
        session_id: str,
        team: str,
        present_ids: List[int],
        absent_items: List[Dict[str, Any]],
        user: str,
    ) -> None:
        try:
            return self.attendance_repo.upsert_attendance_full(
                session_id=session_id,
                team=team,
                present_ids=present_ids,
                absent_items=absent_items,
                user=user,
            )
        except (DatabaseError, ApplicationError):
            raise
        


    def save_match_minutes_once(
        self,
        session_id: str,
        team: str,
        minutes_items: List[Dict[str, Any]],
        user: str,
    ) -> None:
        try:
            return self.attendance_repo.save_match_minutes_once(
                session_id=session_id, team=team, minutes_items=minutes_items, user=user
            )
        except (DatabaseError, ApplicationError):
            raise
    
    # -----------------------------
    # Injury management functions
    # -----------------------------

    def insert_player_injury(self, injury_doc: dict) -> str:
        try:
            return self.injury_repo.insert_player_injury(injury_doc=injury_doc)
        except (DatabaseError, ApplicationError):
            raise



    def get_player_injuries(self, player_id: int, sort_desc: bool = True) -> list:
        try:
            return self.injury_repo.get_player_injuries(player_id=int(player_id), sort_desc=sort_desc)
        except (DatabaseError, ApplicationError):
            raise



    def get_injury_by_id(self, injury_id: str):
        try:
            return self.injury_repo.get_injury_by_id(injury_id=injury_id)
        except (DatabaseError, ApplicationError):
            raise



    def add_treatment_session(self, injury_id: str, treatment_session: dict, current_status: str, updated_by: str) -> bool:
        try:
            return self.injury_repo.add_treatment_session(
                injury_id=injury_id,
                treatment_session=treatment_session,
                current_status=current_status,
                updated_by=updated_by,
            )
        except (DatabaseError, ApplicationError):
            raise

    def add_injury_comment(self, injury_id: str, text: str, author_email: str) -> bool:
        try:
            return self.injury_repo.add_injury_comment(injury_id=injury_id, text=text, author_email=author_email)
        except (DatabaseError, ApplicationError):
            raise