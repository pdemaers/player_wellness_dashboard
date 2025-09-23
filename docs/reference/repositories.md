# Repositories (DB access layer)

These are thin classes that talk directly to MongoDB via `pymongo`.  
Business logic should live in Services (if present), not here.

## Roster
::: db.repositories.roster_repo.RosterRepository
    options:
      members:
        - get_player_names
      show_docstring_description: true

## Sessions
::: db.repositories.sessions_repo.SessionsRepository

## Attendance / Match Minutes
::: db.repositories.attendance_repo.MatchMinutesRepository