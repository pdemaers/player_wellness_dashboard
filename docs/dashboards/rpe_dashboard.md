# RPE Dashboard

The RPE (Rate of Perceived Exertion) Dashboard provides staff with a detailed overview of player training loads and acute/chronic ratios, helping to monitor workload, identify risk, and support player management decisions.

---

## Features

### 1. Team Selection

- Users must select a team (`U18`, `U21`, etc.) to view RPE data.
- If no team is selected, a prompt is shown to choose a team.

---

### 2. Tabs Overview

The dashboard is organized into three tabs:

#### **Tab 1: Weekly Load Table**

- Displays weekly RPE load for each player in a pivot table format.
- Rows: Player names.
- Columns: ISO weeks.
- Values: Summed RPE load, rounded to two decimals.
- If no data is available, an info message is shown.

#### **Tab 2: AC Ratio Table**

- Shows the Acute/Chronic RPE ratio for each player and week.
- Ratios are color-coded for risk:
  - 🔴 High risk (outside 0.75–1.35)
  - 🟠 Moderate risk (borderline)
  - 🟢 Low risk (within safe range)
- If no data is available, an info message is shown.

#### **Tab 3: All RPE Entries**

- Displays all daily RPE entries for the selected team.
- Users can filter displayed data by ISO week using a multiselect.
- Default selection is the last week (or last four weeks if available).
- If no data is available, an info message is shown.

---

## Error Handling

- All data retrieval and processing is wrapped in `try/except` blocks.
- User-friendly error messages are displayed if data cannot be loaded.

---

## Usage

1. Select a team from the dropdown.
2. Navigate between tabs to view weekly loads, AC ratios, or all RPE entries.
3. Use the week selector in the "All RPE Entries" tab to filter data by week.

