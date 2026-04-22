"""
ELT Pipeline: Extract cricket match data from JSON files, Load into CSV files.
Parses Cricsheet JSON format (v1.0.0 and v1.1.0) for ICC Women's Cricket World Cup data.
"""

import json
import csv
import os
import glob
from collections import defaultdict

from Logger.logging_config import configure_logging


DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv_data")
logger = configure_logging(__name__)


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_match_info(match_id, data):
    """Extract match-level information from JSON data."""
    info = data.get("info", {})
    outcome = info.get("outcome", {})

    winner = outcome.get("winner", "")
    win_by = ""
    win_margin = ""
    if "by" in outcome:
        by = outcome["by"]
        if "runs" in by:
            win_by = "runs"
            win_margin = by["runs"]
        elif "wickets" in by:
            win_by = "wickets"
            win_margin = by["wickets"]

    # Handle no result / tie
    if not winner:
        if "result" in outcome:
            winner = outcome["result"]  # e.g., "no result", "tie"

    teams = info.get("teams", [])
    team1 = teams[0] if len(teams) > 0 else ""
    team2 = teams[1] if len(teams) > 1 else ""

    dates = info.get("dates", [])
    date = dates[0] if dates else ""

    event = info.get("event", {})
    event_name = event.get("name", "")
    event_stage = event.get("stage", "")

    toss = info.get("toss", {})

    player_of_match = info.get("player_of_match", [])
    pom = player_of_match[0] if player_of_match else ""

    return {
        "match_id": match_id,
        "date": date,
        "city": info.get("city", ""),
        "venue": info.get("venue", ""),
        "team1": team1,
        "team2": team2,
        "winner": winner,
        "win_by": win_by,
        "win_margin": win_margin,
        "event_name": event_name,
        "event_stage": event_stage,
        "match_type": info.get("match_type", ""),
        "gender": info.get("gender", ""),
        "toss_winner": toss.get("winner", ""),
        "toss_decision": toss.get("decision", ""),
        "player_of_match": pom,
        "season": info.get("season", ""),
        "overs": info.get("overs", ""),
    }


def parse_innings_data(match_id, data):
    """Extract ball-by-ball, batting, and bowling data from innings."""
    innings_list = data.get("innings", [])
    deliveries_rows = []
    batting_stats = defaultdict(lambda: {
        "runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0,
        "is_out": 0, "dismissal_kind": "", "team": ""
    })
    bowling_stats = defaultdict(lambda: {
        "deliveries": 0, "runs_conceded": 0, "wickets": 0,
        "extras_given": 0, "team": "", "legal_deliveries": 0
    })

    info = data.get("info", {})
    teams = info.get("teams", [])
    players_by_team = info.get("players", {})

    # Build player-to-team mapping
    player_team_map = {}
    for team_name, player_list in players_by_team.items():
        for player in player_list:
            player_team_map[player] = team_name

    for inning_idx, inning in enumerate(innings_list):
        innings_num = inning_idx + 1
        batting_team = inning.get("team", "")

        # Determine bowling team
        bowling_team = ""
        for t in teams:
            if t != batting_team:
                bowling_team = t
                break

        overs = inning.get("overs", [])
        for over_data in overs:
            over_num = over_data.get("over", 0)
            deliveries = over_data.get("deliveries", [])

            ball_num = 0
            for delivery in deliveries:
                ball_num += 1
                batter = delivery.get("batter", "")
                bowler = delivery.get("bowler", "")
                non_striker = delivery.get("non_striker", "")
                runs = delivery.get("runs", {})
                batter_runs = runs.get("batter", 0)
                extras_total = runs.get("extras", 0)
                total_runs = runs.get("total", 0)

                extras_detail = delivery.get("extras", {})
                is_wide = "wides" in extras_detail
                is_noball = "noballs" in extras_detail

                # Wicket info
                wicket_type = ""
                player_dismissed = ""
                wickets = delivery.get("wickets", [])
                if wickets:
                    w = wickets[0]
                    wicket_type = w.get("kind", "")
                    player_dismissed = w.get("player_out", "")

                # Deliveries CSV row
                deliveries_rows.append({
                    "match_id": match_id,
                    "innings": innings_num,
                    "over": over_num,
                    "ball": ball_num,
                    "batter": batter,
                    "bowler": bowler,
                    "non_striker": non_striker,
                    "batter_runs": batter_runs,
                    "extras": extras_total,
                    "total_runs": total_runs,
                    "extras_type": ",".join(extras_detail.keys()) if extras_detail else "",
                    "wicket_type": wicket_type,
                    "player_dismissed": player_dismissed,
                })

                # Batting stats aggregation
                batter_key = (match_id, innings_num, batter)
                batting_stats[batter_key]["team"] = batting_team
                batting_stats[batter_key]["runs"] += batter_runs
                # Only count legal deliveries for balls faced (not wides)
                if not is_wide:
                    batting_stats[batter_key]["balls_faced"] += 1
                if batter_runs == 4:
                    batting_stats[batter_key]["fours"] += 1
                if batter_runs == 6:
                    batting_stats[batter_key]["sixes"] += 1

                if wickets:
                    for w in wickets:
                        dismissed_player = w.get("player_out", "")
                        dismissed_key = (match_id, innings_num, dismissed_player)
                        batting_stats[dismissed_key]["is_out"] = 1
                        batting_stats[dismissed_key]["dismissal_kind"] = w.get("kind", "")
                        batting_stats[dismissed_key]["team"] = batting_team

                # Bowling stats aggregation
                bowler_key = (match_id, innings_num, bowler)
                bowling_stats[bowler_key]["team"] = bowling_team
                bowling_stats[bowler_key]["runs_conceded"] += total_runs
                bowling_stats[bowler_key]["extras_given"] += extras_total
                bowling_stats[bowler_key]["deliveries"] += 1
                # Legal deliveries (not wides or no-balls)
                if not is_wide and not is_noball:
                    bowling_stats[bowler_key]["legal_deliveries"] += 1
                if wickets:
                    for w in wickets:
                        kind = w.get("kind", "")
                        # Don't count run outs as bowler's wickets
                        if kind != "run out":
                            bowling_stats[bowler_key]["wickets"] += 1

    # Convert batting stats to rows
    batting_rows = []
    for (mid, inn, batter), stats in batting_stats.items():
        balls = stats["balls_faced"]
        sr = round((stats["runs"] / balls) * 100, 2) if balls > 0 else 0.0
        batting_rows.append({
            "match_id": mid,
            "innings": inn,
            "batter": batter,
            "team": stats["team"],
            "runs": stats["runs"],
            "balls_faced": balls,
            "fours": stats["fours"],
            "sixes": stats["sixes"],
            "strike_rate": sr,
            "is_out": stats["is_out"],
            "dismissal_kind": stats["dismissal_kind"],
        })

    # Convert bowling stats to rows
    bowling_rows = []
    for (mid, inn, bowler), stats in bowling_stats.items():
        legal = stats["legal_deliveries"]
        overs_bowled = f"{legal // 6}.{legal % 6}"
        economy = round((stats["runs_conceded"] / (legal / 6)), 2) if legal > 0 else 0.0
        bowling_rows.append({
            "match_id": mid,
            "innings": inn,
            "bowler": bowler,
            "team": stats["team"],
            "overs": overs_bowled,
            "deliveries": stats["deliveries"],
            "legal_deliveries": legal,
            "runs_conceded": stats["runs_conceded"],
            "wickets": stats["wickets"],
            "economy": economy,
            "extras_given": stats["extras_given"],
        })

    return deliveries_rows, batting_rows, bowling_rows


def run_pipeline():
    """Main ETL pipeline execution."""
    logger.info("Starting ETL pipeline")
    ensure_output_dir()

    json_files = glob.glob(os.path.join(DATASET_DIR, "*.json"))
    logger.info("Found %s JSON files in %s", len(json_files), DATASET_DIR)

    if not json_files:
        logger.warning("No JSON files found in dataset directory; generated CSV files will be empty")

    all_matches = []
    all_deliveries = []
    all_batting = []
    all_bowling = []

    for index, filepath in enumerate(sorted(json_files), start=1):
        match_id = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.exception("Failed to read JSON file %s", filepath)
            continue

        if index == 1 or index % 25 == 0 or index == len(json_files):
            logger.info("Processing match file %s/%s: %s", index, len(json_files), os.path.basename(filepath))

        # Extract match info
        match_row = parse_match_info(match_id, data)
        all_matches.append(match_row)

        # Extract innings data
        deliveries, batting, bowling = parse_innings_data(match_id, data)
        all_deliveries.extend(deliveries)
        all_batting.extend(batting)
        all_bowling.extend(bowling)

    # Write matches.csv
    matches_path = os.path.join(OUTPUT_DIR, "matches.csv")
    matches_fields = [
        "match_id", "date", "city", "venue", "team1", "team2",
        "winner", "win_by", "win_margin", "event_name", "event_stage",
        "match_type", "gender", "toss_winner", "toss_decision",
        "player_of_match", "season", "overs"
    ]
    with open(matches_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=matches_fields)
        writer.writeheader()
        writer.writerows(all_matches)
    logger.info("Wrote matches.csv with %s rows", len(all_matches))

    # Write deliveries.csv
    deliveries_path = os.path.join(OUTPUT_DIR, "deliveries.csv")
    deliveries_fields = [
        "match_id", "innings", "over", "ball", "batter", "bowler",
        "non_striker", "batter_runs", "extras", "total_runs",
        "extras_type", "wicket_type", "player_dismissed"
    ]
    with open(deliveries_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=deliveries_fields)
        writer.writeheader()
        writer.writerows(all_deliveries)
    logger.info("Wrote deliveries.csv with %s rows", len(all_deliveries))

    # Write batting.csv
    batting_path = os.path.join(OUTPUT_DIR, "batting.csv")
    batting_fields = [
        "match_id", "innings", "batter", "team", "runs", "balls_faced",
        "fours", "sixes", "strike_rate", "is_out", "dismissal_kind"
    ]
    with open(batting_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=batting_fields)
        writer.writeheader()
        writer.writerows(all_batting)
    logger.info("Wrote batting.csv with %s rows", len(all_batting))

    # Write bowling.csv
    bowling_path = os.path.join(OUTPUT_DIR, "bowling.csv")
    bowling_fields = [
        "match_id", "innings", "bowler", "team", "overs", "deliveries",
        "legal_deliveries", "runs_conceded", "wickets", "economy",
        "extras_given"
    ]
    with open(bowling_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=bowling_fields)
        writer.writeheader()
        writer.writerows(all_bowling)
    logger.info("Wrote bowling.csv with %s rows", len(all_bowling))

    logger.info(
        "ETL pipeline complete: matches=%s deliveries=%s batting=%s bowling=%s output_dir=%s",
        len(all_matches),
        len(all_deliveries),
        len(all_batting),
        len(all_bowling),
        OUTPUT_DIR,
    )


if __name__ == "__main__":
    run_pipeline()
