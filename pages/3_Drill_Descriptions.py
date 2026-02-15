"""
Drill Descriptions — reference for all drills and their progression levels.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.data_manager import load_drills

st.set_page_config(page_title="Drill Descriptions", page_icon="📖", layout="wide")

st.title("📖 Drill Descriptions")
st.caption("All drills and their progression levels in one place.")

drills = load_drills()

if not drills:
    st.info("No drill data found. Run the Excel import first.")
    st.stop()

BALL_STRIKING_DRILLS = {"Towel drill", "Closed Eye", "Heel, Toe, Center", "3 Club Spray", "Wedge Ladder", "1 Hand Pitch"}
PUTTING_DRILLS = {"3-foot Putt", "Guess slope"}

ball_striking = [d for d in drills if d["name"] in BALL_STRIKING_DRILLS]
putting = [d for d in drills if d["name"] in PUTTING_DRILLS]


def _render_drills(drill_list):
    for drill in drill_list:
        name = drill["name"]
        levels = drill.get("levels", {})
        desc = drill.get("description")

        header = name + (f" — *{desc}*" if desc else "")
        st.subheader(header)

        if levels:
            cols = st.columns(len(levels))
            for col, (level_name, level_desc) in zip(cols, levels.items()):
                with col:
                    st.caption(level_name)
                    st.markdown(level_desc)
        st.markdown("---")


tab_bs, tab_putt = st.tabs(["Ball Striking", "Putting"])

with tab_bs:
    _render_drills(ball_striking)

with tab_putt:
    _render_drills(putting)
