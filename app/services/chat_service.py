"""Chatbot service for AI-powered cricket Q&A.

Integrates with Google Gemini API to provide intelligent responses
based on the cricket dataset.
"""
import json
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from app.services.data_service import DataService
from app.services.transform_service import TransformService
from app.utils.parsers import DateParser, safe_int
from config.settings import get_settings
from core.logging_config import configure_logging

logger = configure_logging(__name__)


class ChatService:
    """Service for handling AI chatbot interactions."""
    
    _base_context: Optional[str] = None
    
    @classmethod
    def _build_base_context(cls) -> str:
        """Build a compact, authoritative context block from dashboard data."""
        if cls._base_context is not None:
            return cls._base_context
        
        overview = TransformService.get_overview()
        batters = TransformService.get_batters()
        teams = TransformService.get_teams()
        
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
                f"- {batter['batter']} ({batter['team']}): runs={batter['runs']}, "
                f"SR={batter['strike_rate']}, innings={batter['innings']}"
            )
        
        lines.append("TOP_ECONOMY_BOWLERS:")
        for bowler in teams["elite_bowlers"][:10]:
            lines.append(
                f"- {bowler['bowler']} ({bowler['team']}): economy={bowler['economy']}, "
                f"wickets={bowler['wickets']}, deliveries={bowler['deliveries']}"
            )
        
        cls._base_context = "\n".join(lines)
        return cls._base_context
    
    @classmethod
    def clear_cache(cls):
        """Clear cached context (call when data changes)."""
        cls._base_context = None
    
    @classmethod
    def _build_query_context(cls, question: str) -> str:
        """Add query-relevant slices from matches/batting/bowling to base context."""
        terms = [t for t in re.findall(r"[a-z0-9]+", question.lower()) if len(t) > 2]
        
        def has_term(text: str) -> bool:
            lowered = (text or "").lower()
            return any(term in lowered for term in terms)
        
        # Get relevant matches
        matches_sorted = sorted(
            DataService.get_matches(),
            key=lambda row: (DateParser.parse_match_date(row.get("date")), row.get("match_id", "")),
            reverse=True,
        )
        
        relevant_matches = []
        for match in matches_sorted:
            blob = " ".join([
                match.get("date", ""),
                match.get("team1", ""),
                match.get("team2", ""),
                match.get("venue", ""),
                match.get("city", ""),
                match.get("event_stage", ""),
                match.get("winner", ""),
            ])
            if terms and not has_term(blob):
                continue
            
            result_text = match.get("winner") or "No result"
            if match.get("winner") and match.get("win_margin") and match.get("win_by"):
                result_text = f"{match['winner']} won by {match['win_margin']} {match['win_by']}"
            
            relevant_matches.append(
                f"- {match.get('date', '')}: {match.get('team1', '')} vs {match.get('team2', '')} "
                f"| {result_text} | {match.get('venue', '')}, {match.get('city', '')}"
            )
            if len(relevant_matches) >= 12:
                break
        
        # Fallback if no matches found
        if not relevant_matches:
            for match in matches_sorted[:8]:
                relevant_matches.append(
                    f"- {match.get('date', '')}: {match.get('team1', '')} vs {match.get('team2', '')} "
                    f"| winner={match.get('winner', '') or 'No result'}"
                )
        
        # Aggregate batting stats for relevant players
        batter_totals = defaultdict(lambda: {"runs": 0, "team": ""})
        for row in DataService.get_batting():
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
        
        # Aggregate bowling stats
        bowler_totals = defaultdict(lambda: {"runs": 0, "balls": 0, "team": ""})
        for row in DataService.get_bowling():
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
        
        # Build context
        chunks = [cls._build_base_context(), "", "QUERY_RELEVANT_MATCHES:"]
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
    
    @classmethod
    def _call_gemini(cls, message: str, history: List[Dict], context_block: str) -> str:
        """Call Gemini REST API with strict policy instructions."""
        settings = get_settings()
        
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={quote_plus(settings.gemini_api_key)}"
        )
        
        system_prompt = (
            "You are the Kinetic Cricket Assistant for this dashboard. "
            "Strict rules: (1) Answer only cricket-related questions. "
            "(2) Use only facts from DATA_CONTEXT supplied in the final user turn; do not use external knowledge. "
            f"(3) If the question is outside cricket OR not answerable from DATA_CONTEXT, reply exactly: '{settings.chat_decline_message}'. "
            "(4) Keep answers concise and numeric when possible."
        )
        
        # Build conversation history
        contents = []
        for turn in history[-settings.chat_max_history:]:
            role = turn.get("role", "user")
            text = str(turn.get("content", "")).strip()
            if not text:
                continue
            contents.append({
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text[:900]}],
            })
        
        # Add current query with context
        prompt = (
            f"DATA_CONTEXT:\n{context_block}\n\n"
            f"USER_QUESTION:\n{message}\n\n"
            f"If the answer is not in DATA_CONTEXT, respond exactly with: {settings.chat_decline_message}"
        )
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        # Build payload
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {
                "temperature": settings.gemini_temperature,
                "topK": settings.gemini_top_k,
                "topP": settings.gemini_top_p,
                "maxOutputTokens": settings.gemini_max_tokens,
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
        
        # Parse response
        candidates = response_payload.get("candidates") or []
        if not candidates:
            return settings.chat_decline_message
        
        parts = candidates[0].get("content", {}).get("parts", [])
        reply = " ".join(part.get("text", "").strip() for part in parts if part.get("text")).strip()
        return reply or settings.chat_decline_message
    
    @classmethod
    def chat(cls, message: str, history: List[Dict]) -> str:
        """Process a chat message and return AI response.
        
        Args:
            message: User's question
            history: Previous conversation turns
            
        Returns:
            AI response text
        """
        context_block = cls._build_query_context(message)
        return cls._call_gemini(message, history, context_block)
