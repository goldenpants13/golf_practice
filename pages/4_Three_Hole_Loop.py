"""
3-Hole Loop — log and track rounds on the backyard loop.
"""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import load_three_hole_loop, save_three_hole_loop_round

st.set_page_config(page_title="3-Hole Loop", page_icon="🌙", layout="wide")

st.title("🌙 3-Hole Loop")
st.caption("Track your rounds on the backyard 3-hole loop.")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HOLES = [
    {"num": 1, "par": 5, "has_fairway": True},
    {"num": 2, "par": 3, "has_fairway": False},
    {"num": 3, "par": 4, "has_fairway": True},
]
TOTAL_PAR = sum(h["par"] for h in HOLES)

# ---------------------------------------------------------------------------
# Entry form
# ---------------------------------------------------------------------------
st.subheader("Log a Round")

with st.form("three_hole_form", clear_on_submit=True):
    round_date = st.date_input("Date", value=date.today(), key="loop_date")

    cols = st.columns(3)
    hole_data = {}

    for col, hole in zip(cols, HOLES):
        n = hole["num"]
        par = hole["par"]
        with col:
            st.markdown(f"**Hole {n} (Par {par})**")
            hole_data[f"h{n}_score"] = st.number_input(
                "Score", min_value=1, max_value=15, value=par, step=1,
                key=f"h{n}_score",
            )
            if hole["has_fairway"]:
                hole_data[f"h{n}_fairway"] = st.checkbox("Fairway Hit", key=f"h{n}_fw")
            hole_data[f"h{n}_gir"] = st.checkbox("GIR", key=f"h{n}_gir")
            hole_data[f"h{n}_ud_chance"] = st.checkbox("Up/Down Chance", key=f"h{n}_udc")
            hole_data[f"h{n}_ud_convert"] = st.checkbox(
                "Up/Down Converted", key=f"h{n}_udy",
            )
            hole_data[f"h{n}_penalty"] = st.checkbox("Penalty", key=f"h{n}_pen")

    submitted = st.form_submit_button("Log Round", type="primary")

if submitted:
    row = {"date": round_date.strftime("%Y-%m-%d")}
    for k, v in hole_data.items():
        if isinstance(v, bool):
            row[k] = "Y" if v else "N"
        else:
            row[k] = v
    save_three_hole_loop_round(row)
    st.success(
        f"Round logged for {round_date.strftime('%b %d')} — "
        f"Total: {row['h1_score'] + row['h2_score'] + row['h3_score']} "
        f"(Par {TOTAL_PAR})"
    )
    st.rerun()

# ---------------------------------------------------------------------------
# Load data for visualizations
# ---------------------------------------------------------------------------
df = load_three_hole_loop()

if df.empty:
    st.markdown("---")
    st.info("No rounds logged yet. Play the loop and log your first round above!")
    st.stop()

# Ensure proper types
for h in HOLES:
    n = h["num"]
    df[f"h{n}_score"] = pd.to_numeric(df[f"h{n}_score"], errors="coerce")

df["total_score"] = df["h1_score"] + df["h2_score"] + df["h3_score"]
df["vs_par"] = df["total_score"] - TOTAL_PAR
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

total_rounds = len(df)

# ---------------------------------------------------------------------------
# Helper to compute percentages from Y/N columns
# ---------------------------------------------------------------------------
def _yn_pct(series):
    valid = series.dropna()
    valid = valid[valid.isin(["Y", "N"])]
    if len(valid) == 0:
        return 0.0
    return (valid == "Y").sum() / len(valid) * 100


def _yn_pct_series(col_names):
    """Compute percentage across multiple Y/N columns for each row,
    then return overall percentage."""
    total_y = 0
    total_valid = 0
    for col in col_names:
        if col in df.columns:
            valid = df[col].dropna()
            valid = valid[valid.isin(["Y", "N"])]
            total_y += (valid == "Y").sum()
            total_valid += len(valid)
    if total_valid == 0:
        return 0.0
    return total_y / total_valid * 100


# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Summary")

scoring_avg = df["total_score"].mean()
vs_par_avg = df["vs_par"].mean()

fairway_pct = _yn_pct_series(["h1_fairway", "h3_fairway"])
gir_pct = _yn_pct_series(["h1_gir", "h2_gir", "h3_gir"])

# Up/down: only count conversions where there was a chance
ud_chances = 0
ud_converts = 0
for h in HOLES:
    n = h["num"]
    chance_col = f"h{n}_ud_chance"
    convert_col = f"h{n}_ud_convert"
    if chance_col in df.columns and convert_col in df.columns:
        chances = df[chance_col] == "Y"
        ud_chances += chances.sum()
        ud_converts += ((df[chance_col] == "Y") & (df[convert_col] == "Y")).sum()
ud_pct = (ud_converts / ud_chances * 100) if ud_chances > 0 else 0.0

penalty_cols = [f"h{h['num']}_penalty" for h in HOLES]
total_penalties = sum(
    (df[col] == "Y").sum() for col in penalty_cols if col in df.columns
)
penalties_per_round = total_penalties / total_rounds if total_rounds > 0 else 0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Rounds", total_rounds)
m2.metric("Scoring Avg", f"{scoring_avg:.1f}", delta=f"{vs_par_avg:+.1f} vs par",
          delta_color="inverse")
m3.metric("Fairway %", f"{fairway_pct:.0f}%")
m4.metric("GIR %", f"{gir_pct:.0f}%")
m5.metric("Up & Down %", f"{ud_pct:.0f}%")
m6.metric("Penalties/Rnd", f"{penalties_per_round:.1f}")

# ---------------------------------------------------------------------------
# Scoring trend chart
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Scoring Trend")

if total_rounds >= 2:
    trend_c1, trend_c2 = st.columns([1, 3])
    with trend_c1:
        ma_window = st.slider(
            "Moving avg window",
            min_value=2,
            max_value=min(total_rounds, 20),
            value=min(3, total_rounds),
            step=1,
            key="loop_ma",
        )
    with trend_c2:
        plot_df = df.copy()
        plot_df["moving_avg"] = plot_df["total_score"].rolling(
            window=ma_window, min_periods=1
        ).mean()

        fig_score = go.Figure()
        fig_score.add_trace(go.Scatter(
            x=plot_df["date"], y=plot_df["total_score"],
            mode="lines+markers",
            line=dict(color="#66bb6a", width=2),
            marker=dict(size=8),
            name="Score",
        ))
        fig_score.add_trace(go.Scatter(
            x=plot_df["date"], y=plot_df["moving_avg"],
            mode="lines",
            line=dict(color="#ffffff", width=3),
            name=f"{ma_window}-Round Moving Avg",
        ))
        fig_score.add_hline(
            y=TOTAL_PAR, line_dash="dash", line_color="#f44336", opacity=0.5,
            annotation_text=f"Par ({TOTAL_PAR})", annotation_position="top left",
        )
        fig_score.update_layout(
            yaxis_title="Total Score",
            xaxis_title="Date",
            height=350,
            margin=dict(l=40, r=20, t=20, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_score, use_container_width=True)
else:
    st.caption("Play more rounds to see a scoring trend chart.")

# ---------------------------------------------------------------------------
# Per-hole scoring averages vs par
# ---------------------------------------------------------------------------
st.markdown("---")
col_hole_chart, col_stats_chart = st.columns(2)

with col_hole_chart:
    st.subheader("Per-Hole Averages")
    hole_labels = [f"Hole {h['num']}" for h in HOLES]
    hole_avgs = [df[f"h{h['num']}_score"].mean() for h in HOLES]
    hole_pars = [h["par"] for h in HOLES]

    fig_holes = go.Figure()
    fig_holes.add_trace(go.Bar(
        x=hole_labels, y=hole_avgs,
        name="Avg Score",
        marker_color="#66bb6a",
        text=[f"{a:.1f}" for a in hole_avgs],
        textposition="outside",
    ))
    fig_holes.add_trace(go.Bar(
        x=hole_labels, y=hole_pars,
        name="Par",
        marker_color="#424242",
        text=[str(p) for p in hole_pars],
        textposition="outside",
    ))
    fig_holes.update_layout(
        barmode="group",
        yaxis_title="Strokes",
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_holes, use_container_width=True)

# ---------------------------------------------------------------------------
# Stat percentages over time (rolling)
# ---------------------------------------------------------------------------
with col_stats_chart:
    st.subheader("Stats Over Time")

    if total_rounds >= 3:
        stat_window = st.slider(
            "Rolling window",
            min_value=2,
            max_value=min(total_rounds, 20),
            value=min(3, total_rounds),
            step=1,
            key="stat_roll",
        )

        # Compute per-round stats
        round_stats = pd.DataFrame({"date": df["date"]})

        # Fairway: 2 chances per round (holes 1 and 3)
        fw_hits = ((df.get("h1_fairway", pd.Series()) == "Y").astype(int) +
                   (df.get("h3_fairway", pd.Series()) == "Y").astype(int))
        round_stats["fairway_pct"] = fw_hits / 2 * 100

        # GIR: 3 chances per round
        gir_hits = sum(
            (df[f"h{h['num']}_gir"] == "Y").astype(int) for h in HOLES
        )
        round_stats["gir_pct"] = gir_hits / 3 * 100

        # Up/Down: variable chances
        ud_chance_per_round = sum(
            (df[f"h{h['num']}_ud_chance"] == "Y").astype(int) for h in HOLES
        )
        ud_convert_per_round = sum(
            ((df[f"h{h['num']}_ud_chance"] == "Y") &
             (df[f"h{h['num']}_ud_convert"] == "Y")).astype(int) for h in HOLES
        )
        round_stats["ud_pct"] = np.where(
            ud_chance_per_round > 0,
            ud_convert_per_round / ud_chance_per_round * 100,
            np.nan,
        )

        # Rolling averages
        for col in ["fairway_pct", "gir_pct", "ud_pct"]:
            round_stats[f"{col}_roll"] = round_stats[col].rolling(
                window=stat_window, min_periods=1
            ).mean()

        fig_stats = go.Figure()
        fig_stats.add_trace(go.Scatter(
            x=round_stats["date"], y=round_stats["fairway_pct_roll"],
            mode="lines+markers", name="Fairway %",
            line=dict(color="#66bb6a", width=2), marker=dict(size=5),
        ))
        fig_stats.add_trace(go.Scatter(
            x=round_stats["date"], y=round_stats["gir_pct_roll"],
            mode="lines+markers", name="GIR %",
            line=dict(color="#42a5f5", width=2), marker=dict(size=5),
        ))
        fig_stats.add_trace(go.Scatter(
            x=round_stats["date"], y=round_stats["ud_pct_roll"],
            mode="lines+markers", name="Up/Down %",
            line=dict(color="#ffa726", width=2), marker=dict(size=5),
        ))
        fig_stats.update_layout(
            yaxis_title="Percentage",
            xaxis_title="Date",
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_stats, use_container_width=True)
    else:
        st.caption("Play 3+ rounds to see rolling stat trends.")

# ---------------------------------------------------------------------------
# Penalty frequency
# ---------------------------------------------------------------------------
st.markdown("---")
col_pen, col_table = st.columns([1, 2])

with col_pen:
    st.subheader("Penalties")
    rounds_with_penalty = 0
    for _, row in df.iterrows():
        has_pen = any(row.get(f"h{h['num']}_penalty") == "Y" for h in HOLES)
        if has_pen:
            rounds_with_penalty += 1
    rounds_clean = total_rounds - rounds_with_penalty

    fig_pen = go.Figure(data=[go.Pie(
        labels=["Clean", "With Penalty"],
        values=[rounds_clean, rounds_with_penalty],
        hole=0.45,
        marker=dict(colors=["#2e7d32", "#f44336"]),
        textinfo="label+value",
    )])
    fig_pen.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig_pen, use_container_width=True)
    st.caption(f"{total_penalties} total penalties across {total_rounds} rounds")

# ---------------------------------------------------------------------------
# Recent rounds table
# ---------------------------------------------------------------------------
with col_table:
    st.subheader("Recent Rounds")
    display = df.copy().sort_values("date", ascending=False).head(10)
    display["date"] = display["date"].dt.strftime("%b %d, %Y")

    show_cols = ["date"]
    rename = {"date": "Date", "total_score": "Total", "vs_par": "+/-"}
    for h in HOLES:
        n = h["num"]
        col_name = f"h{n}_score"
        show_cols.append(col_name)
        rename[col_name] = f"H{n}"
    show_cols += ["total_score", "vs_par"]

    # Add fairway/GIR/UD summary
    def _round_summary(row):
        parts = []
        # Fairway
        fw = sum(1 for c in ["h1_fairway", "h3_fairway"]
                 if row.get(c) == "Y")
        parts.append(f"FW {fw}/2")
        # GIR
        gir = sum(1 for h in HOLES if row.get(f"h{h['num']}_gir") == "Y")
        parts.append(f"GIR {gir}/3")
        # Up/down
        udc = sum(1 for h in HOLES if row.get(f"h{h['num']}_ud_chance") == "Y")
        udy = sum(1 for h in HOLES
                  if row.get(f"h{h['num']}_ud_chance") == "Y"
                  and row.get(f"h{h['num']}_ud_convert") == "Y")
        if udc > 0:
            parts.append(f"UD {udy}/{udc}")
        # Penalties
        pen = sum(1 for h in HOLES if row.get(f"h{h['num']}_penalty") == "Y")
        if pen > 0:
            parts.append(f"PEN {pen}")
        return " | ".join(parts)

    display["Stats"] = display.apply(_round_summary, axis=1)
    show_cols.append("Stats")

    display = display[show_cols].rename(columns=rename)
    st.dataframe(display, use_container_width=True, hide_index=True)
