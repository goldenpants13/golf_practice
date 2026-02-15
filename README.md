# Golf Practice Tracker

A Streamlit web app for tracking golf practice sessions, short game testing, drill progression, and backyard 3-hole loop rounds. Data is stored persistently in Google Sheets, so it works from any device.

**Live app:** Deployed on [Streamlit Community Cloud](https://share.streamlit.io)
**Repository:** [github.com/goldenpants13/golf_practice](https://github.com/goldenpants13/golf_practice)

---

## Pages

### 1. Dashboard (`app.py`)

The home page. Shows an overview of all practice activity.

- **Key metrics** — Total sessions, current streak, longest streak, sessions this month
- **Practice frequency heatmap** — GitHub-style calendar showing which days you practiced
- **Sessions by category** — Donut chart breaking down ball striking, putting, short game, testing, and 3-hole loop sessions
- **Recent activity** — Table of the last 10 sessions across all categories with drill summaries
- **Goals** — Tabbed view of big goals, component goals, and sub-goals (read from `data/goals.json`)

### 2. Practice Log (`pages/1_Practice_Log.py`)

Log practice sessions across three categories via tabbed forms.

**Ball Striking tab:**
- 8 drill inputs: Mechanical (balls), Towel Drill, Eyes Close Strike, Toe/Heel/Center, Jump the Ball, Wedge Ladder, Crazy Shit, 1 Handed Pitch
- Each measured in sets or ball count
- Recent sessions table below the form

**Putting tab:**
- 3 drill inputs: 3-Foot Drill, Guess the Slope, Lag Drill
- Each measured in sets

**Short Game tab:**
- Freeform notes and duration (minutes)
- For any short game work that doesn't fit the other categories

### 3. Short Game Testing (`pages/2_Short_Game_Testing.py`)

A scorecard for testing your short game with handicap-based scoring.

**8 shot types:** 50 Yards F, 30 Yards F, 10 F Chip, 20 Yards R, Flop, 15 F Pitch, 8 Yard Sand, 15 Yard Sand

- Enter raw scores for each shot type
- App auto-calculates a handicap per shot type using lookup tables (`data/testing_lookup.json`)
- Shows summary metrics: shots tested and average handicap
- Color-coded bar chart (green = scratch or better, orange = mid, red = high handicap)
- **Historical trend chart** with:
  - Adjustable number of sessions to display
  - Moving average overlay with adjustable window
  - Dropdown to view average handicap or any individual shot type
- Full test history table

### 4. Drill Descriptions (`pages/3_Drill_Descriptions.py`)

Reference page showing all drills and their progression levels.

**Ball Striking tab:** Towel Drill, Closed Eye, Heel/Toe/Center, 3 Club Spray, Wedge Ladder, 1 Hand Pitch — each with Level 1 through Level 3 or 4 progression criteria.

**Putting tab:** 3-Foot Putt, Guess Slope — each with level progression.

Drill data is read from `data/drills.json`.

### 5. Three-Hole Loop (`pages/4_Three_Hole_Loop.py`)

Track rounds on the backyard 3-hole loop.

**Holes:**
| Hole | Par |
|------|-----|
| 1    | 5   |
| 2    | 3   |
| 3    | 4   |
| **Total** | **12** |

**Stats tracked per hole:** Score, Fairway (holes 1 & 3), GIR, Up/Down Chance, Up/Down Converted, Penalty

**Visualizations:**
- Summary metrics: rounds played, scoring avg vs par, FW%, GIR%, up-and-down %, penalties per round
- Scoring trend line chart with moving average and par reference line
- Per-hole average score vs par (grouped bar chart)
- Rolling stat percentages (FW%, GIR%, Up/Down %) over time
- Penalty frequency donut chart
- Recent rounds table with stat summaries

---

## Project Structure

```
golf_practice/
├── app.py                          # Dashboard (home page)
├── pages/
│   ├── 1_Practice_Log.py           # Log ball striking, putting, short game
│   ├── 2_Short_Game_Testing.py     # Scorecard with handicap calculation
│   ├── 3_Drill_Descriptions.py     # Drill reference with levels
│   └── 4_Three_Hole_Loop.py        # 3-hole round tracking
├── utils/
│   ├── __init__.py
│   ├── data_manager.py             # All data read/write (Google Sheets + JSON)
│   ├── import_excel.py             # One-time: import from Golf 2026.xlsx
│   └── import_to_sheets.py         # One-time: seed Google Sheets from CSVs
├── data/
│   ├── goals.json                  # Goals hierarchy (static)
│   ├── drills.json                 # Drill descriptions and levels (static)
│   ├── testing_lookup.json         # Handicap lookup tables (static)
│   ├── ball_striking.csv           # Legacy local data (no longer used)
│   ├── putting.csv                 # Legacy local data (no longer used)
│   ├── short_game.csv              # Legacy local data (no longer used)
│   └── testing.csv                 # Legacy local data (no longer used)
├── .streamlit/
│   ├── config.toml                 # Theme configuration (dark green)
│   └── secrets.toml                # Google Sheets credentials (NOT in git)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Data Storage

### Dynamic data (Google Sheets)

All practice logs, test results, and round data are stored in a Google Sheet called "Practice Data DB" with one worksheet per data type:

| Worksheet | Contents |
|-----------|----------|
| `ball_striking` | Ball striking practice sessions |
| `putting` | Putting practice sessions |
| `short_game` | Short game practice sessions |
| `testing` | Short game test results (raw scores) |
| `three_hole_loop` | 3-hole loop rounds |

Data access goes through `utils/data_manager.py`, which uses `st-gsheets-connection` to read and write. All page files call functions like `load_ball_striking()` and `save_ball_striking_session(row)` — they never touch Google Sheets directly.

### Static data (JSON files in `data/`)

Reference data that doesn't change from the app:

- **`goals.json`** — Big goals, component goals, and sub-goals
- **`drills.json`** — Drill names, progression levels, and descriptions
- **`testing_lookup.json`** — Score-to-handicap conversion tables for each shot type

To edit goals or drills, modify these JSON files directly and push to GitHub.

---

## How to Run Locally

### Prerequisites
- Python 3.9+
- A `.streamlit/secrets.toml` file with Google Sheets credentials (see below)

### Steps

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## How to Deploy Changes

Whenever you make changes in Cursor:

1. Ask the AI to "commit and push to GitHub"
2. It runs: `git add -A && git commit -m "description" && git push`
3. Streamlit Cloud auto-detects the push and redeploys (takes ~1-2 minutes)

That's it. No manual deployment steps.

---

## Google Sheets Setup

The app connects to Google Sheets via a service account. Setup was done once:

1. **Google Cloud project** (`golf-practice-db`) with Sheets API and Drive API enabled
2. **Service account** (`golf-app@golf-practice-db.iam.gserviceaccount.com`) with a JSON key
3. **Google Sheet** shared with the service account email as Editor
4. **Credentials** stored in:
   - Locally: `.streamlit/secrets.toml` (git-ignored)
   - Streamlit Cloud: Settings > Secrets

### secrets.toml format

```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

---

## How to Add or Modify Things

### Add a new drill to Practice Log

1. Open `pages/1_Practice_Log.py`
2. Add a new `st.number_input()` in the appropriate tab
3. Add the corresponding key to the `row` dict that gets saved
4. The Google Sheet will automatically gain the new column

### Edit goals

1. Open `data/goals.json`
2. Edit the JSON directly — add/remove/modify goals
3. Commit and push

### Edit drill descriptions or levels

1. Open `data/drills.json`
2. Modify the drill entries
3. Commit and push

### Add a new shot type to testing

1. Add the score-to-handicap table in `data/testing_lookup.json`
2. Add the shot name to `SHOT_TYPES` and column name to `SHOT_CSV_COLS` in `pages/2_Short_Game_Testing.py`

---

## Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[Pandas](https://pandas.pydata.org/)** — Data manipulation
- **[Plotly](https://plotly.com/python/)** — Interactive charts
- **[st-gsheets-connection](https://github.com/streamlit/gsheets-connection)** — Google Sheets integration
- **[Google Sheets](https://sheets.google.com/)** — Persistent cloud storage
- **[Streamlit Community Cloud](https://share.streamlit.io/)** — Free hosting
