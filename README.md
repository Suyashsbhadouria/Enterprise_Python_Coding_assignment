# Enterprise Python Coding Assignment

End-to-end ELT + Analytics Dashboard for ICC Women's Cricket World Cup data.

## What This Project Delivers

- ELT pipeline that reads all JSON files from `Dataset/Raw/` and can generate transformed CSVs.
- Flask app fetches analytics datasets at runtime from Appwrite Database (not from local CSV files).
- Four Appwrite collections mirror the CSV schemas exactly:
	- `matches`
	- `deliveries`
	- `batting`
	- `bowling`
- Flask web application with a multi-page UI inspired by the provided design references in `stitch_women_s_world_cup_analytics/`.
- Working navigation and interactions:
	- Overview
	- Matches (city/team filters + search)
	- Batters (search)
	- Teams
	- Live Match Center, Settings, Support routes
- API endpoints for each analytics page.

## Project Structure

- `etl_pipeline.py`: Extract + load + transform JSON into CSV outputs.
- `app.py`: Flask routes and analytics orchestration.
- `Appwrite/schema.py`: Canonical schema definitions for all four collections.
- `templates/`: Jinja templates for all dashboard pages.
- `dataset/`: source JSON match files.
- `csv_data/`: ELT output data used by the dashboard.
- `stitch_women_s_world_cup_analytics/`: UI reference screens/code.

## Appwrite Runtime Setup

The dashboard reads analytics data at runtime from Appwrite collections.

Set these environment variables before starting the app:

```env
APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1
APPWRITE_PROJECT_ID=your_project_id
APPWRITE_API_KEY=your_api_key
APPWRITE_DATABASE_ID=your_database_id

APPWRITE_COLLECTION_MATCHES_ID=matches
APPWRITE_COLLECTION_DELIVERIES_ID=deliveries
APPWRITE_COLLECTION_BATTING_ID=batting
APPWRITE_COLLECTION_BOWLING_ID=bowling

APPWRITE_CACHE_TTL_SECONDS=300
```

## ELT Workflow (optional for DB seeding)

1. Extract from all `*.json` files in `dataset/`.
2. Transform into match-level and ball/player-level analytics tables.
3. Load transformed outputs into CSV files (optional staging before inserting into Appwrite).

Run ELT manually:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py
```

Latest local run metrics:

- 102 JSON files processed
- 102 match rows
- 52,713 delivery rows
- 1,761 batting rows
- 1,238 bowling rows

## Run The App

Install dependencies (if needed):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
install the dependencies
Start server:

```powershell
.\.venv\Scripts\python.exe app.py
```

Optional Gemini chat configuration (for floating in-app chatbot):

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
$env:GEMINI_MODEL="gemini-2.5-flash-lite"
$env:SLACK_WEBHOOK_URL="url"
```

Or use a local `.env` file in project root:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
APP_NAME=BoundaryLine Intelligence




# Database Configuration
SQLALCHEMY_DATABASE_URI=sqlite:///users.db
```

Notes:

- If `GEMINI_API_KEY` is not set, chatbot replies with a configuration prompt.
- Chatbot is restricted to cricket questions and instructed to answer from dashboard dataset context only.
- Runtime analytics data is fetched from Appwrite collections.

Logging configuration (optional):

```env
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE_NAME=app.log
LOG_MAX_BYTES=1048576
LOG_BACKUP_COUNT=5
```

- Logs are written to a rotating file (default: `logs/app.log`) and also printed to console.

Open:

- `http://127.0.0.1:5000/`

## Run With Docker

Build image:

```powershell
docker build -t women-world-cup-analytics .
```

Run container:

```powershell
docker run --rm -p 5000:5000 --name women-world-cup-analytics women-world-cup-analytics
```

Open:

- `http://127.0.0.1:5000/`

Notes:

- The container expects Appwrite environment variables to be set.
- Works on any machine with Docker installed (Windows, macOS, Linux).

## Table Schema (Appwrite)

Canonical schema lives in `Appwrite/schema.py`. The table/collection fields are:

### `matches`

- `match_id` (string)
- `date` (string)
- `city` (string)
- `venue` (string)
- `team1` (string)
- `team2` (string)
- `winner` (string)
- `win_by` (string)
- `win_margin` (integer)
- `event_name` (string)
- `event_stage` (string)
- `match_type` (string)
- `gender` (string)
- `toss_winner` (string)
- `toss_decision` (string)
- `player_of_match` (string)
- `season` (string)
- `overs` (integer)

### `deliveries`

- `match_id` (string)
- `innings` (integer)
- `over` (integer)
- `ball` (integer)
- `batter` (string)
- `bowler` (string)
- `non_striker` (string)
- `batter_runs` (integer)
- `extras` (integer)
- `total_runs` (integer)
- `extras_type` (string)
- `wicket_type` (string)
- `player_dismissed` (string)

### `batting`

- `match_id` (string)
- `innings` (integer)
- `batter` (string)
- `team` (string)
- `runs` (integer)
- `balls_faced` (integer)
- `fours` (integer)
- `sixes` (integer)
- `strike_rate` (double)
- `is_out` (integer)
- `dismissal_kind` (string)

### `bowling`

- `match_id` (string)
- `innings` (integer)
- `bowler` (string)
- `team` (string)
- `overs` (string)
- `deliveries` (integer)
- `legal_deliveries` (integer)
- `runs_conceded` (integer)
- `wickets` (integer)
- `economy` (double)
- `extras_given` (integer)

## Routes

UI Routes:

- `/` (Overview)
- `/matches`
- `/batters`
- `/teams`
- `/live`
- `/settings`
- `/support`

API Routes:

- `/api/overview`
- `/api/matches`
- `/api/batters`
- `/api/teams`
- `/api/chat` (POST body: `{"message":"...","history":[...]}`)
- `/api/logs` (GET with filters)

### Query Logs API

Use `/api/logs` to retrieve and filter log lines.

Examples:

```text
/api/logs
/api/logs?limit=100
/api/logs?level=ERROR
/api/logs?q=matches
/api/logs?since=2026-04-21&until=2026-04-21
/api/logs?include_archived=true
```

Supported query parameters:

- `limit`: max entries returned (`1` to `2000`, default `200`)
- `level`: one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `q`: text search across logger name, message, and level
- `since`: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`, or ISO datetime
- `until`: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`, or ISO datetime
- `include_archived`: `true/false` to include rotated files (`app.log.1`, etc.)

## Submission Readiness Checklist

- ELT pipeline runs end-to-end from JSON to CSV.
- Dashboard pages render with transformed Appwrite data.
- All primary navigation and call-to-actions resolve to working routes.
- Filters/search on key pages are functional.
- API endpoints return JSON successfully.
