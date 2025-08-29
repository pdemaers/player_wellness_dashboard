# Roster Management

Manage player rosters for U18/U21.

## Tasks
- **Add** player: `player_id` (string), `player_first_name`, `player_last_name`, `team`.
- **Edit** player details.
- **Bulk update** via the table → **Save changes**.

## Best practices
- Keep `player_id` aligned with the Registration app (string).
- Use consistent name casing (helps matching + charts).
- Review before season start and transfer windows.

## Troubleshooting
- Player missing from dashboards → verify `team` and `player_id` type.