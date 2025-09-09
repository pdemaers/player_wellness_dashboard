# Wellness Dashboard

The Wellness Dashboard provides coaches, physios, and staff with a comprehensive overview of player wellness data, including daily check-ins, weekly averages, and historical entries. This dashboard helps monitor player well-being and identify trends or issues over time.

---

## Features

### 1. Team Selection

- Users must select a team (`U18`, `U21`, etc.) to view wellness data.
- If no team is selected, a prompt is shown to choose a team.

---

### 2. Tabs Overview

The dashboard is organized into three tabs:

#### **Tab 1: Today's Check**

- Displays all wellness entries submitted today for the selected team.
- Shows each player's:
  - Name
  - Wellness score (with colored icon)
  - Sleep hours (with colored icon)
  - Submission time
- Icons indicate status:
  - **Wellness:** 🟢 (good), 🟠 (moderate), 🔴 (poor), ❓ (unknown)
  - **Sleep:** 🟢 (good), 🟠 (moderate), 🔴 (poor), ❓ (unknown)
- If no entries are available, an info message is shown.

#### **Tab 2: Weekly Averages**

- Displays a matrix of weekly wellness averages for the selected team.
- Data is shown in a table, rounded to two decimals.
- If no data is available, an info message is shown.

#### **Tab 3: All Entries**

- Shows all historical wellness entries for the selected team in a pivot table format.
- Users can filter the displayed data by ISO week (e.g., `2025-W32`).
- Default selection is the last four weeks (if available).
- If no data is available, an info message is shown.

---

## Error Handling

- All data retrieval and processing is wrapped in `try/except` blocks.
- User-friendly error messages are displayed if data cannot be loaded.

---

## Usage

1. Select a team from the dropdown.
2. Navigate between tabs to view today's check-ins, weekly averages, or all historical entries.
3. Use the week selector in the "All Entries" tab to filter data by week.

