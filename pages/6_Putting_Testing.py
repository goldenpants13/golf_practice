"""
Putting Testing — structured putting tests with history tracking.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import delete_csv_row, load_putting_testing, save_putting_testing_session

st.set_page_config(page_title="Putting Testing", page_icon="🏌️", layout="wide")

st.title("🏌️ Putting Testing")
st.caption("Pick a test, log your results, and track improvement over time.")

# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------
LAG_DISTANCES = [30, 40, 50]
LAG_VERSIONS = ["Uphill", "Downhill"]
LAG_FIELDS = [
    (f"{d}ft {v}", f"lag_{d}_{v.lower()}")
    for d in LAG_DISTANCES
    for v in LAG_VERSIONS
]

TEST_NAMES = ["Lag Drill", "Stack Putting Session", "3-Footer Drill"]

# ---------------------------------------------------------------------------
# Test selector
# ---------------------------------------------------------------------------
selected_test = st.radio("Select Test", TEST_NAMES, horizontal=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Lag Drill
# ---------------------------------------------------------------------------
if selected_test == "Lag Drill":
    st.subheader("Lag Drill")
    st.caption("5 putts at each distance/slope combo. Enter how many finish in the box.")

    with st.form("lag_drill_form", clear_on_submit=True):
        lag_date = st.date_input("Date", value=date.today(), key="lag_date")

        scores = {}
        for d in LAG_DISTANCES:
            cols = st.columns(2)
            for i, v in enumerate(LAG_VERSIONS):
                field_key = f"lag_{d}_{v.lower()}"
                label = f"{d}ft {v}"
                with cols[i]:
                    scores[field_key] = st.number_input(
                        label,
                        min_value=0,
                        max_value=5,
                        value=0,
                        step=1,
                        key=field_key,
                        help="Putts in the box (out of 5)",
                    )

        submitted = st.form_submit_button("Submit Lag Drill", type="primary")

    if submitted:
        total = sum(scores.values())
        if total > 0:
            row = {"date": lag_date.strftime("%Y-%m-%d"), "test_type": "Lag Drill"}
            row.update(scores)
            row["score"] = total
            save_putting_testing_session(row)
            st.success(f"Lag Drill saved — **{total}/30** putts in the box!")
            st.rerun()
        else:
            st.warning("Enter at least one score before submitting.")

# ---------------------------------------------------------------------------
# Stack Putting Session (placeholder)
# ---------------------------------------------------------------------------
elif selected_test == "Stack Putting Session":
    st.subheader("Stack Putting Session")
    st.info(
        "**Stack Putting Session** is a placeholder. Tell me how this test works "
        "(distances, scoring, pass/fail) and I'll build the form."
    )

# ---------------------------------------------------------------------------
# 3-Footer Drill (placeholder)
# ---------------------------------------------------------------------------
elif selected_test == "3-Footer Drill":
    st.subheader("3-Footer Drill")
    st.info(
        "**3-Footer Drill** is a placeholder. Tell me how this test works "
        "(number of putts, make percentage target, etc.) and I'll build the form."
    )

# ---------------------------------------------------------------------------
# Session History (filtered by selected test)
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Session History")

hist_df = load_putting_testing()
if not hist_df.empty:
    if "test_type" in hist_df.columns:
        filtered = hist_df[hist_df["test_type"] == selected_test].copy()
    else:
        filtered = hist_df.copy()

    if not filtered.empty:
        # Summary metrics
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Total Sessions", len(filtered))
        if "score" in filtered.columns:
            filtered["score"] = pd.to_numeric(filtered["score"], errors="coerce")
            mcol2.metric("Best Score", f"{int(filtered['score'].max())}/30")
            mcol3.metric("Avg Score", f"{filtered['score'].mean():.1f}/30")

        # Trend chart
        if len(filtered) >= 2 and "score" in filtered.columns and "date" in filtered.columns:
            trend = filtered.sort_values("date")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend["date"], y=trend["score"],
                mode="lines+markers",
                line=dict(color="#66bb6a", width=2),
                marker=dict(size=8),
                name="Score",
                hovertemplate="Date: %{x|%b %d}<br>Score: %{y}/30<extra></extra>",
            ))
            if len(trend) >= 3:
                trend["score_ma"] = trend["score"].rolling(window=3, min_periods=1).mean()
                fig.add_trace(go.Scatter(
                    x=trend["date"], y=trend["score_ma"],
                    mode="lines",
                    line=dict(color="#ffffff", width=3),
                    name="3-Session Avg",
                ))
            fig.update_layout(
                yaxis_title="Score (out of 30)",
                xaxis_title="Date",
                yaxis=dict(range=[0, 31]),
                height=300,
                margin=dict(l=40, r=20, t=20, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Distance breakdown chart (Lag Drill specific)
        if selected_test == "Lag Drill" and len(filtered) >= 1:
            lag_cols_present = [c for _, c in LAG_FIELDS if c in filtered.columns]
            if lag_cols_present:
                avgs = {}
                for label, col in LAG_FIELDS:
                    if col in filtered.columns:
                        vals = pd.to_numeric(filtered[col], errors="coerce")
                        avgs[label] = vals.mean()
                if avgs:
                    fig_bar = go.Figure(data=[go.Bar(
                        x=list(avgs.keys()),
                        y=list(avgs.values()),
                        marker_color=["#2e7d32", "#66bb6a"] * 3,
                    )])
                    fig_bar.update_layout(
                        yaxis_title="Avg Putts in Box (out of 5)",
                        yaxis=dict(range=[0, 5.5]),
                        height=280,
                        margin=dict(l=40, r=20, t=20, b=40),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

        # History table with delete
        display = filtered.copy()
        if "date" in display.columns:
            display["date"] = pd.to_datetime(display["date"]).dt.strftime("%b %d, %Y")

        col_map = {"date": "Date", "test_type": "Test", "score": "Score"}
        for label, col in LAG_FIELDS:
            col_map[col] = label
        display = display.rename(columns={k: v for k, v in col_map.items() if k in display.columns})
        drop_cols = [c for c in display.columns if c == "Test"]
        display = display.drop(columns=drop_cols, errors="ignore")

        sorted_display = display.sort_values("Date", ascending=False) if "Date" in display.columns else display
        original_indices = sorted_display.index.tolist()
        sorted_display = sorted_display.reset_index(drop=True)

        event = st.dataframe(
            sorted_display,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="pt_history_table",
        )

        if event.selection.rows:
            sel_pos = event.selection.rows[0]
            orig_idx = original_indices[sel_pos]
            row_date = sorted_display.loc[sel_pos, "Date"] if "Date" in sorted_display.columns else ""
            if st.button(
                f"🗑️  Delete selected session ({row_date})",
                key="pt_delete_btn",
                type="secondary",
            ):
                delete_csv_row("putting_testing", orig_idx)
                st.success("Session deleted.")
                st.rerun()
    else:
        st.info(f"No **{selected_test}** sessions yet.")
else:
    st.info("No putting test sessions yet. Complete a test above to start tracking!")
