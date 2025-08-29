# Roster Management

Admin page to correct **names** and **team** for existing players.
> **Player additions or removals are not allowed here.**  
> Add/remove players directly in **MongoDB (Compass)** to preserve the GDPR-safe `player_id` key used across apps.

## What you can edit
- `player_first_name`
- `player_last_name`
- `team` (U18 / U21)

`player_id` is **locked** (read-only) and rows **cannot be added or removed**.

## How to use
1. Open **Team Roster Editor**.
2. Edit fields in-line.
3. Click **Save changes**. The app validates that the set of `player_id`s is unchanged before saving.

## Why this policy?
- `player_id` is the unique, **non-identifying** key used by the **Registration app** (players) and the **Dashboard app**.
- Changing IDs, adding, or removing rows here risks data mismatches across collections (wellness, RPE, sessions).

## How to add/remove a player (admin)
Use **MongoDB Compass** (or equivalent):
1. Open the `roster` collection.
2. Insert a new document with fields:
    - `player_id` (string or int, consistent with your setup)
    - `player_first_name`
    - `player_last_name`
    - `team` ("U18" or "U21")
3. Verify any dependent collections/processes if needed.

## Troubleshooting
- **Player missing in dashboards** → Check `team` and `player_id` type consistency.
- **Save blocked** → The app detected added/removed rows. Revert, or perform changes in MongoDB.
- **DB error** → The app shows specific error messages returned by the database layer.