# Contributing & Documentation Standards

## Docstrings
- **Style**: Google-style docstrings.
- **Type hints**: required on all public functions.
- **Sections**: `Args`, `Returns`, `Raises`, `Notes`, `Examples` (when useful).

### Example
```python
def get_today_wellness_entries(team: str, target_date: date | None = None) -> list[dict]:
    """Return wellness entries submitted on a specific day.

    Args:
        team: "U18" or "U21".
        target_date: Calendar date; defaults to today (Europe/Brussels).

    Returns:
        List of documents with keys: `_id`, `player_id`, `date`, `feeling`, `sleep_hours`, `timestamp`.

    Raises:
        DatabaseError: On MongoDB errors.
        ValueError: If `team` is invalid.

    Notes:
        Uses inclusive [start_of_day, end_of_day] window.
    """
```

## Linting
- Add `pydocstyle` or `ruff` docstring rules if desired.

## Local Docs Preview
```bash
pip install -r requirements-docs.txt
mkdocs serve
```

## Deploy
We use GitHub Actions to deploy to GitHub Pages on pushes to `main`.