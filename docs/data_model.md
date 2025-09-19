# Data Model

_Generated on 2025-09-19 15:15._

This page documents the MongoDB collections, common field types (sampled), and indexes. Relationships are inferred heuristically from `*_id` fields.

---

## Collections Overview

| Collection | Approx. Docs | Notes |
|---|---:|---|
| `attendance` | 29 |  |
| `match_minutes` | 1 |  |
| `meal_diary_entries` | 102 |  |
| `pdp_structure` | 2 |  |
| `player_injuries` | 2 |  |
| `player_pdp` | 1 |  |
| `player_rpe` | 764 |  |
| `player_rpe_archive_20250904_160822` | 75 |  |
| `player_rpe_archive_20250910_150528` | 14 |  |
| `player_wellness` | 952 |  |
| `player_wellness_archive_20250910_151750` | 125 |  |
| `roster` | 44 |  |
| `sessions` | 70 |  |
| `weight_registration` | 24 |  |


---

## `attendance`

**Estimated documents:** 29

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 29 | ObjectId |
| `absent` | 29 | array |
| `created` | 29 | datetime |
| `last_updated` | 29 | datetime |
| `present` | 29 | array |
| `session_id` | 29 | string |
| `team` | 29 | string |
| `user` | 29 | string |

### Indexes

- 

---

## `match_minutes`

**Estimated documents:** 1

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 1 | ObjectId |
| `created` | 1 | datetime |
| `last_updated` | 1 | datetime |
| `minutes` | 1 | array |
| `session_id` | 1 | string |
| `team` | 1 | string |
| `user` | 1 | string |

### Indexes

- 

---

## `meal_diary_entries`

**Estimated documents:** 102

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 102 | ObjectId |
| `day_type` | 102 | null, string |
| `meal_date` | 102 | int |
| `meal_elements` | 102 | array |
| `meal_type` | 102 | null, string |
| `player_id` | 102 | int, null, string |

### Indexes

- 

---

## `pdp_structure`

**Estimated documents:** 2

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 2 | string |
| `created_at` | 2 | string |
| `structure` | 2 | object |
| `version` | 2 | int |

### Indexes

- 

---

## `player_injuries`

**Estimated documents:** 2

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 2 | ObjectId |
| `comments` | 2 | array |
| `created_at` | 2 | datetime |
| `created_by` | 2 | string |
| `description` | 2 | string |
| `diagnostic` | 2 | string |
| `doctor_name` | 2 | string |
| `doctor_visit_date` | 2 | string |
| `imagery_type` | 2 | string |
| `injury_date` | 2 | string |
| `player_id` | 2 | int |
| `projected_duration` | 2 | string |
| `team` | 2 | string |
| `updated_at` | 2 | datetime |
| `updated_by` | 2 | string |

### Indexes

- 

---

## `player_pdp`

**Estimated documents:** 1

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 1 | ObjectId |
| `created` | 1 | string |
| `created_by` | 1 | string |
| `data` | 1 | object |
| `last_updated` | 1 | string |
| `last_updated_by` | 1 | string |
| `player_id` | 1 | string |
| `team` | 1 | string |

### Indexes

- 

---

## `player_rpe`

**Estimated documents:** 764

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 500 | ObjectId |
| `date` | 500 | string |
| `individual_session` | 500 | bool |
| `player_id` | 500 | int |
| `rpe_score` | 500 | int |
| `session_id` | 500 | string |
| `timestamp` | 500 | datetime |
| `training_minutes` | 500 | int |

### Indexes

- 
- 

---

## `player_rpe_archive_20250904_160822`

**Estimated documents:** 75

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_archived_at` | 75 | datetime |
| `_id` | 75 | ObjectId |
| `_reason` | 75 | string |
| `date` | 75 | string |
| `individual_session` | 75 | bool |
| `player_id` | 75 | int |
| `rpe_score` | 75 | int |
| `session_id` | 75 | string |
| `timestamp` | 75 | datetime |
| `training_minutes` | 75 | int |

### Indexes

- 

---

## `player_rpe_archive_20250910_150528`

**Estimated documents:** 14

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_archived_at` | 14 | datetime |
| `_id` | 14 | ObjectId |
| `_reason` | 14 | string |
| `date` | 14 | string |
| `individual_session` | 14 | bool |
| `player_id` | 14 | int |
| `rpe_score` | 14 | int |
| `session_id` | 14 | string |
| `timestamp` | 14 | datetime |
| `training_minutes` | 14 | int |

### Indexes

- 

---

## `player_wellness`

**Estimated documents:** 952

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 500 | ObjectId |
| `date` | 500 | string |
| `feeling` | 500 | float, int, null |
| `player_id` | 500 | int |
| `session_id` | 500 | string |
| `sleep_hours` | 500 | float |
| `timestamp` | 500 | datetime |

### Indexes

- 
- 

---

## `player_wellness_archive_20250910_151750`

**Estimated documents:** 125

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_archived_at` | 125 | datetime |
| `_id` | 125 | ObjectId |
| `_reason` | 125 | string |
| `date` | 125 | string |
| `feeling` | 125 | float, int, null |
| `player_id` | 125 | int |
| `session_id` | 125 | string |
| `sleep_hours` | 125 | float |
| `timestamp` | 125 | datetime |

### Indexes

- 

---

## `roster`

**Estimated documents:** 44

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 44 | ObjectId |
| `player_first_name` | 44 | string |
| `player_id` | 44 | int |
| `player_last_name` | 44 | string |
| `team` | 44 | string |

### Indexes

- 
- 

---

## `sessions`

**Estimated documents:** 70

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 70 | ObjectId |
| `date` | 70 | datetime |
| `duration` | 70 | int |
| `session_id` | 70 | string |
| `session_type` | 70 | string |
| `team` | 70 | string |
| `weeknumber` | 70 | int |

### Indexes

- 
- 

---

## `weight_registration`

**Estimated documents:** 24

### Fields (sampled types)

| Field | Presence | Types |
|---|---:|---|
| `_id` | 24 | ObjectId |
| `day_type` | 24 | null, string |
| `player_id` | 24 | int |
| `registration_date` | 24 | int |
| `weight_after` | 24 | float |
| `weight_before` | 24 | float |

### Indexes

- 

---

## Inferred Relationships

- `attendance`.`session_id` → `sessions`  _(inferred)_
- `match_minutes`.`session_id` → `sessions`  _(inferred)_
- `meal_diary_entries`.`player_id` → `roster`  _(inferred)_
- `player_injuries`.`player_id` → `roster`  _(inferred)_
- `player_pdp`.`player_id` → `roster`  _(inferred)_
- `player_rpe`.`player_id` → `roster`  _(inferred)_
- `player_rpe`.`session_id` → `sessions`  _(inferred)_
- `player_rpe_archive_20250904_160822`.`player_id` → `roster`  _(inferred)_
- `player_rpe_archive_20250904_160822`.`session_id` → `sessions`  _(inferred)_
- `player_rpe_archive_20250910_150528`.`player_id` → `roster`  _(inferred)_
- `player_rpe_archive_20250910_150528`.`session_id` → `sessions`  _(inferred)_
- `player_wellness`.`player_id` → `roster`  _(inferred)_
- `player_wellness`.`session_id` → `sessions`  _(inferred)_
- `player_wellness_archive_20250910_151750`.`player_id` → `roster`  _(inferred)_
- `player_wellness_archive_20250910_151750`.`session_id` → `sessions`  _(inferred)_
- `roster`.`player_id` → `roster`  _(inferred)_
- `sessions`.`session_id` → `sessions`  _(inferred)_
- `weight_registration`.`player_id` → `roster`  _(inferred)_

> Diagram: see `img/er_diagram.svg` if generated.
