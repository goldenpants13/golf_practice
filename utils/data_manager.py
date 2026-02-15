"""
Centralized data access layer for the Golf Practice app.
All CSV/JSON reads and writes go through this module so that
swapping the storage backend later (e.g. for cloud deployment)
requires changes in only one place.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _csv_path(name: str) -> Path:
    return DATA_DIR / f"{name}.csv"


def _json_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


# ---------------------------------------------------------------------------
# Generic CSV helpers
# ---------------------------------------------------------------------------

def load_csv(name: str) -> pd.DataFrame:
    """Load a CSV from the data directory. Returns an empty DataFrame if the
    file does not exist yet."""
    path = _csv_path(name)
    if path.exists() and path.stat().st_size > 0:
        # Peek at columns first to avoid parse_dates errors on files
        # that don't have a "date" column or have no data rows.
        try:
            df = pd.read_csv(path)
            if "date" in df.columns and not df.empty:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            return df
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
    return pd.DataFrame()


def save_csv(name: str, df: pd.DataFrame) -> None:
    """Overwrite the CSV in the data directory with the given DataFrame."""
    _ensure_data_dir()
    df.to_csv(_csv_path(name), index=False)


def append_csv_row(name: str, row: dict) -> None:
    """Append a single row to a CSV file (creates it if missing)."""
    df = load_csv(name)
    new_row = pd.DataFrame([row])
    df = pd.concat([df, new_row], ignore_index=True)
    save_csv(name, df)


# ---------------------------------------------------------------------------
# Generic JSON helpers
# ---------------------------------------------------------------------------

def load_json(name: str) -> Any:
    """Load a JSON file from the data directory. Returns None if missing."""
    path = _json_path(name)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_json(name: str, data: Any) -> None:
    """Write data to a JSON file in the data directory."""
    _ensure_data_dir()
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


# ---------------------------------------------------------------------------
# Aggregation helpers (used by the dashboard)
# ---------------------------------------------------------------------------

def all_practice_dates() -> List[date]:
    """Return a sorted list of all unique dates across all practice types."""
    dates = set()
    for name in ("ball_striking", "putting", "short_game", "testing"):
        df = load_csv(name)
        if not df.empty and "date" in df.columns:
            for d in pd.to_datetime(df["date"]).dt.date:
                dates.add(d)
    return sorted(dates)


def practice_session_counts() -> Dict[str, int]:
    """Return total session counts per practice category."""
    counts = {}
    for name in ("ball_striking", "putting", "short_game", "testing"):
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
    # Start from today or the last practice day
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
