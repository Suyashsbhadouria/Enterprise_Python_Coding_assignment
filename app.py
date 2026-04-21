# Srinithi Frontend
"""
Flask Web Application for Women's Cricket World Cup Analytics Dashboard.
Loads transformed CSV data and serves the 'The Kinetic Analyst' dashboard.

"""

import os
import csv
import time
import uuid
import logging
from collections import defaultdict, Counter
from flask import Flask, render_template, jsonify, request, g
from etl_pipeline import run_pipeline
from logging_config import configure_logging

app = Flask(__name__)
logger = configure_logging(__name__)

CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv_data")

# Cache statistics tracking
_cache_stats = {"matches": 0, "batting": 0, "bowling": 0}


def ensure_csv_data():
    """Generate CSV outputs from dataset JSON files if required files are missing."""
    required = ["matches.csv", "deliveries.csv", "batting.csv", "bowling.csv"]
    missing = [name for name in required if not os.path.exists(os.path.join(CSV_DIR, name))]
    if missing:
        logger.warning("Missing CSV outputs: %s; running ETL pipeline", ", ".join(missing))
        run_pipeline()
    else:
        logger.info("CSV data ready; all required files present")


def load_csv(filename):
    """Load a CSV file and return list of dicts."""
    filepath = os.path.join(CSV_DIR, filename)
    start_time = time.perf_counter()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug("CSV load: file=%s rows=%d time=%.1fms", filename, len(rows), elapsed_ms)
        return rows
    except Exception as e:
        logger.exception("Failed to load CSV: %s", filename)
        raise


# ─── Data Loading (cached at module level) ───
_matches = None
_batting = None
_bowling = None


def get_matches():
    global _matches
    if _matches is None:
        _cache_stats["matches"] = 0
        _matches = load_csv("matches.csv")
        logger.info("Cache miss: loaded matches (%d records)", len(_matches))
    else:
        _cache_stats["matches"] += 1
    return _matches


def get_batting():
    global _batting
    if _batting is None:
        _cache_stats["batting"] = 0
        _batting = load_csv("batting.csv")
        logger.info("Cache miss: loaded batting (%d records)", len(_batting))
    else:
        _cache_stats["batting"] += 1
    return _batting


def get_bowling():
    global _bowling
    if _bowling is None:
        _cache_stats["bowling"] = 0
        _bowling = load_csv("bowling.csv")
        logger.info("Cache miss: loaded bowling (%d records)", len(_bowling))
    else:
        _cache_stats["bowling"] += 1
    return _bowling


# ─── Transform Functions ───

def transform_overview():
    """Compute Tournament Overview analytics."""
    matches = get_matches()
    batting = get_batting()

    total_matches = len(matches)

    # Total runs scored across tournament
    total_runs = sum(int(b["runs"]) for b in batting if b.get("runs"))

    # Unique teams
    teams = set()
    for m in matches:
        teams.add(m["team1"])
        teams.add(m["team2"])
    participating_teams = sorted(teams)

    # Unique venues/cities
    venues = set(m["venue"] for m in matches if m["venue"])
    cities = set(m["city"] for m in matches if m["city"])

    # Top winning teams
    win_counts = Counter()
    for m in matches:
        if m["winner"] and m["winner"] not in ("no result", "tie", ""):
            win_counts[m["winner"]] += 1
    top_winners = win_counts.most_common(10)
    max_wins = top_winners[0][1] if top_winners else 1

    # Runs progression over tournament (total runs per match sorted by date)
    matches_sorted = sorted(matches, key=lambda x: x["date"])
    runs_per_match = []
    for m in matches_sorted:
        match_runs = sum(int(b["runs"]) for b in batting if b["match_id"] == m["match_id"] and b.get("runs"))
        runs_per_match.append({
            "match_id": m["match_id"],
            "date": m["date"],
            "total_runs": match_runs,
            "team1": m["team1"],
            "team2": m["team2"],
            "event_stage": m["event_stage"],
        })

    # Recent match results (last 5 by date)
    recent = matches_sorted[-5:][::-1]
    recent_results = []
    for m in recent:
        result_text = ""
        if m["winner"] and m["win_by"] and m["win_margin"]:
            result_text = f"{m['winner']} won by {m['win_margin']} {m['win_by']}"
        elif m["winner"]:
            result_text = f"{m['winner']} won"
        else:
            result_text = m.get("winner", "No result")

        # Determine stage name
        stage = m.get("event_stage", "")
        if not stage:
            stage = "Group"

        recent_results.append({
            "match_id": m["match_id"],
            "date": m["date"],
            "team1": m["team1"],
            "team2": m["team2"],
            "winner": m["winner"],
            "result_text": result_text,
            "venue": m["venue"],
            "city": m["city"],
            "stage": stage,
        })

    # Determine which host country is dominant
    city_counts = Counter(m["city"] for m in matches if m["city"])
    top_city = city_counts.most_common(1)[0] if city_counts else ("", 0)

    data = {
        "total_matches": total_matches,
        "total_runs": total_runs,
        "teams": participating_teams,
        "team_count": len(participating_teams),
        "venue_count": len(venues),
        "city_count": len(cities),
        "top_winners": top_winners,
        "max_wins": max_wins,
        "runs_per_match": runs_per_match,
        "recent_results": recent_results,
        "top_city": top_city,
    }
    logger.info(
        "Overview metrics prepared: matches=%s runs=%s teams=%s venues=%s cities=%s",
        total_matches,
        total_runs,
        len(participating_teams),
        len(venues),
        len(cities),
    )
    return data


@app.before_request
def log_request_start():
    """Log request start with unique request ID."""
    g.request_id = str(uuid.uuid4())[:8]
    g.request_start = time.perf_counter()
    
    # Log request details
    query_str = f"?{request.query_string.decode()}" if request.query_string else ""
    logger.info(
        "REQUEST_START [%s] %s %s%s | UA=%s",
        g.request_id,
        request.method,
        request.path,
        query_str,
        request.user_agent.browser or "unknown",
    )


@app.after_request
def log_request_end(response):
    """Log request completion with timing and status."""
    request_id = getattr(g, "request_id", "unknown")
    start_time = getattr(g, "request_start", None)
    if start_time is not None:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        content_length = response.content_length or len(response.get_data())
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            "REQUEST_END [%s] %s %s -> %s | time=%.1fms size=%dB",
            request_id,
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
            content_length,
        )
    return response


@app.errorhandler(404)
def handle_not_found(error):
    request_id = getattr(g, "request_id", "unknown")
    logger.warning("404_NOT_FOUND [%s] %s %s", request_id, request.method, request.path)
    return render_template("info.html", title="Not Found", subtitle="The requested page does not exist.", message="Check the URL and try again.", active_page=""), 404


@app.errorhandler(500)
def handle_server_error(error):
    request_id = getattr(g, "request_id", "unknown")
    logger.error("500_SERVER_ERROR [%s] %s %s", request_id, request.method, request.path, exc_info=True)
    return render_template("info.html", title="Server Error", subtitle="An unexpected error occurred.", message="Please try again or check the application logs.", active_page=""), 500


def transform_matches(city_filter=None, team_filter=None):
    """Compute Match Analysis data."""
    matches = get_matches()
    batting = get_batting()

    # Filter
    filtered = matches
    if city_filter and city_filter != "All Cities":
        filtered = [m for m in filtered if m["city"] == city_filter]
    if team_filter and team_filter != "All Teams":
        filtered = [m for m in filtered if m["team1"] == team_filter or m["team2"] == team_filter]

    # Sort by date descending
    filtered_sorted = sorted(filtered, key=lambda x: x["date"], reverse=True)

    # Match history with computed match IDs
    match_history = []
    for idx, m in enumerate(filtered_sorted):
        match_history.append({
            "display_id": f"#M-{1000 + len(filtered_sorted) - idx}",
            "match_id": m["match_id"],
            "date": m["date"],
            "team1": m["team1"],
            "team2": m["team2"],
            "venue": m["venue"],
            "city": m["city"],
            "winner": m["winner"],
        })

    # Venue volume
    city_counts = Counter(m["city"] for m in matches if m["city"])
    venue_volume = city_counts.most_common(10)
    max_vol = venue_volume[0][1] if venue_volume else 1

    # Highest avg score by venue
    venue_scores = defaultdict(list)
    for m in matches:
        match_runs = sum(int(b["runs"]) for b in batting if b["match_id"] == m["match_id"] and b.get("runs"))
        if m["venue"]:
            venue_scores[m["venue"]].append(match_runs)

    best_venue = ""
    best_avg = 0
    best_city = ""
    for venue, scores in venue_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        if avg > best_avg:
            best_avg = avg
            best_venue = venue
            # Find city for this venue
            for m in matches:
                if m["venue"] == venue:
                    best_city = m["city"]
                    break

    # Get all unique cities and teams for filters
    all_cities = sorted(set(m["city"] for m in matches if m["city"]))
    all_teams = sorted(set(m["team1"] for m in matches) | set(m["team2"] for m in matches))

    data = {
        "match_history": match_history,
        "venue_volume": venue_volume,
        "max_volume": max_vol,
        "best_venue": best_venue,
        "best_avg": round(best_avg, 1),
        "best_city": best_city,
        "all_cities": all_cities,
        "all_teams": all_teams,
    }
    logger.info(
        "Match analytics prepared: matches=%s cities=%s teams=%s best_venue=%s",
        len(match_history),
        len(all_cities),
        len(all_teams),
        best_venue or "n/a",
    )
    return data


def transform_batters():
    """Compute Batter Performance analytics."""
    batting = get_batting()

    # Aggregate batter stats across all matches
    batter_agg = defaultdict(lambda: {
        "runs": 0, "balls_faced": 0, "innings": 0, "fours": 0, "sixes": 0,
        "team": "", "boundary_runs": 0
    })

    for b in batting:
        key = b["batter"]
        runs = int(b["runs"] or 0)
        balls = int(b["balls_faced"] or 0)
        fours = int(b["fours"] or 0)
        sixes = int(b["sixes"] or 0)

        batter_agg[key]["runs"] += runs
        batter_agg[key]["balls_faced"] += balls
        batter_agg[key]["innings"] += 1
        batter_agg[key]["fours"] += fours
        batter_agg[key]["sixes"] += sixes
        batter_agg[key]["team"] = b["team"]
        batter_agg[key]["boundary_runs"] += (fours * 4) + (sixes * 6)

    # Build leaderboard sorted by runs
    leaderboard = []
    for batter, stats in batter_agg.items():
        sr = round((stats["runs"] / stats["balls_faced"]) * 100, 1) if stats["balls_faced"] > 0 else 0
        rpb = round(stats["runs"] / stats["balls_faced"], 2) if stats["balls_faced"] > 0 else 0
        leaderboard.append({
            "batter": batter,
            "team": stats["team"],
            "runs": stats["runs"],
            "innings": stats["innings"],
            "balls_faced": stats["balls_faced"],
            "fours": stats["fours"],
            "sixes": stats["sixes"],
            "strike_rate": sr,
            "rpb": rpb,
            "boundary_runs": stats["boundary_runs"],
            "running_runs": stats["runs"] - stats["boundary_runs"],
        })

    leaderboard.sort(key=lambda x: x["runs"], reverse=True)

    # Top 20 for display
    top_batters = leaderboard[:20]

    # Scoring intensity
    if top_batters:
        max_sr = max(b["strike_rate"] for b in top_batters)
    else:
        max_sr = 100

    # Tournament avg RPB
    total_runs = sum(b["runs"] for b in leaderboard)
    total_balls = sum(b["balls_faced"] for b in leaderboard)
    tournament_avg_rpb = round(total_runs / total_balls, 2) if total_balls > 0 else 0

    # Aggressive / Balanced counts
    aggressive = sum(1 for b in top_batters if b["rpb"] > 1.2)
    balanced = sum(1 for b in top_batters if 0.8 <= b["rpb"] <= 1.2)

    # Top intensity batter
    top_intensity = max(top_batters, key=lambda x: x["rpb"]) if top_batters else None

    data = {
        "leaderboard": top_batters,
        "max_sr": max_sr,
        "tournament_avg_rpb": tournament_avg_rpb,
        "aggressive_count": aggressive,
        "balanced_count": balanced,
        "total_batters": len(top_batters),
        "top_intensity": top_intensity,
    }
    logger.info(
        "Batter analytics prepared: batters=%s avg_rpb=%s top_batter=%s",
        len(top_batters),
        tournament_avg_rpb,
        top_intensity["batter"] if top_intensity else "n/a",
    )
    return data


def transform_teams():
    """Compute Team Insights (bowling & team) analytics."""
    bowling = get_bowling()
    # Aggregate bowler stats
    bowler_agg = defaultdict(lambda: {
        "deliveries": 0, "legal_deliveries": 0, "runs_conceded": 0,
        "wickets": 0, "team": ""
    })

    for b in bowling:
        key = b["bowler"]
        bowler_agg[key]["deliveries"] += int(b["deliveries"] or 0)
        bowler_agg[key]["legal_deliveries"] += int(b["legal_deliveries"] or 0)
        bowler_agg[key]["runs_conceded"] += int(b["runs_conceded"] or 0)
        bowler_agg[key]["wickets"] += int(b["wickets"] or 0)
        bowler_agg[key]["team"] = b["team"]

    # Elite economy bowlers (min 100 legal deliveries)
    elite_bowlers = []
    for bowler, stats in bowler_agg.items():
        if stats["legal_deliveries"] >= 100:
            economy = round((stats["runs_conceded"] / (stats["legal_deliveries"] / 6)), 2) if stats["legal_deliveries"] > 0 else 0
            elite_bowlers.append({
                "bowler": bowler,
                "team": stats["team"],
                "deliveries": stats["legal_deliveries"],
                "runs_total": stats["runs_conceded"],
                "wickets": stats["wickets"],
                "economy": economy,
            })
    elite_bowlers.sort(key=lambda x: x["economy"])
    top_elite = elite_bowlers[:10]

    # Avg runs conceded per match per team (bowling team)
    team_runs_conceded = defaultdict(lambda: {"total_conceded": 0, "matches": set()})
    for b in bowling:
        team = b["team"]
        mid = b["match_id"]
        team_runs_conceded[team]["total_conceded"] += int(b["runs_conceded"] or 0)
        team_runs_conceded[team]["matches"].add(mid)

    avg_conceded = []
    for team, data in team_runs_conceded.items():
        num_matches = len(data["matches"])
        avg = round(data["total_conceded"] / num_matches, 1) if num_matches > 0 else 0
        avg_conceded.append({"team": team, "avg": avg, "matches": num_matches})

    avg_conceded.sort(key=lambda x: x["avg"])
    max_avg_conceded = max(a["avg"] for a in avg_conceded) if avg_conceded else 1

    # Crucial metric: teams with economy under 4.20 win %
    team_econ = defaultdict(lambda: {"total_deliveries": 0, "total_runs": 0})
    for b in bowling:
        team = b["team"]
        team_econ[team]["total_deliveries"] += int(b["legal_deliveries"] or 0)
        team_econ[team]["total_runs"] += int(b["runs_conceded"] or 0)

    low_econ_teams = []
    team_economies = []
    for team, data in team_econ.items():
        if data["total_deliveries"] > 0:
            econ = (data["total_runs"] / (data["total_deliveries"] / 6))
            team_economies.append({"team": team, "economy": round(econ, 2), "deliveries": data["total_deliveries"], "runs": data["total_runs"]})
            if econ < 4.20:
                low_econ_teams.append(team)

    team_economies.sort(key=lambda x: x["economy"])
    closest_low_economy_teams = team_economies[:5]
    best_economy_team = team_economies[0] if team_economies else None

    data = {
        "elite_bowlers": top_elite,
        "avg_conceded": avg_conceded,
        "max_avg_conceded": max_avg_conceded,
        "low_econ_teams": low_econ_teams,
        "closest_low_economy_teams": closest_low_economy_teams,
        "best_economy_team": best_economy_team,
    }
    logger.info(
        "Team analytics prepared: elite_bowlers=%s low_econ_teams=%s",
        len(top_elite),
        len(low_econ_teams),
    )
    return data


@app.template_filter("team_abbr")
def team_abbr(name):
    """Return short 3-letter abbreviation for a team label."""
    if not name:
        return "---"
    words = [w for w in name.split() if w]
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0].upper() for w in words)[:3]


# ─── Routes ───

@app.route("/")
def overview():
    data = transform_overview()
    return render_template("overview.html", data=data, active_page="overview")


@app.route("/matches")
def matches_page():
    city_filter = request.args.get("city", "All Cities")
    team_filter = request.args.get("team", "All Teams")
    data = transform_matches(city_filter, team_filter)
    return render_template("matches.html", data=data, active_page="matches",
                           selected_city=city_filter, selected_team=team_filter)


@app.route("/batters")
def batters_page():
    data = transform_batters()
    return render_template("batters.html", data=data, active_page="batters")


@app.route("/teams")
def teams_page():
    data = transform_teams()
    return render_template("teams.html", data=data, active_page="teams")


@app.route("/live")
def live_match_center():
    return matches_page()


@app.route("/settings")
def settings_page():
    return render_template(
        "info.html",
        title="Settings",
        subtitle="Configure your analytics workspace preferences.",
        message="Settings are available for presentation mode, default filters, and export behavior.",
        active_page="settings",
    )


@app.route("/support")
def support_page():
    return render_template(
        "info.html",
        title="Support",
        subtitle="Need help with this analytics suite?",
        message="Use the API endpoints or the CSV outputs for debugging and integrations.",
        active_page="support",
    )


# ─── API Endpoints ───

@app.route("/api/overview")
def api_overview():
    return jsonify(transform_overview())


@app.route("/api/matches")
def api_matches():
    city = request.args.get("city", "All Cities")
    team = request.args.get("team", "All Teams")
    return jsonify(transform_matches(city, team))


@app.route("/api/batters")
def api_batters():
    return jsonify(transform_batters())


@app.route("/api/teams")
def api_teams():
    return jsonify(transform_teams())


if __name__ == "__main__":
    logger.info("Starting dashboard bootstrap")
    ensure_csv_data()
    logger.info("Starting Flask development server on 0.0.0.0:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
