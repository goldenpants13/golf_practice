"""
Practice Log — log ball-striking and putting sessions.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import (
    delete_csv_row,
    load_ball_striking,
    load_putting,
    save_ball_striking_session,
    save_putting_session,
)

st.set_page_config(page_title="Practice Log", page_icon="📝", layout="wide")

st.title("📝 Practice Log")
st.caption("Record your practice sessions across all categories.")


def _show_table_with_delete(raw_df, display_df, sheet_name, label, key_prefix):
    """Show a dataframe with row selection and a delete button."""
    sorted_display = display_df.sort_values("Date", ascending=False) if "Date" in display_df.columns else display_df
    original_indices = sorted_display.index.tolist()
    sorted_display = sorted_display.reset_index(drop=True)

    event = st.dataframe(
        sorted_display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"{key_prefix}_table",
    )

    if event.selection.rows:
        sel_pos = event.selection.rows[0]
        orig_idx = original_indices[sel_pos]
        row_date = sorted_display.loc[sel_pos, "Date"] if "Date" in sorted_display.columns else ""
        if st.button(
            f"🗑️  Delete selected {label} session ({row_date})",
            key=f"{key_prefix}_delete_btn",
            type="secondary",
        ):
            delete_csv_row(sheet_name, orig_idx)
            st.success("Session deleted.")
            st.rerun()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_bs, tab_putt = st.tabs(["Ball Striking", "Putting"])

# ========================  BALL STRIKING  ==================================
with tab_bs:
    st.subheader("Ball Striking Session")

    with st.form("ball_striking_form", clear_on_submit=True):
        bs_date = st.date_input("Date", value=date.today(), key="bs_date")

        c1, c2, c3 = st.columns(3)
        with c1:
            mechanical = st.number_input(
                "Mechanical (No Results) — balls", min_value=0, value=0, step=5, key="bs_mech"
            )
            towel = st.number_input(
                "Towel Drill (sets of 3)", min_value=0, value=0, step=1, key="bs_towel"
            )
            eyes_close = st.number_input(
                "Eyes Close Strike (sets of 3)", min_value=0, value=0, step=1, key="bs_eyes"
            )
        with c2:
            toe_heel = st.number_input(
                "Toe, Heel, Center (sets of 3)", min_value=0, value=0, step=1, key="bs_toe"
            )
            jump_ball = st.number_input(
                "Jump the Ball", min_value=0, value=0, step=1, key="bs_jump"
            )
            wedge_ladder = st.number_input(
                "Wedge Ladder (sets of 3)", min_value=0, value=0, step=1, key="bs_wedge"
            )
        with c3:
            crazy = st.number_input(
                "Crazy Shit (sets of 1)", min_value=0, value=0, step=1, key="bs_crazy"
            )
            one_hand = st.number_input(
                "1 Handed Pitch (sets of 3)", min_value=0, value=0, step=1, key="bs_onehand"
            )

        submitted_bs = st.form_submit_button("Log Ball Striking Session", type="primary")

    if submitted_bs:
        row = {
            "date": bs_date.strftime("%Y-%m-%d"),
            "mechanical_no_results": mechanical if mechanical else None,
            "towel_drill_3x": towel if towel else None,
            "eyes_close_strike_3x": eyes_close if eyes_close else None,
            "toe_heel_center_3x": toe_heel if toe_heel else None,
            "jump_the_ball": jump_ball if jump_ball else None,
            "wedge_ladder_3x": wedge_ladder if wedge_ladder else None,
            "crazy_shit_1x": crazy if crazy else None,
            "one_handed_pitch_3x": one_hand if one_hand else None,
        }
        drills_logged = [v for k, v in row.items() if k != "date" and v]
        if drills_logged:
            save_ball_striking_session(row)
            st.success(
                f"Logged ball striking session on {bs_date.strftime('%b %d')} — "
                f"{len(drills_logged)} drill(s) recorded."
            )
            st.rerun()
        else:
            st.warning("Enter at least one drill before submitting.")

    st.markdown("#### Recent Ball Striking Sessions")
    bs_df = load_ball_striking()
    if not bs_df.empty:
        display = bs_df.copy()
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%b %d, %Y")
        col_map = {
            "date": "Date",
            "mechanical_no_results": "Mechanical",
            "towel_drill_3x": "Towel",
            "eyes_close_strike_3x": "Eyes Close",
            "toe_heel_center_3x": "Toe/Heel/Ctr",
            "jump_the_ball": "Jump Ball",
            "wedge_ladder_3x": "Wedge Ladder",
            "crazy_shit_1x": "Crazy Shit",
            "one_handed_pitch_3x": "1-Hand Pitch",
        }
        display = display.rename(columns=col_map)
        _show_table_with_delete(bs_df, display, "ball_striking", "ball striking", "bs")
    else:
        st.info("No ball striking sessions logged yet.")


# ========================  PUTTING  ========================================
with tab_putt:
    st.subheader("Putting Session")

    with st.form("putting_form", clear_on_submit=True):
        putt_date = st.date_input("Date", value=date.today(), key="putt_date")

        c1, c2, c3 = st.columns(3)
        with c1:
            three_foot = st.number_input(
                "3-Foot Drill (sets)", min_value=0, value=0, step=1, key="putt_3ft"
            )
        with c2:
            slope = st.number_input(
                "Guess the Slope (sets)", min_value=0, value=0, step=1, key="putt_slope"
            )
        with c3:
            lag = st.number_input(
                "Lag Drill (sets)", min_value=0, value=0, step=1, key="putt_lag"
            )

        submitted_putt = st.form_submit_button("Log Putting Session", type="primary")

    if submitted_putt:
        row = {
            "date": putt_date.strftime("%Y-%m-%d"),
            "three_foot_drill": three_foot if three_foot else None,
            "guess_the_slope": slope if slope else None,
            "lag_drill": lag if lag else None,
        }
        drills_logged = [v for k, v in row.items() if k != "date" and v]
        if drills_logged:
            save_putting_session(row)
            st.success(
                f"Logged putting session on {putt_date.strftime('%b %d')} — "
                f"{len(drills_logged)} drill(s) recorded."
            )
            st.rerun()
        else:
            st.warning("Enter at least one drill before submitting.")

    st.markdown("#### Recent Putting Sessions")
    putt_df = load_putting()
    if not putt_df.empty:
        display = putt_df.copy()
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%b %d, %Y")
        col_map = {
            "date": "Date",
            "three_foot_drill": "3-Foot Drill",
            "guess_the_slope": "Guess Slope",
            "lag_drill": "Lag Drill",
        }
        display = display.rename(columns=col_map)
        _show_table_with_delete(putt_df, display, "putting", "putting", "putt")
    else:
        st.info("No putting sessions logged yet.")
