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
# Test definitions (placeholder structure — flesh out as needed)
# ---------------------------------------------------------------------------
TESTS = {
    "Lag Drill": {
        "description": "Coming soon — define your lag putting test format.",
        "fields": [],
    },
    "Stack Putting Session": {
        "description": "Coming soon — define your stack putting test format.",
        "fields": [],
    },
    "3-Footer Drill": {
        "description": "Coming soon — define your 3-foot putting test format.",
        "fields": [],
    },
}

# ---------------------------------------------------------------------------
# Test selector
# ---------------------------------------------------------------------------
selected_test = st.radio("Select Test", list(TESTS.keys()), horizontal=True)

st.markdown("---")

test_info = TESTS[selected_test]

st.subheader(selected_test)
st.caption(test_info["description"])

st.info(
    f"**{selected_test}** is a placeholder. Tell me how you want this test to work "
    f"(scoring, number of putts, distances, pass/fail criteria, etc.) "
    f"and I'll build out the form and grading."
)

# ---------------------------------------------------------------------------
# Session History
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Session History")

hist_df = load_putting_testing()
if not hist_df.empty:
    # Filter to selected test type
    if "test_type" in hist_df.columns:
        filtered = hist_df[hist_df["test_type"] == selected_test].copy()
    else:
        filtered = hist_df.copy()

    if not filtered.empty:
        mcol1, mcol2 = st.columns(2)
        mcol1.metric("Total Sessions", len(filtered))
        if "score" in filtered.columns:
            mcol2.metric("Best Score", int(filtered["score"].max()))

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
            ))
            fig.update_layout(
                yaxis_title="Score",
                xaxis_title="Date",
                height=300,
                margin=dict(l=40, r=20, t=20, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Table with delete
        display = filtered.copy()
        if "date" in display.columns:
            display["date"] = pd.to_datetime(display["date"]).dt.strftime("%b %d, %Y")
        col_map = {"date": "Date", "test_type": "Test", "score": "Score", "notes": "Notes"}
        display = display.rename(columns={k: v for k, v in col_map.items() if k in display.columns})

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
