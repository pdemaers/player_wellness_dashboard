"""
Session Dashboard Charts
Pure functions that return Plotly figures or tabular outlier results.
"""

from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ---------- Boxplot & outliers ----------

def rpe_boxplot_per_session(df: pd.DataFrame, title: str) -> go.Figure:
    """
    Expects: date (datetime64), session_type, rpe
    One box per session, x label formatted as "YYYY-MM-DD (TYPE)".
    """
    if df.empty:
        return go.Figure()

    xlbl = df["date"].dt.strftime("%Y-%m-%d") + " (" + df["session_type"].astype(str) + ")"
    fig = px.box(
        df.assign(x_label=xlbl),
        x="x_label",
        y="rpe",
        color="session_type",
        points="all",
        labels={"x_label": "Session", "rpe": "RPE"},
        title=title
    )
    fig.update_traces(boxpoints="outliers")
    fig.update_layout(xaxis=dict(type="category"))
    return fig



def rpe_outliers_table(df: pd.DataFrame, iqr_k: float = 1.5) -> pd.DataFrame:
    """
    IQR-based outliers per session.
    Returns: date, session_type, session_id, player_id, rpe, lower_fence, upper_fence
    """
    if df.empty:
        return pd.DataFrame()

    def _one(g: pd.DataFrame) -> pd.DataFrame:
        q1, q3 = g["rpe"].quantile(0.25), g["rpe"].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - iqr_k * iqr, q3 + iqr_k * iqr
        mask = (g["rpe"] < lower) | (g["rpe"] > upper)
        out = g.loc[mask, ["date", "session_type", "session_id", "player_id", "rpe"]].copy()
        out["lower_fence"], out["upper_fence"] = lower, upper
        return out

    return df.groupby("session_id", group_keys=False).apply(_one).reset_index(drop=True)


# ---------- Your existing KPIs ----------

def bar_avg_load_per_type(agg_df: pd.DataFrame, title: str) -> go.Figure:
    """
    Expects: session_type, total_load, session_count
    """
    if agg_df.empty:
        return go.Figure()

    df = agg_df.copy()
    df["avg_load_per_session"] = df["total_load"] / df["session_count"]
    type_df = df.groupby("session_type", as_index=False)["avg_load_per_session"].mean()

    return px.bar(
        type_df, x="session_type", y="avg_load_per_session",
        title=title, color="session_type",
        labels={"avg_load_per_session": "Avg Load / Session"}
    )



def stacked_load_per_week(agg_df: pd.DataFrame, title: str) -> go.Figure:
    """
    Expects: week, session_type, total_load
    """
    if agg_df.empty:
        return go.Figure()

    stacked_df = agg_df.pivot(index="week", columns="session_type", values="total_load").fillna(0).reset_index()
    fig = px.bar(
        stacked_df, x="week", y=stacked_df.columns[1:],
        title=title, labels={"value": "Load", "week": "Week"},
        barmode="stack"
    )
    return fig



def stacked_pct_load_per_week(agg_df: pd.DataFrame, title: str) -> go.Figure:
    """
    100% stacked version of weekly load by type.
    """
    if agg_df.empty:
        return go.Figure()

    stacked_df = agg_df.pivot(index="week", columns="session_type", values="total_load").fillna(0)
    stacked_df["total"] = stacked_df.sum(axis=1)
    pct = stacked_df.div(stacked_df["total"], axis=0).drop(columns="total") * 100
    pct = pct.reset_index().round(1)

    melted = pct.melt(id_vars="week", var_name="Session Type", value_name="Percentage")

    fig = px.bar(
        melted,
        x="week",
        y="Percentage",
        color="Session Type",
        text="Percentage",
        title=title,
        labels={"week": "Training Week"}
    )
    fig.update_traces(texttemplate="%{text}%", textposition="inside")
    fig.update_layout(barmode="stack", yaxis_title="Percentage (%)")
    return fig