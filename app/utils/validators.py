"""Input validation utilities."""
import re
from typing import Set, Optional
from config.settings import get_settings


class LogValidator:
    """Validate log query parameters."""
    
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    
    @classmethod
    def validate_level(cls, level: str) -> tuple[bool, Optional[str]]:
        """Validate log level parameter.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not level:
            return True, None
        
        level_upper = level.upper()
        if level_upper not in cls.VALID_LOG_LEVELS:
            return False, f"Invalid level. Use one of: {', '.join(sorted(cls.VALID_LOG_LEVELS))}"
        return True, None
    
    @classmethod
    def validate_limit(cls, limit: str, max_limit: int = 2000) -> tuple[bool, Optional[str], int]:
        """Validate and sanitize limit parameter.
        
        Returns:
            Tuple of (is_valid, error_message, sanitized_value)
        """
        try:
            value = int(limit) if limit else 200
        except ValueError:
            return False, "Invalid limit. Provide an integer.", 200
        
        sanitized = max(1, min(value, max_limit))
        return True, None, sanitized


class ChatValidator:
    """Validate chat/AI query parameters."""
    
    CORE_CRICKET_KEYWORDS = {
        "cricket", "match", "matches", "innings", "inning", "run", "runs", "wicket", "wickets",
        "bat", "batter", "batters", "batting", "bowl", "bowler", "bowlers", "bowling",
        "economy", "strike", "rate", "rpb", "over", "overs", "team", "teams", "venue",
        "city", "winner", "won", "lost", "score", "scores", "tournament", "world", "cup",
        "final", "semi", "group", "powerplay", "boundary", "boundaries", "fours", "sixes",
    }
    
    def __init__(self):
        self._lexicon: Optional[Set[str]] = None
    
    def _build_lexicon(self) -> Set[str]:
        """Build a token lexicon from dataset entities."""
        from app.services.data_service import DataService
        
        lexicon = set(self.CORE_CRICKET_KEYWORDS)
        
        # Add team names, venues, cities from matches
        for match in DataService.get_matches():
            combined = " ".join([
                match.get("team1", ""),
                match.get("team2", ""),
                match.get("venue", ""),
                match.get("city", ""),
                match.get("event_stage", ""),
                match.get("winner", ""),
            ]).lower()
            lexicon.update(token for token in re.findall(r"[a-z0-9]+", combined) if len(token) > 2)
        
        # Add player names
        for row in DataService.get_batting():
            combined = f"{row.get('batter', '')} {row.get('team', '')}".lower()
            lexicon.update(token for token in re.findall(r"[a-z0-9]+", combined) if len(token) > 2)
        
        for row in DataService.get_bowling():
            combined = f"{row.get('bowler', '')} {row.get('team', '')}".lower()
            lexicon.update(token for token in re.findall(r"[a-z0-9]+", combined) if len(token) > 2)
        
        return lexicon
    
    def get_lexicon(self) -> Set[str]:
        """Get or build the cricket lexicon (cached)."""
        if self._lexicon is None:
            self._lexicon = self._build_lexicon()
        return self._lexicon
    
    def is_cricket_query(self, question: str) -> bool:
        """Check if a question is cricket-related."""
        if not question:
            return False
        
        tokens = {token for token in re.findall(r"[a-z0-9]+", question.lower()) if len(token) > 2}
        if not tokens:
            return False
        
        return bool(tokens & self.get_lexicon())
    
    def validate_message(self, message: str) -> tuple[bool, Optional[str], str]:
        """Validate chat message.
        
        Returns:
            Tuple of (is_valid, error_message, sanitized_message)
        """
        settings = get_settings()
        
        cleaned = str(message).strip()
        if not cleaned:
            return False, "Message is required.", ""
        
        # Truncate if too long
        if len(cleaned) > settings.chat_max_message_length:
            cleaned = cleaned[:settings.chat_max_message_length]
        
        if not self.is_cricket_query(cleaned):
            return False, settings.chat_decline_message, cleaned
        
        return True, None, cleaned


# Global validator instance
_chat_validator: Optional[ChatValidator] = None


def get_chat_validator() -> ChatValidator:
    """Get or create the global chat validator."""
    global _chat_validator
    if _chat_validator is None:
        _chat_validator = ChatValidator()
    return _chat_validator
