"""
Wedge Ladder — interactive distance control drill with grading.
"""

import random
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import delete_csv_row, load_wedge_ladder, save_wedge_ladder_session

st.set_page_config(page_title="Wedge Ladder", page_icon="🪜", layout="wide")

st.title("🪜 Wedge Ladder")
st.caption("Test your wedge distance control. Hit each target, get graded.")

# ---------------------------------------------------------------------------
# Grading scale reference
# ---------------------------------------------------------------------------
GRADES = [
    (1, "50% of shots within 5 yards"),
    (2, "70% of shots within 5 yards"),
    (3, "70% of shots within 4 yards"),
    (4, "70% of shots within 3 yards"),
    (5, "70% of shots within 2 yards"),
]


def calculate_grade(targets, actuals):
    """Return the highest grade achieved and per-threshold stats."""
    n = len(targets)
    if n == 0:
        return 0, {}

    diffs = [abs(t - a) for t, a in zip(targets, actuals)]
    stats = {}
    for threshold in (5, 4, 3, 2):
        within = sum(1 for d in diffs if d <= threshold)
        pct = within / n * 100
        stats[threshold] = {"within": within, "total": n, "pct": round(pct, 1)}

    grade = 0
    if stats[5]["pct"] >= 50:
        grade = 1
    if stats[5]["pct"] >= 70:
        grade = 2
    if stats[4]["pct"] >= 70:
        grade = 3
    if stats[3]["pct"] >= 70:
        grade = 4
    if stats[2]["pct"] >= 70:
        grade = 5

    return grade, stats


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "wl_active" not in st.session_state:
    st.session_state.wl_active = False
if "wl_distances" not in st.session_state:
    st.session_state.wl_distances = []
if "wl_mode" not in st.session_state:
    st.session_state.wl_mode = "In Order"
if "wl_start" not in st.session_state:
    st.session_state.wl_start = 40
if "wl_end" not in st.session_state:
    st.session_state.wl_end = 120

# ---------------------------------------------------------------------------
# Setup section
# ---------------------------------------------------------------------------
if not st.session_state.wl_active:
    st.subheader("Setup")

    mode = st.radio("Mode", ["In Order", "Randomizer"], horizontal=True, key="wl_mode_input")

    col1, col2 = st.columns(2)
    with col1:
        start_dist = st.number_input(
            "Start Distance (yards)", min_value=10, max_value=200, value=40, step=5, key="wl_start_input"
        )
    with col2:
        end_dist = st.number_input(
            "End Distance (yards)", min_value=10, max_value=200, value=120, step=5, key="wl_end_input"
        )

    if start_dist >= end_dist:
        st.warning("Start distance must be less than end distance.")
    else:
        distances_ordered = list(range(int(start_dist), int(end_dist) + 1, 5))
        st.info(f"**{len(distances_ordered)} shots** from {int(start_dist)} to {int(end_dist)} yards "
                f"({'random order' if mode == 'Randomizer' else 'ascending order'})")

        # Grading reference
        with st.expander("Grading Scale"):
            for g, desc in GRADES:
                st.markdown(f"**Grade {g}:** {desc}")

        if st.button("Start Drill", type="primary"):
            if mode == "Randomizer":
                shuffled = distances_ordered.copy()
                random.shuffle(shuffled)
                st.session_state.wl_distances = shuffled
            else:
                st.session_state.wl_distances = distances_ordered
            st.session_state.wl_mode = mode
            st.session_state.wl_start = int(start_dist)
            st.session_state.wl_end = int(end_dist)
            st.session_state.wl_active = True
            st.rerun()

# ---------------------------------------------------------------------------
# Active drill
# ---------------------------------------------------------------------------
else:
    distances = st.session_state.wl_distances
    mode = st.session_state.wl_mode

    st.subheader(f"Wedge Ladder — {mode}")
    st.caption(f"{st.session_state.wl_start}–{st.session_state.wl_end} yards  |  "
               f"{len(distances)} shots  |  "
               f"{'🔀 Random' if mode == 'Randomizer' else '📶 Ascending'}")

    with st.form("wedge_ladder_form"):
        actuals = []
        for i, target in enumerate(distances):
            val = st.number_input(
                f"Shot {i + 1}  —  Target: **{target} yards**",
                min_value=0,
                max_value=300,
                value=target,
                step=1,
                key=f"wl_shot_{i}",
            )
            actuals.append(val)

        col_submit, col_cancel = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("Submit Results", type="primary")
        with col_cancel:
            cancelled = st.form_submit_button("Cancel Drill")

    if cancelled:
        st.session_state.wl_active = False
        st.rerun()

    if submitted:
        if all(a == 0 for a in actuals):
            st.warning("Enter at least one actual distance before submitting.")
        else:
            grade, stats = calculate_grade(distances, actuals)

            # --- Results display ---
            st.markdown("---")
            st.subheader("Results")

            # Grade banner
            grade_colors = {0: "🔴", 1: "🟠", 2: "🟡", 3: "🟢", 4: "🔵", 5: "⭐"}
            st.markdown(f"### {grade_colors.get(grade, '')}  Grade: **{grade}** / 5")

            # Threshold breakdown
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Within 5 yds", f"{stats[5]['pct']}%", f"{stats[5]['within']}/{stats[5]['total']}")
            mcol2.metric("Within 4 yds", f"{stats[4]['pct']}%", f"{stats[4]['within']}/{stats[4]['total']}")
            mcol3.metric("Within 3 yds", f"{stats[3]['pct']}%", f"{stats[3]['within']}/{stats[3]['total']}")
            mcol4.metric("Within 2 yds", f"{stats[2]['pct']}%", f"{stats[2]['within']}/{stats[2]['total']}")

            # Shot-by-shot results table
            results_data = []
            for i, (t, a) in enumerate(zip(distances, actuals)):
                diff = a - t
                abs_diff = abs(diff)
                direction = "short" if diff < 0 else ("long" if diff > 0 else "perfect")
                results_data.append({
                    "Shot": i + 1,
                    "Target": f"{t} yds",
                    "Actual": f"{a} yds",
                    "Diff": f"{'+' if diff > 0 else ''}{diff} yds",
                    "Result": "✅" if abs_diff <= 5 else "❌",
                })
            st.dataframe(
                pd.DataFrame(results_data),
                use_container_width=True,
                hide_index=True,
            )

            # Scatter chart: target vs actual
            fig = go.Figure()
            min_d = min(distances) - 10
            max_d = max(distances) + 10
            fig.add_trace(go.Scatter(
                x=[min_d, max_d], y=[min_d, max_d],
                mode="lines", line=dict(color="white", width=1, dash="dash"),
                name="Perfect", showlegend=False,
            ))
            colors = ["#66bb6a" if abs(a - t) <= 5 else "#f44336" for t, a in zip(distances, actuals)]
            fig.add_trace(go.Scatter(
                x=distances, y=actuals,
                mode="markers",
                marker=dict(size=10, color=colors, line=dict(color="white", width=1)),
                name="Shots",
                hovertemplate="Target: %{x} yds<br>Actual: %{y} yds<extra></extra>",
            ))
            fig.update_layout(
                xaxis_title="Target (yards)",
                yaxis_title="Actual (yards)",
                height=350,
                margin=dict(l=40, r=20, t=20, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Save to Google Sheets
            row = {
                "date": date.today().strftime("%Y-%m-%d"),
                "mode": mode.lower().replace(" ", "_"),
                "start_distance": st.session_state.wl_start,
                "end_distance": st.session_state.wl_end,
                "total_shots": len(distances),
                "grade": grade,
                "pct_within_5": stats[5]["pct"],
                "pct_within_4": stats[4]["pct"],
                "pct_within_3": stats[3]["pct"],
                "pct_within_2": stats[2]["pct"],
            }
            save_wedge_ladder_session(row)
            st.success("Session saved!")

            if st.button("Start New Drill", type="primary"):
                st.session_state.wl_active = False
                st.rerun()

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Session History")

hist_df = load_wedge_ladder()
if not hist_df.empty:
    # Summary metrics
    mcol1, mcol2, mcol3 = st.columns(3)
    mcol1.metric("Total Sessions", len(hist_df))
    if "grade" in hist_df.columns:
        mcol2.metric("Best Grade", int(hist_df["grade"].max()))
        mcol3.metric("Avg Grade", round(hist_df["grade"].mean(), 1))

    # Grade trend chart
    if len(hist_df) >= 2 and "grade" in hist_df.columns and "date" in hist_df.columns:
        trend_df = hist_df.sort_values("date")
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend_df["date"], y=trend_df["grade"],
            mode="lines+markers",
            line=dict(color="#66bb6a", width=2),
            marker=dict(size=8),
            name="Grade",
            hovertemplate="Date: %{x|%b %d}<br>Grade: %{y}<extra></extra>",
        ))
        if len(trend_df) >= 3:
            trend_df["grade_ma"] = trend_df["grade"].rolling(window=3, min_periods=1).mean()
            fig_trend.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["grade_ma"],
                mode="lines",
                line=dict(color="#ffffff", width=3),
                name="3-Session Avg",
            ))
        fig_trend.update_layout(
            yaxis_title="Grade",
            xaxis_title="Date",
            yaxis=dict(range=[0, 5.5], dtick=1),
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # History table with delete
    display = hist_df.copy()
    if "date" in display.columns:
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%b %d, %Y")
    col_map = {
        "date": "Date",
        "mode": "Mode",
        "start_distance": "Start",
        "end_distance": "End",
        "total_shots": "Shots",
        "grade": "Grade",
        "pct_within_5": "≤5 yds %",
        "pct_within_4": "≤4 yds %",
        "pct_within_3": "≤3 yds %",
        "pct_within_2": "≤2 yds %",
    }
    display = display.rename(columns=col_map)

    sorted_display = display.sort_values("Date", ascending=False) if "Date" in display.columns else display
    original_indices = sorted_display.index.tolist()
    sorted_display = sorted_display.reset_index(drop=True)

    event = st.dataframe(
        sorted_display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="wl_history_table",
    )

    if event.selection.rows:
        sel_pos = event.selection.rows[0]
        orig_idx = original_indices[sel_pos]
        row_date = sorted_display.loc[sel_pos, "Date"] if "Date" in sorted_display.columns else ""
        if st.button(
            f"🗑️  Delete selected session ({row_date})",
            key="wl_delete_btn",
            type="secondary",
        ):
            delete_csv_row("wedge_ladder", orig_idx)
            st.success("Session deleted.")
            st.rerun()
else:
    st.info("No wedge ladder sessions yet. Start a drill above!")
