"""Data access service layer.

Wraps Appwrite database access with caching and error handling.
All data fetching goes through this service.
"""
from typing import List, Dict, Any, Optional
from functools import lru_cache

from Appwrite.appwrite_db import get_matches as _appwrite_get_matches
from Appwrite.appwrite_db import get_batting as _appwrite_get_batting
from Appwrite.appwrite_db import get_bowling as _appwrite_get_bowling
from core.logging_config import configure_logging

logger = configure_logging(__name__)


class DataService:
    """Service for accessing cricket data from Appwrite."""
    
    _matches_cache: Optional[List[Dict[str, Any]]] = None
    _batting_cache: Optional[List[Dict[str, Any]]] = None
    _bowling_cache: Optional[List[Dict[str, Any]]] = None
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached data."""
        cls._matches_cache = None
        cls._batting_cache = None
        cls._bowling_cache = None
        logger.info("Data cache cleared")
    
    @classmethod
    def get_matches(cls, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all match data.
        
        Args:
            use_cache: If False, fetches fresh data from source
        """
        if use_cache and cls._matches_cache is not None:
            return cls._matches_cache
        
        try:
            data = _appwrite_get_matches()
            cls._matches_cache = data
            return data
        except Exception as e:
            logger.exception("Failed to fetch matches: %s", e)
            # Return cached data if available, even if stale
            if cls._matches_cache is not None:
                return cls._matches_cache
            return []
    
    @classmethod
    def get_batting(cls, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all batting data.
        
        Args:
            use_cache: If False, fetches fresh data from source
        """
        if use_cache and cls._batting_cache is not None:
            return cls._batting_cache
        
        try:
            data = _appwrite_get_batting()
            cls._batting_cache = data
            return data
        except Exception as e:
            logger.exception("Failed to fetch batting data: %s", e)
            if cls._batting_cache is not None:
                return cls._batting_cache
            return []
    
    @classmethod
    def get_bowling(cls, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all bowling data.
        
        Args:
            use_cache: If False, fetches fresh data from source
        """
        if use_cache and cls._bowling_cache is not None:
            return cls._bowling_cache
        
        try:
            data = _appwrite_get_bowling()
            cls._bowling_cache = data
            return data
        except Exception as e:
            logger.exception("Failed to fetch bowling data: %s", e)
            if cls._bowling_cache is not None:
                return cls._bowling_cache
            return []
    
    @classmethod
    def get_match_by_id(cls, match_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific match by ID."""
        for match in cls.get_matches():
            if match.get("match_id") == match_id:
                return match
        return None
    
    @classmethod
    def get_batting_for_match(cls, match_id: str) -> List[Dict[str, Any]]:
        """Get batting records for a specific match."""
        return [b for b in cls.get_batting() if b.get("match_id") == match_id]
    
    @classmethod
    def get_bowling_for_match(cls, match_id: str) -> List[Dict[str, Any]]:
        """Get bowling records for a specific match."""
        return [b for b in cls.get_bowling() if b.get("match_id") == match_id]
