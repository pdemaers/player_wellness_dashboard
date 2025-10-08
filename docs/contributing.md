# Contributing Guide

Welcome 👋 — thanks for helping improve this project.  
This document explains how to work safely with the codebase, especially during the **ongoing database layer refactor**.

---

## 📦 Branching Strategy

- **`main` branch**
  - Always stable, production-ready.
  - Streamlit Cloud deploys directly from `main`.
  - Hotfixes and small feature requests from users go here.

- **Feature / Refactor branches**
  - Create a branch for every new feature or refactor.
  - Naming:  
    - `feature/<short-name>` for new functionality  
    - `refactor/<short-name>` for structural changes  
    - `fix/<short-name>` for bugfixes  
  - Example:  
    ~~~bash
    git checkout -b refactor/db-layer
    ~~~

---

## 🔄 Workflow

### Everyday cycle

1) **Stay updated**
   ~~~bash
   git checkout main
   git pull origin main
   ~~~

2) **Create your branch**
   ~~~bash
   git checkout -b refactor/db-layer
   ~~~

3) **Make small, safe changes**
   - Move **one function at a time** (baby steps).
   - Keep public method signatures unchanged until all call sites are updated.
   - Run the app locally (`streamlit run main.py`) after each step.

4) **Commit often**
   ~~~bash
   git add -A
   git commit -m "refactor(roster): delegate get_player_names to RosterRepository"
   ~~~

5) **Push to GitHub**
   ~~~bash
   git push -u origin refactor/db-layer
   ~~~

---

## ✅ Baby-Step Refactor Checklist

- [ ] Public API unchanged (e.g. `mongo.get_player_names(...)` still works).
- [ ] Moved logic wrapped in a repository or service.
- [ ] App boots without exceptions.
- [ ] UI behavior unchanged on affected pages.
- [ ] No stray imports from views into `db/*`.

When this is true → commit!

---

## 🚦 Error Handling Guidelines

- **DatabaseError**  
  Raised when MongoDB operations fail.

- **ApplicationError**  
  Raised when application logic fails (bad data, formatting issues, invalid input).

- **AppError (base class)** *(optional later)*  
  Both `DatabaseError` and `ApplicationError` can inherit from this for unified catching.

**Example usage in a view**
~~~python
try:
    players = mongo.get_player_names(team="U21")
except DatabaseError as e:
    st.error(f"Database error: {e}")
except ApplicationError as e:
    st.error(f"Application error: {e}")
~~~

---

## 🔄 Syncing with `main`

While on your branch:
~~~bash
git fetch origin
git merge origin/main
~~~

Resolve conflicts if needed, then retest locally.

---

## 🛑 Rollback

If something goes wrong:

- Undo last commit (not pushed):
  ~~~bash
  git reset --hard HEAD~1
  ~~~

- Undo last commit (already pushed):
  ~~~bash
  git revert <commit-hash>
  ~~~

- Delete a failed branch entirely:
  ~~~bash
  git checkout main
  git branch -D refactor/db-layer
  ~~~

---

## 📝 Commit Message Style

Use **conventional commits**:

- `feat:` → new feature  
- `fix:` → bug fix  
- `refactor:` → restructuring, no behavior change  
- `docs:` → documentation only  
- `test:` → adding tests  
- `chore:` → maintenance  

**Examples**
- `refactor(roster): delegate get_player_names to RosterRepository`  
- `fix(attendance): correct date filter logic`  
- `feat(pdp): add priority flag to PDP topics`

---

## 🌱 Best Practices

- Keep PRs **small and focused** — easier to review and rollback.
- One responsibility per repo:
  - `RosterRepository` → roster-related queries
  - `SessionsRepository` → sessions
  - `WellnessRepository` → wellness, etc.
- Views (Streamlit pages) never talk directly to MongoDB — always via repos or services.
- Write docstrings with clear **Args/Returns**.

---

## 📋 Pull Request Template

**Summary**  
Explain the change in 2–3 sentences.

**Changes**
- [ ] Extracted `<method>` into `<RepoClass>`
- [ ] Delegated old method in `MongoWrapper`
- [ ] Verified `<affected page>` renders correctly

**Checklist**
- [ ] Tested locally with real data  
- [ ] No new linter warnings/errors  
- [ ] Commit messages follow conventional format  

---

## 🔀 Visual Branching (for reference)

~~~text
main ──●──────●────────●─────────────●─────────►
         \                \
          \                \__ (hotfix) merge into main
           \
            └── refactor/db-layer ─●──●──●─────► (PR → main)
~~~

# Documentation Standards

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