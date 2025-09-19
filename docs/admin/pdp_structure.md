# PDP Structure Management

This module provides an interface for managing the **Personal Development Plan (PDP) structure** for each team within the Player Wellness Dashboard.  
It allows coaches to edit categories, subcategories, and topics that form the PDP evaluation framework.

---

## Overview

The `render(mongo, user)` function displays a **Streamlit-based editor** that connects to the MongoDB backend, retrieves the current PDP structure for the selected team, and allows modifications through an interactive UI.

Key features:
- Team-specific PDP structures
- Category and subcategory navigation
- Topic creation, editing, and activation/deactivation
- Versioning and soft-delete logic for historical consistency

---

## Dependencies

- **External libraries**
  - `streamlit` — UI components
  - `pandas` — Table manipulation for topic editing
  - `uuid` — Unique IDs for topics
  - `datetime` — Timestamps for versioning
  - `copy.deepcopy` — Ensures structures are edited safely

- **Internal utilities**
  - `get_table_height` from `utils.ui_utils`
  - `team_selector` from `utils.team_selector`
  - `TEAMS` constant from `utils.constants`

---

## Workflow

1. **Team Selection**
   - Coaches choose a team via `team_selector(TEAMS)`.
   - If no team is selected, the UI prompts the user.

2. **Retrieve or Initialize PDP Structure**
   - Fetch structure from MongoDB using `mongo.get_pdp_structure_for_team(team)`.
   - If missing, an empty structure is initialized with version `1`.

3. **Ensure Unique Topic IDs**
   - Each topic is assigned a `topic_id` (`uuid4`) if missing.

4. **Category & Subcategory Selection**
   - Users pick a category and subcategory via dropdowns.
   - Active topics within that subcategory are displayed in an editable table.

5. **Topic Editing**
   - Topics are shown in a `st.data_editor` table with:
     - `name` (editable text)
     - `active` (checkbox)
   - Topics can be added dynamically.

6. **Soft Delete Mechanism**
   - If a topic is removed from the editor, it is not permanently deleted.
   - Instead, it is marked with `"active": False` to preserve history.

7. **Save Updated Structure**
   - Clicking **Save PDP Structure**:
     - Increments the `version`
     - Updates `created_at` timestamp
     - Persists changes via `mongo.update_pdp_structure_for_team(team)`

---

## Data Model

Each PDP structure document in MongoDB follows this schema:

```json
{
  "_id": "U21_structure",
  "version": 2,
  "created_at": "2025-09-19",
  "structure": {
    "CategoryName": {
      "SubcategoryName": [
        {
          "topic_id": "550e8400-e29b-41d4-a716-446655440000",
          "name": "Example Topic",
          "active": true
        },
        ...
      ]
    }
  }
}