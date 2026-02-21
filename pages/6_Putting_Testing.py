"""
Putting Testing — structured putting tests with history tracking.
"""

import random
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import delete_csv_row, load_putting_testing, save_putting_testing_session

st.set_page_config(page_title="Putting Testing", page_icon="🏌️", layout="wide")

st.title("🏌️ Putting Testing")
st.caption("Pick a test, log your results, and track improvement over time.")

# ---------------------------------------------------------------------------
# Lag Drill constants
# ---------------------------------------------------------------------------
LAG_DISTANCES = [30, 40, 50]
LAG_VERSIONS = ["Uphill", "Downhill"]
LAG_FIELDS = [
    (f"{d}ft {v}", f"lag_{d}_{v.lower()}")
    for d in LAG_DISTANCES
    for v in LAG_VERSIONS
]

# ---------------------------------------------------------------------------
# Swedish Drill constants
# ---------------------------------------------------------------------------
SWEDISH_PUTT_DISTANCES = [22, 12, 18, 10, 14, 8] * 3  # 18 putts, each distance 3x

SWEDISH_BENCHMARKS = [
    (-5.5, "Tour Player"),
    (-2.9, "European Tour"),
    (-1.5, "Challenge Tour"),
    (+0.2, "+2 HCP"),
    (+2.0, "Scratch"),
    (+6.3, "5 HCP"),
    (+10.7, "10 HCP"),
]

# Interpolation data: test score → putting handicap
_SW_SCORES = [0.2, 2.0, 6.3, 10.7]
_SW_HCAPS = [-2, 0, 5, 10]


def swedish_putt_score(dist_from_hole: float) -> int:
    """Score a single putt based on distance from hole (meters)."""
    if dist_from_hole == 0:
        return -2  # Eagle (holed)
    if dist_from_hole <= 0.5:
        return -1  # Birdie
    if dist_from_hole <= 1.0:
        return 0   # Par
    if dist_from_hole <= 2.0:
        return 1   # Bogey
    if dist_from_hole <= 3.0:
        return 2   # Double Bogey
    return 3        # Triple Bogey


def swedish_score_label(score: int) -> str:
    labels = {-2: "Eagle", -1: "Birdie", 0: "Par", 1: "Bogey", 2: "Double", 3: "Triple"}
    return labels.get(score, str(score))


def swedish_putting_handicap(total_score: float) -> float:
    """Interpolate a putting handicap from the total test score."""
    return float(np.interp(total_score, _SW_SCORES, _SW_HCAPS))


def swedish_level_label(total_score: float) -> str:
    """Return the closest benchmark level label."""
    closest = min(SWEDISH_BENCHMARKS, key=lambda b: abs(b[0] - total_score))
    return closest[1]


# ---------------------------------------------------------------------------
# Test selector
# ---------------------------------------------------------------------------
LUKE_DONALD_DISTANCES = [4, 5, 6, 7, 8]
LUKE_DONALD_HOLES = [1, 2, 3, 4]
LUKE_DONALD_GOAL = 15  # out of 20

TEST_NAMES = ["Lag Drill", "Swedish Drill", "Luke Donald Drill", "Stack Putting Session"]

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
# Swedish Drill
# ---------------------------------------------------------------------------
elif selected_test == "Swedish Drill":
    st.subheader("Swedish Drill")
    st.caption("18 lag putts (8–22m). Enter distance from hole. Score and handicap calculated automatically.")

    # Scoring reference
    with st.expander("Scoring & Benchmarks"):
        ref1, ref2 = st.columns(2)
        with ref1:
            st.markdown("**Per-Putt Scoring**")
            st.markdown("""
| Result | Score |
|---|---|
| Holed | -2 (Eagle) |
| 0–0.5m | -1 (Birdie) |
| 0.5–1m | 0 (Par) |
| 1–2m | +1 (Bogey) |
| 2–3m | +2 (Double) |
| 3m+ | +3 (Triple) |
""")
        with ref2:
            st.markdown("**Benchmark Totals**")
            st.markdown("""
| Level | Avg Score |
|---|---|
| Tour Player | -5.5 |
| European Tour | -2.9 |
| Challenge Tour | -1.5 |
| +2 HCP | +0.2 |
| Scratch | +2.0 |
| 5 HCP | +6.3 |
| 10 HCP | +10.7 |
""")

    # Session state for randomized order
    if "sw_active" not in st.session_state:
        st.session_state.sw_active = False
    if "sw_order" not in st.session_state:
        st.session_state.sw_order = []

    if not st.session_state.sw_active:
        st.info(f"**18 putts** at distances from 8m to 22m, presented in random order.")
        if st.button("Start Swedish Drill", type="primary"):
            order = SWEDISH_PUTT_DISTANCES.copy()
            random.shuffle(order)
            st.session_state.sw_order = order
            st.session_state.sw_active = True
            st.rerun()
    else:
        order = st.session_state.sw_order

        with st.form("swedish_drill_form"):
            sw_date = st.date_input("Date", value=date.today(), key="sw_date")

            distances_entered = []
            for i, target_m in enumerate(order):
                val = st.number_input(
                    f"Putt {i + 1}  —  Distance: **{target_m}m**  →  Result (m from hole)",
                    min_value=0.0,
                    max_value=20.0,
                    value=1.0,
                    step=0.1,
                    format="%.1f",
                    key=f"sw_putt_{i}",
                )
                distances_entered.append(val)

            col_sub, col_cancel = st.columns(2)
            with col_sub:
                submitted = st.form_submit_button("Submit Results", type="primary")
            with col_cancel:
                cancelled = st.form_submit_button("Cancel Drill")

        if cancelled:
            st.session_state.sw_active = False
            st.rerun()

        if submitted:
            # Calculate scores
            putt_scores = [swedish_putt_score(d) for d in distances_entered]
            total_score = sum(putt_scores)
            putting_hcp = swedish_putting_handicap(total_score)
            level = swedish_level_label(total_score)

            st.markdown("---")
            st.subheader("Results")

            # Summary metrics
            m1, m2, m3 = st.columns(3)
            sign = "+" if total_score > 0 else ""
            m1.metric("Total Score", f"{sign}{total_score}")
            m2.metric("Putting Handicap", f"{putting_hcp:+.1f}")
            m3.metric("Level", level)

            # Shot-by-shot results
            results = []
            for i, (target, dist, sc) in enumerate(zip(order, distances_entered, putt_scores)):
                sign_s = "+" if sc > 0 else ""
                results.append({
                    "Putt": i + 1,
                    "Distance": f"{target}m",
                    "From Hole": f"{dist:.1f}m",
                    "Score": f"{sign_s}{sc}",
                    "Result": swedish_score_label(sc),
                })
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

            # Save
            row = {
                "date": sw_date.strftime("%Y-%m-%d"),
                "test_type": "Swedish Drill",
                "score": total_score,
                "putting_hcp": round(putting_hcp, 1),
            }
            save_putting_testing_session(row)
            st.success("Swedish Drill saved!")

            if st.button("Start New Drill", type="primary"):
                st.session_state.sw_active = False
                st.rerun()

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
# Luke Donald Drill
# ---------------------------------------------------------------------------
elif selected_test == "Luke Donald Drill":
    st.subheader("Luke Donald Drill")
    st.caption(f"5 putts from 5 distances (4–8ft) at 4 hole locations. Goal: {LUKE_DONALD_GOAL}/20 makes.")

    with st.form("luke_donald_form", clear_on_submit=True):
        ld_date = st.date_input("Date", value=date.today(), key="ld_date")

        makes = {}
        cols = st.columns(4)
        for hi, hole in enumerate(LUKE_DONALD_HOLES):
            with cols[hi]:
                st.markdown(f"**Hole {hole}**")
                for dist in LUKE_DONALD_DISTANCES:
                    field_key = f"ld_h{hole}_{dist}ft"
                    makes[field_key] = st.checkbox(f"{dist} ft", key=field_key)

        submitted = st.form_submit_button("Submit Luke Donald Drill", type="primary")

    if submitted:
        total_makes = sum(1 for v in makes.values() if v)
        row = {"date": ld_date.strftime("%Y-%m-%d"), "test_type": "Luke Donald Drill"}
        for key, made in makes.items():
            row[key] = 1 if made else 0
        row["score"] = total_makes
        save_putting_testing_session(row)

        if total_makes >= LUKE_DONALD_GOAL:
            st.success(f"**{total_makes}/20** — Goal reached! 🎯")
        else:
            st.warning(f"**{total_makes}/20** — Goal is {LUKE_DONALD_GOAL}/20. Keep grinding!")
        st.rerun()

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
        filtered["score"] = pd.to_numeric(filtered["score"], errors="coerce")

        # Summary metrics — adapt labels per test type
        if selected_test == "Lag Drill":
            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("Total Sessions", len(filtered))
            mcol2.metric("Best Score", f"{int(filtered['score'].max())}/30")
            mcol3.metric("Avg Score", f"{filtered['score'].mean():.1f}/30")
        elif selected_test == "Swedish Drill":
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Total Sessions", len(filtered))
            best = filtered["score"].min()
            sign = "+" if best > 0 else ""
            mcol2.metric("Best Score", f"{sign}{int(best)}")
            avg = filtered["score"].mean()
            sign = "+" if avg > 0 else ""
            mcol3.metric("Avg Score", f"{sign}{avg:.1f}")
            if "putting_hcp" in filtered.columns:
                latest_hcp = pd.to_numeric(filtered["putting_hcp"], errors="coerce").iloc[-1]
                mcol4.metric("Latest HCP", f"{latest_hcp:+.1f}")
        elif selected_test == "Luke Donald Drill":
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Total Sessions", len(filtered))
            mcol2.metric("Best Score", f"{int(filtered['score'].max())}/20")
            mcol3.metric("Avg Score", f"{filtered['score'].mean():.1f}/20")
            goal_met = (filtered["score"] >= LUKE_DONALD_GOAL).sum()
            mcol4.metric("Goal Hit", f"{goal_met}/{len(filtered)}")
        else:
            mcol1, mcol2 = st.columns(2)
            mcol1.metric("Total Sessions", len(filtered))
            mcol2.metric("Best Score", int(filtered["score"].max()))

        # Trend chart
        if len(filtered) >= 2 and "date" in filtered.columns:
            trend = filtered.sort_values("date")

            if selected_test == "Swedish Drill":
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend["date"], y=trend["score"],
                    mode="lines+markers",
                    line=dict(color="#66bb6a", width=2),
                    marker=dict(size=8),
                    name="Score",
                ))
                if len(trend) >= 3:
                    trend["score_ma"] = trend["score"].rolling(window=3, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=trend["date"], y=trend["score_ma"],
                        mode="lines",
                        line=dict(color="#ffffff", width=3),
                        name="3-Session Avg",
                    ))
                # Benchmark lines
                for bm_score, bm_label in SWEDISH_BENCHMARKS:
                    if -8 <= bm_score <= 15:
                        fig.add_hline(
                            y=bm_score,
                            line_dash="dot",
                            line_color="rgba(255,255,255,0.2)",
                            annotation_text=bm_label,
                            annotation_position="right",
                        )
                fig.update_layout(
                    yaxis_title="Total Score",
                    xaxis_title="Date",
                    height=400,
                    margin=dict(l=40, r=100, t=20, b=40),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True)
            elif selected_test == "Luke Donald Drill":
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend["date"], y=trend["score"],
                    mode="lines+markers",
                    line=dict(color="#66bb6a", width=2),
                    marker=dict(size=8),
                    name="Makes",
                    hovertemplate="Date: %{x|%b %d}<br>Makes: %{y}/20<extra></extra>",
                ))
                if len(trend) >= 3:
                    trend["score_ma"] = trend["score"].rolling(window=3, min_periods=1).mean()
                    fig.add_trace(go.Scatter(
                        x=trend["date"], y=trend["score_ma"],
                        mode="lines",
                        line=dict(color="#ffffff", width=3),
                        name="3-Session Avg",
                    ))
                fig.add_hline(
                    y=LUKE_DONALD_GOAL, line_dash="dash", line_color="#ffa726",
                    annotation_text=f"Goal: {LUKE_DONALD_GOAL}/20",
                    annotation_position="right",
                )
                fig.update_layout(
                    yaxis_title="Makes (out of 20)",
                    xaxis_title="Date",
                    yaxis=dict(range=[0, 21]),
                    height=300,
                    margin=dict(l=40, r=80, t=20, b=40),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend["date"], y=trend["score"],
                    mode="lines+markers",
                    line=dict(color="#66bb6a", width=2),
                    marker=dict(size=8),
                    name="Score",
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
                    yaxis_title="Score",
                    xaxis_title="Date",
                    height=300,
                    margin=dict(l=40, r=20, t=20, b=40),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True)

        # Distance breakdown (Lag Drill specific)
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

        # Distance make % breakdown (Luke Donald specific)
        if selected_test == "Luke Donald Drill" and len(filtered) >= 1:
            dist_pcts = {}
            for dist in LUKE_DONALD_DISTANCES:
                cols_for_dist = [f"ld_h{h}_{dist}ft" for h in LUKE_DONALD_HOLES]
                present = [c for c in cols_for_dist if c in filtered.columns]
                if present:
                    vals = filtered[present].apply(pd.to_numeric, errors="coerce")
                    dist_pcts[f"{dist}ft"] = vals.values.mean() * 100
            if dist_pcts:
                fig_bar = go.Figure(data=[go.Bar(
                    x=list(dist_pcts.keys()),
                    y=list(dist_pcts.values()),
                    marker_color=["#2e7d32", "#388e3c", "#43a047", "#4caf50", "#66bb6a"],
                    text=[f"{v:.0f}%" for v in dist_pcts.values()],
                    textposition="outside",
                )])
                fig_bar.update_layout(
                    yaxis_title="Make %",
                    yaxis=dict(range=[0, 105]),
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

        col_map = {"date": "Date", "test_type": "Test", "score": "Score", "putting_hcp": "Putting HCP"}
        for label, col in LAG_FIELDS:
            col_map[col] = label
        display = display.rename(columns={k: v for k, v in col_map.items() if k in display.columns})
        # Drop internal columns from display
        drop_cols = ["Test"]
        if selected_test == "Luke Donald Drill":
            drop_cols += [c for c in display.columns if c.startswith("ld_h")]
        display = display.drop(columns=[c for c in drop_cols if c in display.columns], errors="ignore")

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
