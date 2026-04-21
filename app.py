"""
app.py
Flask Web Application for Women's Cricket World Cup Analytics Dashboard.
Loads transformed CSV data and serves the analytics dashboard.
"""
from functools import lru_cache
from collections import defaultdict, Counter
import os
import time
import json
import re
from glob import glob
from datetime import datetime
from collections import defaultdict, Counter
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from dotenv import load_dotenv
<<<<<<< HEAD
from flask import Flask, render_template, jsonify, request, g, session, redirect, url_for
from etl_pipeline import run_pipeline
=======
from flask import Flask, render_template, jsonify, request, g
from Appwrite.appwrite_db import get_matches as appwrite_get_matches
from Appwrite.appwrite_db import get_batting as appwrite_get_batting
from Appwrite.appwrite_db import get_bowling as appwrite_get_bowling
>>>>>>> origin
from logging_config import configure_logging, get_log_file_path

# Import our new modular extensions
from extensions import db, oauth
from auth import auth_bp, admin_required

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_for_dev_change_me")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///users.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize modular plugins
db.init_app(app)
oauth.init_app(app)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={'scope': 'openid email profile'}
)

app.register_blueprint(auth_bp)

logger = configure_logging(__name__)

LOG_FILE_PATH = get_log_file_path()

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y")
LOG_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")
APP_NAME = os.getenv("APP_NAME", "BoundaryLine Intelligence")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
CHAT_DECLINE_MESSAGE = "I can only answer cricket questions using this dashboard dataset."
LOG_LINE_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

CORE_CRICKET_KEYWORDS = {
    "cricket", "match", "matches", "innings", "inning", "run", "runs", "wicket", "wickets",
    "bat", "batter", "batters", "batting", "bowl", "bowler", "bowlers", "bowling",
    "economy", "strike", "rate", "rpb", "over", "overs", "team", "teams", "venue",
    "city", "winner", "won", "lost", "score", "scores", "tournament", "world", "cup",
    "final", "semi", "group", "powerplay", "boundary", "boundaries", "fours", "sixes",
}

_chat_base_context = None
_cricket_lexicon = None


@app.context_processor
def inject_global_template_vars():
    """Expose global branding variables to all templates."""
    return {"APP_NAME": APP_NAME}


def get_matches():
    """Return match-level rows from Appwrite source."""
    return appwrite_get_matches()


def get_batting():
    """Return batting rows from Appwrite source."""
    return appwrite_get_batting()


def get_bowling():
    """Return bowling rows from Appwrite source."""
    return appwrite_get_bowling()


def parse_match_date(value):
    """Parse supported date formats and return a sortable datetime."""
    if not value:
        return datetime.min

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_log_filter_datetime(value, *, end_of_day=False):
    """Parse date/datetime filters accepted by /api/logs endpoint."""
    if not value:
        return None

    raw = value.strip()
    for fmt in LOG_DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d" and end_of_day:
                parsed = parsed.replace(hour=23, minute=59, second=59)
            return parsed
        except ValueError:
            continue

    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def parse_log_line(raw_line):
    """Parse one formatted log line into a structured entry."""
    parts = raw_line.rstrip("\n").split(" | ", 3)
    if len(parts) != 4:
        return None

    timestamp_str, level, logger_name, message = parts
    try:
        timestamp = datetime.strptime(timestamp_str, LOG_LINE_TIMESTAMP_FORMAT)
    except ValueError:
        return None

    return {
        "timestamp": timestamp_str,
        "level": level,
        "logger": logger_name,
        "message": message,
        "_dt": timestamp,
    }


def get_log_file_candidates(include_archived=False):
    """Return log files to search, oldest to newest."""
    if include_archived:
        pattern = f"{LOG_FILE_PATH}*"
        candidates = [path for path in glob(pattern) if os.path.isfile(path)]
    else:
        candidates = [LOG_FILE_PATH] if os.path.isfile(LOG_FILE_PATH) else []

    candidates.sort(key=lambda path: os.path.getmtime(path))
    return candidates


def query_log_entries(limit=200, level=None, query=None, since=None, until=None, include_archived=False):
    """Read and filter log entries from one or many log files."""
    search_text = (query or "").strip().lower()
    target_level = level.upper() if level else ""
    matching = []

    source_files = get_log_file_candidates(include_archived=include_archived)
    for path in source_files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    parsed = parse_log_line(raw)
                    if parsed is None:
                        continue

                    if target_level and parsed["level"] != target_level:
                        continue
                    if since and parsed["_dt"] < since:
                        continue
                    if until and parsed["_dt"] > until:
                        continue
                    if search_text:
                        haystack = f"{parsed['logger']} {parsed['message']} {parsed['level']}".lower()
                        if search_text not in haystack:
                            continue

                    parsed.pop("_dt", None)
                    matching.append(parsed)
        except OSError:
            continue

    if limit > 0:
        matching = matching[-limit:]

    return matching, source_files


def get_cricket_lexicon():
    """Build a token lexicon from dataset entities for lightweight topical checks."""
    global _cricket_lexicon
    if _cricket_lexicon is not None:
        return _cricket_lexicon

    lexicon = set(CORE_CRICKET_KEYWORDS)

    for match in get_matches():
        combined = " ".join(
            [
                match.get("team1", ""),
                match.get("team2", ""),
                match.get("venue", ""),
                match.get("city", ""),
                match.get("event_stage", ""),
                match.get("winner", ""),
            ]
        ).lower()
        lexicon.update(token for token in re.findall(r"[a-z0-9]+", combined) if len(token) > 2)

    for row in get_batting():
        combined = f"{row.get('batter', '')} {row.get('team', '')}".lower()
        lexicon.update(token for token in re.findall(r"[a-z0-9]+", combined) if len(token) > 2)

    for row in get_bowling():
        combined = f"{row.get('bowler', '')} {row.get('team', '')}".lower()
        lexicon.update(token for token in re.findall(r"[a-z0-9]+", combined) if len(token) > 2)

    _cricket_lexicon = lexicon
    return _cricket_lexicon


def is_cricket_query(question):
    """Allow only likely cricket/domain questions for the chatbot."""
    if not question:
        return False

    tokens = {token for token in re.findall(r"[a-z0-9]+", question.lower()) if len(token) > 2}
    if not tokens:
        return False

    return bool(tokens & get_cricket_lexicon())


def build_chat_base_context():
    """Build a compact, authoritative context block from dashboard data."""
    global _chat_base_context
    if _chat_base_context is not None:
        return _chat_base_context

    overview = transform_overview()
    batters = transform_batters()
    teams = transform_teams()

    lines = [
        "DATASET_SCOPE: Women's Cricket World Cup analytics sourced only from Appwrite database collections.",
        f"TOTAL_MATCHES: {overview['total_matches']}",
        f"TOTAL_RUNS: {overview['total_runs']}",
        f"TEAM_COUNT: {overview['team_count']}",
        f"VENUE_COUNT: {overview['venue_count']}",
        f"CITY_COUNT: {overview['city_count']}",
        "TOP_WINNING_TEAMS:",
    ]

    for team, wins in overview["top_winners"][:8]:
        lines.append(f"- {team}: {wins} wins")

    lines.append("TOP_BATTERS_BY_RUNS:")
    for batter in batters["leaderboard"][:10]:
        lines.append(
            f"- {batter['batter']} ({batter['team']}): runs={batter['runs']}, SR={batter['strike_rate']}, innings={batter['innings']}"
        )

    lines.append("TOP_ECONOMY_BOWLERS:")
    for bowler in teams["elite_bowlers"][:10]:
        lines.append(
            f"- {bowler['bowler']} ({bowler['team']}): economy={bowler['economy']}, wickets={bowler['wickets']}, deliveries={bowler['deliveries']}"
        )

    _chat_base_context = "\n".join(lines)
    return _chat_base_context


def build_chat_query_context(question):
    """Add query-relevant slices from matches/batting/bowling to the base context."""
    terms = [t for t in re.findall(r"[a-z0-9]+", question.lower()) if len(t) > 2]

    def has_term(text):
        lowered = (text or "").lower()
        return any(term in lowered for term in terms)

    matches_sorted = sorted(
        get_matches(),
        key=lambda row: (parse_match_date(row.get("date")), row.get("match_id", "")),
        reverse=True,
    )

    relevant_matches = []
    for match in matches_sorted:
        blob = " ".join(
            [
                match.get("date", ""),
                match.get("team1", ""),
                match.get("team2", ""),
                match.get("venue", ""),
                match.get("city", ""),
                match.get("event_stage", ""),
                match.get("winner", ""),
            ]
        )
        if terms and not has_term(blob):
            continue

        result_text = match.get("winner") or "No result"
        if match.get("winner") and match.get("win_margin") and match.get("win_by"):
            result_text = f"{match['winner']} won by {match['win_margin']} {match['win_by']}"

        relevant_matches.append(
            f"- {match.get('date', '')}: {match.get('team1', '')} vs {match.get('team2', '')} | {result_text} | {match.get('venue', '')}, {match.get('city', '')}"
        )
        if len(relevant_matches) >= 12:
            break

    if not relevant_matches:
        for match in matches_sorted[:8]:
            relevant_matches.append(
                f"- {match.get('date', '')}: {match.get('team1', '')} vs {match.get('team2', '')} | winner={match.get('winner', '') or 'No result'}"
            )

    batter_totals = defaultdict(lambda: {"runs": 0, "team": ""})
    for row in get_batting():
        name = row.get("batter", "")
        if not name:
            continue
        batter_totals[name]["runs"] += safe_int(row.get("runs"))
        batter_totals[name]["team"] = row.get("team", batter_totals[name]["team"])

    batter_rows = []
    for name, stats in batter_totals.items():
        blob = f"{name} {stats['team']}"
        if terms and not has_term(blob):
            continue
        batter_rows.append((name, stats["team"], stats["runs"]))
    batter_rows.sort(key=lambda row: row[2], reverse=True)

    bowler_totals = defaultdict(lambda: {"runs": 0, "balls": 0, "team": ""})
    for row in get_bowling():
        name = row.get("bowler", "")
        if not name:
            continue
        bowler_totals[name]["runs"] += safe_int(row.get("runs_conceded"))
        bowler_totals[name]["balls"] += safe_int(row.get("legal_deliveries"))
        bowler_totals[name]["team"] = row.get("team", bowler_totals[name]["team"])

    bowler_rows = []
    for name, stats in bowler_totals.items():
        if stats["balls"] <= 0:
            continue
        blob = f"{name} {stats['team']}"
        if terms and not has_term(blob):
            continue
        economy = round(stats["runs"] / (stats["balls"] / 6), 2)
        bowler_rows.append((name, stats["team"], economy))
    bowler_rows.sort(key=lambda row: row[2])

    chunks = [build_chat_base_context(), "", "QUERY_RELEVANT_MATCHES:"]
    chunks.extend(relevant_matches[:12])

    if batter_rows:
        chunks.append("QUERY_RELEVANT_BATTERS:")
        for name, team, runs in batter_rows[:8]:
            chunks.append(f"- {name} ({team}): runs={runs}")

    if bowler_rows:
        chunks.append("QUERY_RELEVANT_BOWLERS:")
        for name, team, economy in bowler_rows[:8]:
            chunks.append(f"- {name} ({team}): economy={economy}")

    return "\n".join(chunks)


def call_gemini_chat(message, history, context_block, api_key):
    """Call Gemini REST API with strict policy instructions."""
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={quote_plus(api_key)}"
    )

    system_prompt = (
        "You are the Kinetic Cricket Assistant for this dashboard. "
        "Strict rules: (1) Answer only cricket-related questions. "
        "(2) Use only facts from DATA_CONTEXT supplied in the final user turn; do not use external knowledge. "
        f"(3) If the question is outside cricket OR not answerable from DATA_CONTEXT, reply exactly: '{CHAT_DECLINE_MESSAGE}'. "
        "(4) Keep answers concise and numeric when possible."
    )

    contents = []
    for turn in history[-6:]:
        role = turn.get("role", "user")
        text = str(turn.get("content", "")).strip()
        if not text:
            continue
        contents.append({
            "role": "model" if role == "assistant" else "user",
            "parts": [{"text": text[:900]}],
        })

    prompt = (
        f"DATA_CONTEXT:\n{context_block}\n\n"
        f"USER_QUESTION:\n{message}\n\n"
        f"If the answer is not in DATA_CONTEXT, respond exactly with: {CHAT_DECLINE_MESSAGE}"
    )
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.1,
            "topK": 32,
            "topP": 0.9,
            "maxOutputTokens": 320,
        },
    }

    try:
        req = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=35) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        logger.warning("Gemini HTTP error %s: %s", exc.code, body[:500])
        return "The assistant is temporarily unavailable. Please try again."
    except URLError as exc:
        logger.warning("Gemini URL error: %s", exc)
        return "The assistant is temporarily unavailable. Please try again."
    except Exception as exc:
        logger.exception("Gemini call failed: %s", exc)
        return "The assistant is temporarily unavailable. Please try again."

    candidates = response_payload.get("candidates") or []
    if not candidates:
        return CHAT_DECLINE_MESSAGE

    parts = candidates[0].get("content", {}).get("parts", [])
    reply = " ".join(part.get("text", "").strip() for part in parts if part.get("text")).strip()
    return reply or CHAT_DECLINE_MESSAGE


# ─── Transform Functions ───
@lru_cache(maxsize=1)
def transform_overview():
    matches = get_matches()
    batting = get_batting()

    total_matches = len(matches)

    # ✅ O(N) instead of O(N²)
    runs_by_match = defaultdict(int)
    for b in batting:
        runs_by_match[b.get("match_id")] += safe_int(b.get("runs"))

    total_runs = sum(runs_by_match.values())

    teams = set()
    for m in matches:
        teams.add(m.get("team1"))
        teams.add(m.get("team2"))

    venues = {m.get("venue") for m in matches if m.get("venue")}
    cities = {m.get("city") for m in matches if m.get("city")}

    win_counts = Counter(m.get("winner") for m in matches if m.get("winner"))
    top_winners = win_counts.most_common(10)

    city_counts = Counter(m.get("city") for m in matches if m.get("city"))
    top_city = city_counts.most_common(1)[0] if city_counts else ("", 0)

    runs_per_match = [
        {
            "match_id": m.get("match_id"),
            "date": m.get("date"),
            "total_runs": runs_by_match[m.get("match_id")],
            "team1": m.get("team1"),
            "team2": m.get("team2"),
        }
        for m in matches
    ]

    max_wins = top_winners[0][1] if top_winners else 0
    
    return {
    "total_matches": total_matches,
    "total_runs": total_runs,
    "teams": sorted(list(teams)),
    "team_count": len(teams),
    "venue_count": len(venues),
    "city_count": len(cities),
    "top_winners": top_winners,
    "runs_per_match": runs_per_match,
    "top_city": top_city,
    "max_wins": max_wins,

    # ALWAYS include all keys expected by UI
    }  


@app.before_request
def global_auth_lockdown():
    """Firewall: ensure all routes are protected unless explicitly exempted."""
    allowed_endpoints = ['auth.login', 'auth.auth_callback', 'public_login_page', 'static']
    if request.endpoint not in allowed_endpoints:
        if 'user_id' not in session:
            # For API routes, return 401 instead of redirecting
            if request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for('public_login_page'))
    
    # Load user into global 'g' for templates if logged in
    if 'user_id' in session:
        from models import User
        g.user = db.session.get(User, session['user_id'])
    else:
        g.user = None

@app.before_request
def log_request_start():
    g.request_start = time.perf_counter()
    logger.info("Request started %s %s", request.method, request.path)


@app.after_request
def log_request_end(response):
    start_time = getattr(g, "request_start", None)
    if start_time is not None:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Request completed %s %s -> %s in %.1fms",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
    return response


@app.errorhandler(404)
def handle_not_found(error):
    logger.warning("Not found: %s %s", request.method, request.path)
    return render_template("info.html", title="Not Found", subtitle="The requested page does not exist.", message="Check the URL and try again.", active_page=""), 404


@app.errorhandler(500)
def handle_server_error(error):
    logger.exception("Unhandled server error on %s %s", request.method, request.path)
    return render_template("info.html", title="Server Error", subtitle="An unexpected error occurred.", message="Please try again or check the application logs.", active_page=""), 500


def transform_matches(city_filter=None, team_filter=None):
    matches = get_matches()
    batting = get_batting()

    # ── pre-build runs lookup (O(N), not O(N²)) ──────────────────────────
    runs_by_match = defaultdict(int)
    for b in batting:
        runs_by_match[b.get("match_id", "")] += safe_int(b.get("runs"))

    # ── filter ───────────────────────────────────────────────────────────
    filtered = matches
    if city_filter and city_filter != "All Cities":
        filtered = [m for m in filtered if m.get("city") == city_filter]
    if team_filter and team_filter != "All Teams":
        filtered = [m for m in filtered if m.get("team1") == team_filter or m.get("team2") == team_filter]

    filtered_sorted = sorted(
        filtered,
        key=lambda x: (parse_match_date(x.get("date")), x.get("match_id", "")),
        reverse=True,
    )

    match_history = []
    for idx, m in enumerate(filtered_sorted):
        match_history.append({
            "display_id": f"#M-{1000 + len(filtered_sorted) - idx}",
            "match_id":   m.get("match_id", ""),        # ← .get() not []
            "date":       m.get("date", ""),
            "team1":      m.get("team1", ""),
            "team2":      m.get("team2", ""),
            "venue":      m.get("venue", ""),
            "city":       m.get("city", ""),
            "winner":     m.get("winner", ""),
        })

    # ── venue volume ─────────────────────────────────────────────────────
    city_counts = Counter(m.get("city") for m in matches if m.get("city"))
    venue_volume = city_counts.most_common(10)
    max_vol = venue_volume[0][1] if venue_volume else 1

    # ── best venue by avg score (O(N) now) ───────────────────────────────
    venue_scores  = defaultdict(list)
    venue_to_city = {}
    for m in matches:
        v = m.get("venue")
        if v:
            venue_scores[v].append(runs_by_match[m.get("match_id", "")])
            venue_to_city.setdefault(v, m.get("city", ""))

    best_venue, best_avg, best_city = "", 0, ""
    for venue, scores in venue_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        if avg > best_avg:
            best_avg, best_venue, best_city = avg, venue, venue_to_city[venue]

    all_cities = sorted({m.get("city") for m in matches if m.get("city")})
    all_teams  = sorted({m.get("team1") for m in matches} | {m.get("team2") for m in matches} - {None, ""})

    return {
        "match_history": match_history,
        "venue_volume":  venue_volume,
        "max_volume":    max_vol,
        "best_venue":    best_venue,
        "best_avg":      round(best_avg, 1),
        "best_city":     best_city,
        "all_cities":    all_cities,
        "all_teams":     all_teams,
    }

@lru_cache(maxsize=1)
def transform_batters():
    batting = get_batting()

    agg = defaultdict(lambda: {
        "runs": 0,
        "balls": 0,
        "innings_set": set(),
        "fours": 0,
        "sixes": 0,
        "team": ""
    })

    for b in batting:
        name = b.get("batter")
        if not name:
            continue

        runs = safe_int(b.get("runs"))
        balls = safe_int(b.get("balls_faced"))

        agg[name]["runs"] += runs
        agg[name]["balls"] += balls
        agg[name]["fours"] += safe_int(b.get("fours"))
        agg[name]["sixes"] += safe_int(b.get("sixes"))
        agg[name]["team"] = b.get("team")

        # ✅ FIXED innings count
        agg[name]["innings_set"].add((b.get("match_id"), b.get("innings")))

    leaderboard = []
    for k, v in agg.items():
        balls = v["balls"]
        sr = (v["runs"] / balls * 100) if balls else 0
        rpb = (v["runs"] / balls) if balls else 0
        boundary_runs = (v["fours"] * 4) + (v["sixes"] * 6)

        leaderboard.append({
            "batter": k,
            "team": v["team"],
            "runs": v["runs"],
            "strike_rate": round(sr, 1),
            "innings": len(v["innings_set"]),
            "boundary_runs": boundary_runs,
            "rpb": round(rpb, 2),
        })

    leaderboard.sort(key=lambda x: x["runs"], reverse=True)

    # Calculate metrics for Scoring Intensity and Player Distribution
    top_intensity = max(leaderboard, key=lambda x: x["rpb"]) if leaderboard else None
    
    aggressive_count = sum(1 for b in leaderboard if b["rpb"] > 1.2)
    balanced_count = sum(1 for b in leaderboard if 0.8 <= b["rpb"] <= 1.2)
    
    total_rpb = sum(b["rpb"] for b in leaderboard)
    tournament_avg_rpb = round(total_rpb / len(leaderboard), 2) if leaderboard else 0

    return {
        "leaderboard": leaderboard[:20],
        "top_intensity": top_intensity,
        "aggressive_count": aggressive_count,
        "balanced_count": balanced_count,
        "tournament_avg_rpb": tournament_avg_rpb,
        "total_batters": len(leaderboard)
    }

@lru_cache(maxsize=1)
def transform_teams():
    bowling = get_bowling()
    matches = get_matches()

    # ── per-bowler aggregation (for elite_bowlers) ────────────────────────
    bowler_agg = defaultdict(lambda: {"balls": 0, "runs": 0, "wickets": 0, "team": ""})
    for b in bowling:
        name = b.get("bowler")
        if not name:
            continue
        bowler_agg[name]["balls"]   += safe_int(b.get("legal_deliveries"))
        bowler_agg[name]["runs"]    += safe_int(b.get("runs_conceded"))
        bowler_agg[name]["wickets"] += safe_int(b.get("wickets"))
        bowler_agg[name]["team"]     = b.get("team") or bowler_agg[name]["team"]

    bowlers = []
    for k, v in bowler_agg.items():
        if v["balls"] < 30:          # lowered from 100 — less aggressive filter
            continue
        economy = v["runs"] / (v["balls"] / 6)
        bowlers.append({
            "bowler":     k,
            "team":       v["team"],
            "economy":    round(economy, 2),
            "wickets":    v["wickets"],
            "deliveries": v["balls"],   # ← fixes the chat KeyError from earlier
        })
    bowlers.sort(key=lambda x: x["economy"])

    # ── per-team avg runs conceded per match (for avg_conceded) ───────────
    team_match_ids  = defaultdict(set)
    team_runs_given = defaultdict(int)

    for b in bowling:
        team = b.get("team")
        mid  = b.get("match_id")
        if not team or not mid:
            continue
        team_runs_given[team] += safe_int(b.get("runs_conceded"))
        team_match_ids[team].add(mid)

    avg_conceded = []
    for team, match_ids in team_match_ids.items():
        n = len(match_ids)
        avg_conceded.append({
            "team":          team,
            "avg":           round(team_runs_given[team] / n, 1) if n else 0,
            "matches":       n,
            "total_conceded": team_runs_given[team],
        })
    avg_conceded.sort(key=lambda x: x["avg"])

    max_avg_conceded = max([x["avg"] for x in avg_conceded], default=1)

    return {
        "elite_bowlers": bowlers[:10],
        "avg_conceded":  avg_conceded,   # ← what teams.html needs
        "max_avg_conceded": max_avg_conceded,
    }


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

@app.route("/login-page")
def public_login_page():
    if 'user_id' in session:
        return redirect(url_for('overview'))
    return render_template("login.html")

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
@admin_required
def settings_page():
    return render_template(
        "info.html",
        title="Settings",
        subtitle="Configure your analytics workspace preferences.",
        message="Settings are available for presentation mode, default filters, and export behavior.",
        active_page="settings",
    )


@app.route("/support")
@admin_required
def support_page():
    return render_template(
        "info.html",
        title="Support",
        subtitle="Need help with this analytics suite?",
        message="Use the API endpoints or Appwrite collections for debugging and integrations.",
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


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    if not isinstance(history, list):
        history = []

    if not message:
        return jsonify({"error": "Message is required."}), 400

    if len(message) > 1200:
        message = message[:1200]

    if not is_cricket_query(message):
        return jsonify({"reply": CHAT_DECLINE_MESSAGE})

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify(
            {
                "reply": (
                    "Gemini API key is not configured yet. "
                    "Set GEMINI_API_KEY in your environment, then ask a cricket question again."
                )
            }
        )

    context_block = build_chat_query_context(message)
    reply = call_gemini_chat(message=message, history=history, context_block=context_block, api_key=api_key)

    if not reply:
        reply = CHAT_DECLINE_MESSAGE

    return jsonify({"reply": reply})


@app.route("/api/logs")
@admin_required
def api_logs():
    level = request.args.get("level", "").strip().upper()
    if level and level not in VALID_LOG_LEVELS:
        return jsonify({"error": f"Invalid level. Use one of: {', '.join(sorted(VALID_LOG_LEVELS))}"}), 400

    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        return jsonify({"error": "Invalid limit. Provide an integer between 1 and 2000."}), 400

    limit = max(1, min(limit, 2000))
    query = request.args.get("q", "").strip()
    since_raw = request.args.get("since", "").strip()
    until_raw = request.args.get("until", "").strip()
    include_archived = request.args.get("include_archived", "false").strip().lower() in {"1", "true", "yes"}

    since = parse_log_filter_datetime(since_raw)
    until = parse_log_filter_datetime(until_raw, end_of_day=True)

    if since_raw and since is None:
        return jsonify({"error": "Invalid since value. Use YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, or ISO datetime."}), 400
    if until_raw and until is None:
        return jsonify({"error": "Invalid until value. Use YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, or ISO datetime."}), 400
    if since and until and since > until:
        return jsonify({"error": "Invalid range. 'since' must be earlier than or equal to 'until'."}), 400

    entries, source_files = query_log_entries(
        limit=limit,
        level=level,
        query=query,
        since=since,
        until=until,
        include_archived=include_archived,
    )

    return jsonify(
        {
            "log_file": LOG_FILE_PATH,
            "source_files": source_files,
            "filters": {
                "level": level or None,
                "q": query or None,
                "since": since_raw or None,
                "until": until_raw or None,
                "limit": limit,
                "include_archived": include_archived,
            },
            "returned": len(entries),
            "entries": entries,
        }
    )

def safe_int(value):
    try:
        return int(value)
    except:
        return 0
    
if __name__ == "__main__":
    logger.info("Starting dashboard bootstrap")
<<<<<<< HEAD
    with app.app_context():
        db.create_all()
    ensure_csv_data()
=======
>>>>>>> origin
    logger.info("Starting Flask development server on 0.0.0.0:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
