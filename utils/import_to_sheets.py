"""
One-time script to upload existing CSV data into Google Sheets worksheets.
Run from project root: python utils/import_to_sheets.py
"""

import sys
from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

_PROJECT_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_DIR / "data"

# Worksheets to seed (CSV filename without extension)
WORKSHEETS = [
    "ball_striking",
    "putting",
    "short_game",
    "testing",
    "three_hole_loop",
]

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Read secrets.toml to get credentials
def _load_secrets():
    import toml
    secrets_path = _PROJECT_DIR / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        print(f"ERROR: {secrets_path} not found")
        sys.exit(1)
    return toml.load(secrets_path)


def run_import():
    secrets = _load_secrets()
    gsheets_config = secrets["connections"]["gsheets"]
    spreadsheet_url = gsheets_config["spreadsheet"]

    # Build credentials from secrets
    creds_info = {
        "type": gsheets_config["type"],
        "project_id": gsheets_config["project_id"],
        "private_key_id": gsheets_config["private_key_id"],
        "private_key": gsheets_config["private_key"],
        "client_email": gsheets_config["client_email"],
        "client_id": gsheets_config["client_id"],
        "auth_uri": gsheets_config["auth_uri"],
        "token_uri": gsheets_config["token_uri"],
        "auth_provider_x509_cert_url": gsheets_config["auth_provider_x509_cert_url"],
        "client_x509_cert_url": gsheets_config["client_x509_cert_url"],
    }

    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_url(spreadsheet_url)

    for ws_name in WORKSHEETS:
        csv_path = _DATA_DIR / f"{ws_name}.csv"
        if not csv_path.exists():
            print(f"  {ws_name}: no CSV file, skipping")
            continue

        df = pd.read_csv(csv_path)
        if df.empty:
            print(f"  {ws_name}: CSV is empty, creating empty worksheet")
            try:
                ws = spreadsheet.worksheet(ws_name)
                ws.clear()
                # Write just headers
                ws.update([df.columns.tolist()])
            except gspread.WorksheetNotFound:
                ws = spreadsheet.add_worksheet(title=ws_name, rows=1, cols=len(df.columns) or 1)
                if not df.columns.empty:
                    ws.update([df.columns.tolist()])
            continue

        # Convert datetime columns to strings
        for col in df.columns:
            if "date" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

        # Replace NaN with empty strings for Sheets
        df = df.fillna("")

        # Get or create the worksheet
        try:
            ws = spreadsheet.worksheet(ws_name)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=ws_name, rows=len(df) + 1, cols=len(df.columns))

        # Write header + data
        data = [df.columns.tolist()] + df.values.tolist()
        ws.update(data)
        print(f"  {ws_name}: {len(df)} rows uploaded")

    print("\nImport to Google Sheets complete!")


if __name__ == "__main__":
    print("Importing CSV data to Google Sheets...")
    run_import()
