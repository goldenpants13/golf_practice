"""
Short Game Testing — scorecard with real-time handicap calculation.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import delete_csv_row, load_testing, load_testing_lookup, save_testing_session

st.set_page_config(page_title="Short Game Testing", page_icon="🎯", layout="wide")

st.title("🎯 Short Game Testing")
st.caption("Test your short game, track your handicap across 8 shot types.")

# ---------------------------------------------------------------------------
# Load lookup tables
# ---------------------------------------------------------------------------
lookup = load_testing_lookup()
if not lookup:
    st.error("Testing lookup tables not found. Please run the Excel import first.")
    st.stop()

# The 8 shot types in display order
SHOT_TYPES = [
    "50 Yards F",
    "30 Yards F",
    "10 F Chip",
    "20 Yards R",
    "Flop",
    "15 F Pitch",
    "8 Yard Sand",
    "15 Yard Sand",
]

# Column names in the CSV
SHOT_CSV_COLS = [
    "50_yards_f",
    "30_yards_f",
    "10_f_chip",
    "20_yards_r",
    "flop",
    "15_f_pitch",
    "8_yard_sand",
    "15_yard_sand",
]


def score_to_handicap(shot_type: str, score: int):
    """Look up the handicap for a given shot type and raw score.
    Returns None if the score is outside the lookup table range."""
    table = lookup.get(shot_type, [])
    for entry in table:
        if entry["score"] == score:
            return entry["handicap"]
    # If score exceeds the table, extrapolate or return the best/worst
    if not table:
        return None
    scores = [e["score"] for e in table]
    if score < min(scores):
        return table[0]["handicap"]  # worst
    if score > max(scores):
        return table[-1]["handicap"]  # best
    return None


# ---------------------------------------------------------------------------
# Score entry form
# ---------------------------------------------------------------------------
st.subheader("New Test Session")

with st.form("testing_form", clear_on_submit=True):
    test_date = st.date_input("Test Date", value=date.today(), key="test_date")

    st.markdown("**Enter your score for each shot type** (number of successful shots)")

    scores = {}
    cols = st.columns(4)
    for i, (shot_name, csv_col) in enumerate(zip(SHOT_TYPES, SHOT_CSV_COLS)):
        with cols[i % 4]:
            table = lookup.get(shot_name, [])
            max_score = max(e["score"] for e in table) if table else 20
            scores[csv_col] = st.number_input(
                shot_name,
                min_value=0,
                max_value=max_score + 5,
                value=0,
                step=1,
                key=f"test_{csv_col}",
            )

    submitted = st.form_submit_button("Submit Test Results", type="primary")

if submitted:
    filled = {k: v for k, v in scores.items() if v > 0}
    if filled:
        row = {"date": test_date.strftime("%Y-%m-%d")}
        for csv_col in SHOT_CSV_COLS:
            row[csv_col] = scores[csv_col] if scores[csv_col] > 0 else None
        save_testing_session(row)
        st.success(f"Test results saved for {test_date.strftime('%b %d, %Y')}!")
        st.rerun()
    else:
        st.warning("Enter a score for at least one shot type.")

# ---------------------------------------------------------------------------
# Live handicap preview (outside the form so it can react)
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Handicap Calculator")
st.caption("Enter scores above (outside the form) or review your most recent test below.")

# Show the most recent test if available
test_df = load_testing()
if not test_df.empty:
    latest = test_df.iloc[-1]
    st.markdown(f"**Showing results for:** {pd.to_datetime(latest['date']).strftime('%b %d, %Y')}")

    hcap_data = []
    total_handicap = 0.0
    valid_count = 0

    for shot_name, csv_col in zip(SHOT_TYPES, SHOT_CSV_COLS):
        raw = latest.get(csv_col)
        if pd.notna(raw) and raw != "" and raw != "na":
            try:
                raw_int = int(float(raw))
            except (ValueError, TypeError):
                raw_int = None
            if raw_int and raw_int > 0:
                hcap = score_to_handicap(shot_name, raw_int)
                hcap_data.append({
                    "Shot Type": shot_name,
                    "Score": raw_int,
                    "Handicap": hcap if hcap is not None else "N/A",
                })
                if hcap is not None:
                    total_handicap += hcap
                    valid_count += 1
            else:
                hcap_data.append({"Shot Type": shot_name, "Score": "—", "Handicap": "—"})
        else:
            hcap_data.append({"Shot Type": shot_name, "Score": "—", "Handicap": "—"})

    # Summary metrics
    col1, col2 = st.columns(2)
    col1.metric("Shots Tested", valid_count)
    avg_hcap = total_handicap / valid_count if valid_count else 0
    col2.metric("Avg Handicap", f"{avg_hcap:+.1f}" if valid_count else "—")

    # Scorecard table
    hcap_df = pd.DataFrame(hcap_data)
    st.dataframe(hcap_df, use_container_width=True, hide_index=True)

    # Bar chart of handicaps
    chart_data = [r for r in hcap_data if isinstance(r["Handicap"], (int, float))]
    if chart_data:
        chart_df = pd.DataFrame(chart_data)
        colors = ["#2e7d32" if h <= 0 else "#f44336" if h > 10 else "#ff9800"
                  for h in chart_df["Handicap"]]
        fig = go.Figure(data=[go.Bar(
            x=chart_df["Shot Type"],
            y=chart_df["Handicap"],
            marker_color=colors,
            text=[f"{h:+.0f}" for h in chart_df["Handicap"]],
            textposition="outside",
        )])
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
        fig.update_layout(
            title="Handicap by Shot Type",
            yaxis_title="Handicap",
            height=350,
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No test results yet. Submit your first test above!")

# ---------------------------------------------------------------------------
# Historical trend
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Testing History")

if not test_df.empty and len(test_df) > 0:
    # Build full history with per-shot-type handicaps
    history = []
    for _, row in test_df.iterrows():
        entry = {"date": pd.to_datetime(row["date"])}
        hcaps = []
        for shot_name, csv_col in zip(SHOT_TYPES, SHOT_CSV_COLS):
            raw = row.get(csv_col)
            if pd.notna(raw) and raw != "" and raw != "na":
                try:
                    raw_int = int(float(raw))
                    hcap = score_to_handicap(shot_name, raw_int)
                    if hcap is not None:
                        entry[shot_name] = hcap
                        hcaps.append(hcap)
                except (ValueError, TypeError):
                    pass
        if hcaps:
            entry["avg_handicap"] = sum(hcaps) / len(hcaps)
            history.append(entry)

    if history:
        hist_df = pd.DataFrame(history).sort_values("date").reset_index(drop=True)
        total_sessions = len(hist_df)

        # --- Controls ---
        ctrl1, ctrl2, ctrl3 = st.columns(3)
        with ctrl1:
            if total_sessions > 1:
                sessions_to_show = st.slider(
                    "Sessions to display",
                    min_value=1,
                    max_value=total_sessions,
                    value=total_sessions,
                    step=1,
                    key="sessions_to_show",
                )
            else:
                sessions_to_show = 1
                st.caption("Sessions to display: 1")
        with ctrl2:
            if total_sessions >= 3:
                max_ma = min(total_sessions, 20)
                ma_window = st.slider(
                    "Moving average window",
                    min_value=2,
                    max_value=max_ma,
                    value=min(3, max_ma),
                    step=1,
                    key="ma_window",
                )
            else:
                ma_window = 2
                st.caption("Moving average: need 3+ sessions")
        with ctrl3:
            view_options = ["Average Handicap"] + SHOT_TYPES
            selected_view = st.selectbox(
                "Metric to chart",
                options=view_options,
                index=0,
                key="chart_metric",
            )

        # Slice to selected number of sessions
        plot_df = hist_df.tail(sessions_to_show).copy().reset_index(drop=True)

        # Determine which column to plot
        if selected_view == "Average Handicap":
            y_col = "avg_handicap"
            y_label = "Avg Handicap"
        else:
            y_col = selected_view
            y_label = f"{selected_view} Handicap"

        if y_col in plot_df.columns:
            # Compute moving average
            plot_df["moving_avg"] = plot_df[y_col].rolling(window=ma_window, min_periods=1).mean()

            fig_trend = go.Figure()

            # Raw results
            fig_trend.add_trace(go.Scatter(
                x=plot_df["date"],
                y=plot_df[y_col],
                mode="lines+markers",
                line=dict(color="#66bb6a", width=2),
                marker=dict(size=8),
                name="Per Session",
            ))

            # Moving average
            if len(plot_df) >= 2:
                fig_trend.add_trace(go.Scatter(
                    x=plot_df["date"],
                    y=plot_df["moving_avg"],
                    mode="lines",
                    line=dict(color="#ffffff", width=3, dash="solid"),
                    name=f"{ma_window}-Session Moving Avg",
                ))

            fig_trend.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.2)
            fig_trend.update_layout(
                title=f"{y_label} Over Time",
                yaxis_title=y_label,
                xaxis_title="Date",
                height=400,
                margin=dict(l=40, r=20, t=50, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info(f"No data for **{selected_view}** across the selected sessions.")

    else:
        st.caption("Complete more test sessions to see trends.")

    # Full history table
    st.markdown("#### All Test Results")
    display_df = test_df.copy()
    if "date" in display_df.columns:
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%b %d, %Y")
    # Drop internal columns
    drop_cols = [c for c in ["total", "avg_handicap", "adj", "handicap"] if c in display_df.columns]
    display_df = display_df.drop(columns=drop_cols, errors="ignore")
    col_map = {"date": "Date"}
    for shot_name, csv_col in zip(SHOT_TYPES, SHOT_CSV_COLS):
        col_map[csv_col] = shot_name
    display_df = display_df.rename(columns=col_map)
    sorted_display = display_df.sort_values("Date", ascending=False) if "Date" in display_df.columns else display_df
    original_indices = sorted_display.index.tolist()
    sorted_display = sorted_display.reset_index(drop=True)

    event = st.dataframe(
        sorted_display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="test_table",
    )

    if event.selection.rows:
        sel_pos = event.selection.rows[0]
        orig_idx = original_indices[sel_pos]
        row_date = sorted_display.loc[sel_pos, "Date"] if "Date" in sorted_display.columns else ""
        if st.button(
            f"🗑️  Delete selected test session ({row_date})",
            key="test_delete_btn",
            type="secondary",
        ):
            delete_csv_row("testing", orig_idx)
            st.success("Test session deleted.")
            st.rerun()
else:
    st.info("No test history available yet.")
