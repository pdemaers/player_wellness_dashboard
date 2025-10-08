# Repositories (DB access layer)

These are thin classes that talk directly to MongoDB via `pymongo`.  
Business logic should live in Services (if present), not here.

## Roster
::: db.repositories.roster_repo.RosterRepository
    options:
      members:
        - get_player_names
        - get_roster_df
        - save_roster_df
      show_docstring_description: true

## Sessions
::: db.repositories.sessions_repo.SessionsRepository
    options:
      members:
        - add_session
        - get_sessions_df
      show_docstring_description: true

## Session Dashboard Repository

::: db.repositories.session_dashboard_repo
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - "!^_"

## PDP Structure
::: db.repositories.pdp_repo.PdpRepository
    options:
      members:
        - get_pdp_structure_for_team
        - update_pdp_structure_for_team
        - list_all_team_structures
      show_docstring_description: true

## Player PDP
::: db.repositories.player_pdp_repo.PlayerPdpRepository
    options:
      members:
        - get_latest_pdp_for_player
        - get_all_pdps_for_player
        - insert_new_pdp
      show_docstring_description: true

