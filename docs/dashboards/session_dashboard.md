# Session RPE Dashboard

The Session RPE Dashboard provides a visual analysis of training load distribution across session types and weeks for each team. This dashboard helps staff understand how player effort is spread throughout different training sessions and periods.

---

## Features

### 1. Team Selection

- Users must select a team (`U18`, `U21`, etc.) to view session RPE data.
- If no team is selected, a prompt is shown to choose a team.

---

### 2. Visualizations

The dashboard displays several interactive charts:

#### **Bar Graph: Average Load per Session Type**

- Shows the average RPE load for each session type (e.g., training, match).
- Helps compare intensity across session categories.

#### **Stacked Bar: Load per Session Type per Week**

- Visualizes total RPE load for each session type, stacked by week.
- Reveals how load is distributed across session types over time.

#### **100% Stacked Bar: Relative Load Distribution**

- Displays the percentage contribution of each session type to the weekly total load.
- Useful for comparing the relative importance of session types week by week.

---

### 3. Data Table Calculations

- Calculates average load per session and per player.
- Normalizes session type loads as a percentage of weekly total.

---

## Error Handling

- All data retrieval and processing is wrapped in `try/except` blocks.
- User-friendly error messages are displayed if data cannot be loaded.

---

## Usage

1. Select a team from the dropdown.
2. View interactive charts to analyze session RPE data by type and week.

