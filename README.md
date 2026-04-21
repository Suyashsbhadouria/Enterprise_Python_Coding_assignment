# Enterprise Python Coding Assignment

End-to-end ELT + Analytics Dashboard for ICC Women's Cricket World Cup data.

## What This Project Delivers

- ELT pipeline that reads all JSON files from `dataset/`.
- Generated CSV layers in `csv_data/`:
	- `matches.csv`
	- `deliveries.csv`
	- `batting.csv`
	- `bowling.csv`
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
- `app.py`: Flask app, analytics transforms, page routes, API routes.
- `templates/`: Jinja templates for all dashboard pages.
- `dataset/`: source JSON match files.
- `csv_data/`: ELT output data used by the dashboard.
- `stitch_women_s_world_cup_analytics/`: UI reference screens/code.

## ELT Workflow

1. Extract from all `*.json` files in `dataset/`.
2. Transform into match-level and ball/player-level analytics tables.
3. Load transformed outputs into CSV files under `csv_data/`.

Run ELT manually:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py
```

Latest successful run metrics:

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

Start server:

```powershell
.\.venv\Scripts\python.exe app.py
```

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

- The container automatically ensures CSV files are present before starting the app.
- Works on any machine with Docker installed (Windows, macOS, Linux).

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

## Submission Readiness Checklist

- ELT pipeline runs end-to-end from JSON to CSV.
- Dashboard pages render with transformed CSV data.
- All primary navigation and call-to-actions resolve to working routes.
- Filters/search on key pages are functional.
- API endpoints return JSON successfully.
