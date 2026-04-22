"""Log querying service.

Handles reading, filtering, and serving log file entries.
"""
import os
import glob
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from app.utils.parsers import LogParser
from core.logging_config import get_log_file_path
from core.logging_config import configure_logging

logger = configure_logging(__name__)


class LogService:
    """Service for querying log files."""
    
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    
    @classmethod
    def get_log_file_candidates(cls, include_archived: bool = False) -> List[str]:
        """Return log files to search, oldest to newest."""
        log_file_path = get_log_file_path()
        
        if include_archived:
            pattern = f"{log_file_path}*"
            candidates = [path for path in glob.glob(pattern) if os.path.isfile(path)]
        else:
            candidates = [log_file_path] if os.path.isfile(log_file_path) else []
        
        candidates.sort(key=lambda path: os.path.getmtime(path))
        return candidates
    
    @classmethod
    def query_entries(
        cls,
        limit: int = 200,
        level: Optional[str] = None,
        query: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        include_archived: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Read and filter log entries from one or many log files.
        
        Args:
            limit: Maximum entries to return
            level: Filter by log level
            query: Text search in logger name and message
            since: Filter entries after this datetime
            until: Filter entries before this datetime
            include_archived: Include rotated log files
            
        Returns:
            Tuple of (entries, source_files)
        """
        search_text = (query or "").strip().lower()
        target_level = level.upper() if level else ""
        matching = []
        
        source_files = cls.get_log_file_candidates(include_archived=include_archived)
        
        for path in source_files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    for raw in handle:
                        parsed = LogParser.parse_log_line(raw)
                        if parsed is None:
                            continue
                        
                        # Apply filters
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
                        
                        # Remove internal _dt field before returning
                        parsed.pop("_dt", None)
                        matching.append(parsed)
                        
            except OSError as e:
                logger.warning("Could not read log file %s: %s", path, e)
                continue
        
        # Apply limit (most recent entries)
        if limit > 0:
            matching = matching[-limit:]
        
        return matching, source_files
    
    @classmethod
    def get_log_info(cls) -> Dict[str, Any]:
        """Get information about the current log file."""
        log_file_path = get_log_file_path()
        return {
            "log_file": log_file_path,
            "exists": os.path.isfile(log_file_path),
            "size_bytes": os.path.getsize(log_file_path) if os.path.isfile(log_file_path) else 0,
        }
