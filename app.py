"""
Golf Practice Tracker — Dashboard
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure the project root is on the path so utils can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.data_manager import (
    all_practice_dates,
    current_streak,
    load_csv,
    load_goals,
    longest_streak,
    practice_session_counts,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Golf Practice Tracker",
    page_icon="⛳",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("⛳ Golf Practice Tracker")
st.caption("Track your practice, measure your progress, crush your goals.")

# ---------------------------------------------------------------------------
# Key metrics row
# ---------------------------------------------------------------------------
dates = all_practice_dates()
counts = practice_session_counts()
total_sessions = sum(counts.values())

# Sessions this week
today = date.today()
week_start = today - timedelta(days=today.weekday())  # Monday
sessions_this_week = sum(1 for d in dates if d >= week_start)

# Sessions this month
month_start = today.replace(day=1)
sessions_this_month = sum(1 for d in dates if d >= month_start)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sessions", total_sessions)
col2.metric("Current Streak", f"{current_streak(dates)} days")
col3.metric("Longest Streak", f"{longest_streak(dates)} days")
col4.metric("This Month", sessions_this_month)

# ---------------------------------------------------------------------------
# Practice breakdown
# ---------------------------------------------------------------------------
st.markdown("---")
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Practice Frequency")

    if dates:
        # Build a calendar heatmap for the current year
        year = today.year
        start = date(year, 1, 1)
        end = today
        all_days = pd.date_range(start, end, freq="D")
        date_counts = pd.Series(0, index=all_days)

        # Count sessions per day across all categories
        for name in ("ball_striking", "putting", "testing", "three_hole_loop", "wedge_ladder"):
            df = load_csv(name)
            if not df.empty and "date" in df.columns:
                for d in pd.to_datetime(df["date"]).dt.normalize():
                    if d in date_counts.index:
                        date_counts[d] += 1

        # Create a heatmap with weeks as columns and days of week as rows
        df_cal = pd.DataFrame({
            "date": all_days,
            "count": date_counts.values,
        })
        df_cal["weekday"] = df_cal["date"].dt.weekday  # 0=Mon, 6=Sun
        df_cal["week"] = df_cal["date"].dt.isocalendar().week.astype(int)
        # Adjust week for year boundary
        df_cal["week_offset"] = ((df_cal["date"] - pd.Timestamp(start)).dt.days) // 7

        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        fig = go.Figure(data=go.Heatmap(
            x=df_cal["week_offset"],
            y=df_cal["weekday"],
            z=df_cal["count"],
            colorscale=[
                [0, "#1a1f2e"],
                [0.01, "#1a1f2e"],
                [0.5, "#2e7d32"],
                [1.0, "#66bb6a"],
            ],
            showscale=False,
            hovertemplate="Date: %{customdata}<br>Sessions: %{z}<extra></extra>",
            customdata=df_cal["date"].dt.strftime("%b %d"),
            ygap=3,
            xgap=3,
        ))
        fig.update_yaxes(
            tickvals=list(range(7)),
            ticktext=day_labels,
            autorange="reversed",
        )
        fig.update_xaxes(showticklabels=False)
        fig.update_layout(
            height=200,
            margin=dict(l=40, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No practice sessions yet. Log your first session to see the heatmap!")

with col_right:
    st.subheader("Sessions by Category")
    if total_sessions > 0:
        labels = {
            "ball_striking": "Ball Striking",
            "putting": "Putting",
            "testing": "Short Game Testing",
            "three_hole_loop": "3-Hole Loop",
            "wedge_ladder": "Wedge Ladder",
        }
        fig_pie = go.Figure(data=[go.Pie(
            labels=[labels.get(k, k) for k in counts.keys()],
            values=list(counts.values()),
            hole=0.45,
            marker=dict(colors=["#2e7d32", "#66bb6a", "#1b5e20", "#4caf50", "#81c784"]),
            textinfo="label+value",
        )])
        fig_pie.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No sessions logged yet.")

# ---------------------------------------------------------------------------
# Recent activity
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Recent Activity")

recent_rows = []
for name, label in [("ball_striking", "Ball Striking"), ("putting", "Putting"), ("testing", "Short Game Testing"), ("three_hole_loop", "3-Hole Loop"), ("wedge_ladder", "Wedge Ladder")]:
    df = load_csv(name)
    if not df.empty:
        df = df.copy()
        df["category"] = label
        # Summarize non-date, non-category columns
        data_cols = [c for c in df.columns if c not in ("date", "category")]

        def _summarize(row):
            parts = []
            for col, val in row.items():
                if pd.isna(val) or val == 0:
                    continue
                try:
                    parts.append(f"{col.replace('_', ' ').title()}: {int(float(val))}")
                except (ValueError, TypeError):
                    parts.append(f"{col.replace('_', ' ').title()}: {val}")
            return ", ".join(parts)

        df["summary"] = df[data_cols].apply(_summarize, axis=1)
        recent_rows.append(df[["date", "category", "summary"]])

if recent_rows:
    recent_df = pd.concat(recent_rows, ignore_index=True)
    recent_df["date"] = pd.to_datetime(recent_df["date"])
    recent_df = recent_df.sort_values("date", ascending=False).head(10)
    recent_df["date"] = recent_df["date"].dt.strftime("%b %d, %Y")
    recent_df.columns = ["Date", "Category", "Details"]
    st.dataframe(recent_df, use_container_width=True, hide_index=True)
else:
    st.info("No activity recorded yet. Head to the Practice Log to get started!")

# ---------------------------------------------------------------------------
# Goals overview
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Goals")

goals = load_goals()
if goals:
    tab_big, tab_comp, tab_sub = st.tabs(["Big Goals", "Component Goals", "Sub-Goals"])

    with tab_big:
        for i, g in enumerate(goals.get("big_goals", []), 1):
            st.markdown(f"**{i}.** {g}")

    with tab_comp:
        for i, g in enumerate(goals.get("component_goals", []), 1):
            st.markdown(f"**{i}.** {g}")

    with tab_sub:
        for group, items in goals.get("sub_goals", {}).items():
            with st.expander(group, expanded=False):
                for item in items:
                    st.markdown(f"- {item}")
else:
    st.info("No goals data found. Run the Excel import first.")

