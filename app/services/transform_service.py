"""Data transformation service.

Contains all business logic for transforming raw data into
analytics-ready formats for the dashboard.
"""
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple

from app.services.data_service import DataService
from app.utils.parsers import DateParser, safe_int
from caching.cache import redis_cache
from config.settings import get_settings
from core.logging_config import configure_logging

logger = configure_logging(__name__)


class TransformService:
    """Service for transforming cricket data into analytics formats."""
    
    # ───────────────────────────────────────────────────────────────
    # Overview Transformations
    # ───────────────────────────────────────────────────────────────
    
    @staticmethod
    @redis_cache(key_prefix="overview", ttl=get_settings().cache_ttl_overview)
    def get_overview() -> Dict[str, Any]:
        """Transform data for the overview dashboard."""
        matches = DataService.get_matches()
        batting = DataService.get_batting()
        
        total_matches = len(matches)
        
        # O(N) runs calculation instead of O(N²)
        runs_by_match = defaultdict(int)
        for b in batting:
            runs_by_match[b.get("match_id")] += safe_int(b.get("runs"))
        
        total_runs = sum(runs_by_match.values())
        
        # Collect unique teams, venues, cities
        teams = set()
        for m in matches:
            teams.add(m.get("team1"))
            teams.add(m.get("team2"))
        
        venues = {m.get("venue") for m in matches if m.get("venue")}
        cities = {m.get("city") for m in matches if m.get("city")}
        
        # Winners and cities
        win_counts = Counter(m.get("winner") for m in matches if m.get("winner"))
        top_winners = win_counts.most_common(10)
        
        city_counts = Counter(m.get("city") for m in matches if m.get("city"))
        top_city = city_counts.most_common(1)[0] if city_counts else ("", 0)
        
        # Runs per match
        runs_per_match = [
            {
                "match_id": m.get("match_id"),
                "date": m.get("date"),
                "total_runs": runs_by_match.get(m.get("match_id"), 0),
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
        }
    
    # ───────────────────────────────────────────────────────────────
    # Matches Transformations
    # ───────────────────────────────────────────────────────────────
    
    @staticmethod
    def get_matches(city_filter: Optional[str] = None, team_filter: Optional[str] = None) -> Dict[str, Any]:
        """Transform data for the matches page."""
        matches = DataService.get_matches()
        batting = DataService.get_batting()
        
        # Pre-build runs lookup (O(N))
        runs_by_match = defaultdict(int)
        for b in batting:
            runs_by_match[b.get("match_id", "")] += safe_int(b.get("runs"))
        
        # Filter matches
        filtered = matches
        if city_filter and city_filter != "All Cities":
            filtered = [m for m in filtered if m.get("city") == city_filter]
        if team_filter and team_filter != "All Teams":
            filtered = [m for m in filtered if m.get("team1") == team_filter or m.get("team2") == team_filter]
        
        # Sort by date, newest first
        filtered_sorted = sorted(
            filtered,
            key=lambda x: (DateParser.parse_match_date(x.get("date")), x.get("match_id", "")),
            reverse=True,
        )
        
        # Build match history with display IDs
        match_history = []
        for idx, m in enumerate(filtered_sorted):
            match_history.append({
                "display_id": f"#M-{1000 + len(filtered_sorted) - idx}",
                "match_id": m.get("match_id", ""),
                "date": m.get("date", ""),
                "team1": m.get("team1", ""),
                "team2": m.get("team2", ""),
                "venue": m.get("venue", ""),
                "city": m.get("city", ""),
                "winner": m.get("winner", ""),
            })
        
        # Venue volume statistics
        city_counts = Counter(m.get("city") for m in matches if m.get("city"))
        venue_volume = city_counts.most_common(10)
        max_vol = venue_volume[0][1] if venue_volume else 1
        
        # Best venue by average score
        venue_scores = defaultdict(list)
        venue_to_city = {}
        for m in matches:
            v = m.get("venue")
            if v:
                venue_scores[v].append(runs_by_match.get(m.get("match_id", ""), 0))
                venue_to_city.setdefault(v, m.get("city", ""))
        
        best_venue, best_avg, best_city = "", 0, ""
        for venue, scores in venue_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            if avg > best_avg:
                best_avg, best_venue, best_city = avg, venue, venue_to_city[venue]
        
        # All cities and teams for filter dropdowns
        all_cities = sorted({m.get("city") for m in matches if m.get("city")})
        all_teams = sorted({m.get("team1") for m in matches} | {m.get("team2") for m in matches} - {None, ""})
        
        return {
            "match_history": match_history,
            "venue_volume": venue_volume,
            "max_volume": max_vol,
            "best_venue": best_venue,
            "best_avg": round(best_avg, 1),
            "best_city": best_city,
            "all_cities": all_cities,
            "all_teams": all_teams,
        }
    
    # ───────────────────────────────────────────────────────────────
    # Batters Transformations
    # ───────────────────────────────────────────────────────────────
    
    @staticmethod
    @redis_cache(key_prefix="batters", ttl=get_settings().cache_ttl_batters)
    def get_batters() -> Dict[str, Any]:
        """Transform data for the batters page."""
        batting = DataService.get_batting()
        
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
            agg[name]["team"] = b.get("team", agg[name]["team"])
            
            # Track unique innings
            agg[name]["innings_set"].add((b.get("match_id"), b.get("innings")))
        
        # Build leaderboard
        leaderboard = []
        for name, stats in agg.items():
            balls = stats["balls"]
            sr = (stats["runs"] / balls * 100) if balls else 0
            rpb = (stats["runs"] / balls) if balls else 0
            boundary_runs = (stats["fours"] * 4) + (stats["sixes"] * 6)
            
            leaderboard.append({
                "batter": name,
                "team": stats["team"],
                "runs": stats["runs"],
                "strike_rate": round(sr, 1),
                "innings": len(stats["innings_set"]),
                "boundary_runs": boundary_runs,
                "rpb": round(rpb, 2),
            })
        
        leaderboard.sort(key=lambda x: x["runs"], reverse=True)
        
        # Calculate distribution metrics
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
    
    # ───────────────────────────────────────────────────────────────
    # Teams/Bowling Transformations
    # ───────────────────────────────────────────────────────────────
    
    @staticmethod
    @redis_cache(key_prefix="teams", ttl=get_settings().cache_ttl_teams)
    def get_teams() -> Dict[str, Any]:
        """Transform data for the teams page."""
        bowling = DataService.get_bowling()
        matches = DataService.get_matches()
        
        # Per-bowler aggregation
        bowler_agg = defaultdict(lambda: {"balls": 0, "runs": 0, "wickets": 0, "team": ""})
        for b in bowling:
            name = b.get("bowler")
            if not name:
                continue
            bowler_agg[name]["balls"] += safe_int(b.get("legal_deliveries"))
            bowler_agg[name]["runs"] += safe_int(b.get("runs_conceded"))
            bowler_agg[name]["wickets"] += safe_int(b.get("wickets"))
            bowler_agg[name]["team"] = b.get("team") or bowler_agg[name]["team"]
        
        # Elite bowlers (min 30 balls)
        bowlers = []
        for name, stats in bowler_agg.items():
            if stats["balls"] < 30:
                continue
            economy = stats["runs"] / (stats["balls"] / 6) if stats["balls"] > 0 else 0
            bowlers.append({
                "bowler": name,
                "team": stats["team"],
                "economy": round(economy, 2),
                "wickets": stats["wickets"],
                "deliveries": stats["balls"],
            })
        bowlers.sort(key=lambda x: x["economy"])
        
        # Per-team average runs conceded
        team_match_ids = defaultdict(set)
        team_runs_given = defaultdict(int)
        
        for b in bowling:
            team = b.get("team")
            mid = b.get("match_id")
            if not team or not mid:
                continue
            team_runs_given[team] += safe_int(b.get("runs_conceded"))
            team_match_ids[team].add(mid)
        
        avg_conceded = []
        for team, match_ids in team_match_ids.items():
            n = len(match_ids)
            avg_conceded.append({
                "team": team,
                "avg": round(team_runs_given[team] / n, 1) if n else 0,
                "matches": n,
                "total_conceded": team_runs_given[team],
            })
        avg_conceded.sort(key=lambda x: x["avg"])
        
        max_avg_conceded = max([x["avg"] for x in avg_conceded], default=1)
        
        return {
            "elite_bowlers": bowlers[:10],
            "avg_conceded": avg_conceded,
            "max_avg_conceded": max_avg_conceded,
        }
