# RPE Data Quality (Admin)

!!! note "Admin Only"
    This page is only accessible for users with **admin** permissions.  
    It is intended to monitor the quality and completeness of RPE registrations,
    not player performance.

## Purpose

The RPE Data Quality view helps staff ensure that training load data
is consistent and reliable across the season.  
It highlights compliance issues, duplicates, and anomalies that could
affect decision-making based on RPE.

## Features

- **Team selector**: Switch between U18 and U21 squads.
- **Exempt players**: Long-term injured or absent players are excluded
  automatically (from `constants.EXEMPT`). Admins can override this list.
- **Summary metrics**:
  - Team compliance rate
  - Total number of sessions in the season
  - Number of duplicate entries
  - Number of anomaly rows
- **Player compliance**:
  - Shows expected vs. actual RPE registrations per player
  - Highlights players with low compliance rates
- **Compliance trend**:
  - Weekly cumulative team compliance percentage
  - Useful to track whether compliance improves or declines over the season
- **Data quality checks**:
  - Duplicate RPE entries per player (session- or date-based)
  - Anomalies such as:
    - Missing session ID
    - Orphan session ID (no matching session found)
    - Timestamps outside the allowed session window
- **Exports**: All tables can be downloaded as CSV for reporting.

## Typical Use

- **Weekly review**: Admin checks compliance rates and anomalies.
- **Staff reporting**: Export tables and share with coaches to remind players
  about consistent RPE entry.
- **Data reliability**: Ensures that load analysis dashboards are based on
  complete and trustworthy information.