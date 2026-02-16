"""
Centralized data access layer for the Golf Practice app.
All dynamic data (practice logs, testing, rounds) is stored in Google Sheets.
Static reference data (goals, drills, lookup tables) stays in local JSON files.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Google Sheets connection
# ---------------------------------------------------------------------------

def _get_conn():
    """Return the cached Google Sheets connection."""
    from streamlit_gsheets import GSheetsConnection
    return st.connection("gsheets", type=GSheetsConnection)


# ---------------------------------------------------------------------------
# Google Sheets helpers (replaces CSV read/write)
# ---------------------------------------------------------------------------

def load_csv(name: str) -> pd.DataFrame:
    """Load a worksheet from Google Sheets. Returns an empty DataFrame if
    the worksheet is empty or doesn't exist."""
    try:
        conn = _get_conn()
        df = conn.read(worksheet=name, ttl="0")
        if df is None:
            return pd.DataFrame()
        # Drop fully-empty rows that gsheets sometimes returns
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame()
        # Clean date column -- handle "2026-02-01 0:00:00" format from Sheets
        if "date" in df.columns:
            df["date"] = df["date"].astype(str).str.split(" ").str[0]
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def save_csv(name: str, df: pd.DataFrame) -> None:
    """Overwrite a worksheet in Google Sheets with the given DataFrame."""
    conn = _get_conn()
    # Convert datetime columns to strings for Sheets compatibility
    df_out = df.copy()
    for col in df_out.columns:
        if pd.api.types.is_datetime64_any_dtype(df_out[col]):
            df_out[col] = df_out[col].dt.strftime("%Y-%m-%d")
        # Also handle any date strings with time components
        if col == "date":
            df_out[col] = df_out[col].astype(str).str.split(" ").str[0]
    conn.update(worksheet=name, data=df_out)


def append_csv_row(name: str, row: dict) -> None:
    """Append a single row to a Google Sheets worksheet."""
    df = load_csv(name)
    new_row = pd.DataFrame([row])
    df = pd.concat([df, new_row], ignore_index=True)
    save_csv(name, df)


def delete_csv_row(name: str, idx: int) -> None:
    """Delete a row by index from a Google Sheets worksheet."""
    df = load_csv(name)
    if 0 <= idx < len(df):
        df = df.drop(index=idx).reset_index(drop=True)
        save_csv(name, df)


# ---------------------------------------------------------------------------
# JSON helpers (for static reference data that ships with the repo)
# ---------------------------------------------------------------------------

def _json_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load_json(name: str) -> Any:
    """Load a JSON file from the data directory. Returns None if missing."""
    path = _json_path(name)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_json(name: str, data: Any) -> None:
    """Write data to a JSON file in the data directory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_json_path(name), "w") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Domain-specific loaders
# ---------------------------------------------------------------------------

def load_ball_striking() -> pd.DataFrame:
    return load_csv("ball_striking")


def load_putting() -> pd.DataFrame:
    return load_csv("putting")


def load_short_game() -> pd.DataFrame:
    return load_csv("short_game")


def load_testing() -> pd.DataFrame:
    return load_csv("testing")


def load_three_hole_loop() -> pd.DataFrame:
    return load_csv("three_hole_loop")


def load_wedge_ladder() -> pd.DataFrame:
    return load_csv("wedge_ladder")


def load_goals() -> Optional[dict]:
    return load_json("goals")


def load_drills() -> Optional[dict]:
    return load_json("drills")


def load_testing_lookup() -> Optional[dict]:
    return load_json("testing_lookup")


# ---------------------------------------------------------------------------
# Domain-specific savers
# ---------------------------------------------------------------------------

def save_ball_striking_session(row: dict) -> None:
    append_csv_row("ball_striking", row)


def save_putting_session(row: dict) -> None:
    append_csv_row("putting", row)


def save_short_game_session(row: dict) -> None:
    append_csv_row("short_game", row)


def save_testing_session(row: dict) -> None:
    append_csv_row("testing", row)


def save_three_hole_loop_round(row: dict) -> None:
    append_csv_row("three_hole_loop", row)


def save_wedge_ladder_session(row: dict) -> None:
    append_csv_row("wedge_ladder", row)


# ---------------------------------------------------------------------------
# Aggregation helpers (used by the dashboard)
# ---------------------------------------------------------------------------

def all_practice_dates() -> List[date]:
    """Return a sorted list of all unique dates across all practice types."""
    dates = set()
    for name in ("ball_striking", "putting", "short_game", "testing", "three_hole_loop", "wedge_ladder"):
        df = load_csv(name)
        if not df.empty and "date" in df.columns:
            for d in pd.to_datetime(df["date"]).dt.date:
                dates.add(d)
    return sorted(dates)


def practice_session_counts() -> Dict[str, int]:
    """Return total session counts per practice category."""
    counts = {}
    for name in ("ball_striking", "putting", "short_game", "testing", "three_hole_loop", "wedge_ladder"):
        df = load_csv(name)
        counts[name] = len(df)
    return counts


def current_streak(dates=None) -> int:
    """Calculate the current consecutive-day practice streak ending today
    (or the most recent practice day)."""
    if dates is None:
        dates = all_practice_dates()
    if not dates:
        return 0
    today = date.today()
    if dates[-1] < today:
        check = dates[-1]
    else:
        check = today
    streak = 0
    for d in reversed(dates):
        if d == check:
            streak += 1
            check = date.fromordinal(check.toordinal() - 1)
        elif d < check:
            break
    return streak


def longest_streak(dates=None) -> int:
    """Calculate the longest consecutive-day practice streak."""
    if dates is None:
        dates = all_practice_dates()
    if not dates:
        return 0
    best = 1
    run = 1
    for i in range(1, len(dates)):
        if (dates[i].toordinal() - dates[i - 1].toordinal()) == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best
