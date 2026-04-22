'''appwrite_db.py'''
import os
import logging
from appwrite.query import Query
from Appwrite.appwrite_client import databases

logger = logging.getLogger(__name__)

DATABASE_ID = os.environ["APPWRITE_DATABASE_ID"]

MATCHES_COLLECTION = os.getenv("APPWRITE_MATCHES_COLLECTION_ID", "matches")
BATTING_COLLECTION = os.getenv("APPWRITE_BATTING_COLLECTION_ID", "batting")
BOWLING_COLLECTION = os.getenv("APPWRITE_BOWLING_COLLECTION_ID", "bowling")

_PAGE_SIZE = 100

# ❌ FIXED: removed dangerous alias "runs" → "runs_conceded"
_KEY_ALIASES = {
    "team_1": "team1",
    "team_2": "team2",
    "batting_team": "team",
    "balls": "deliveries",
    "no_balls": "extras_given",
}


def safe_int(v):
    try:
        return int(v)
    except:
        return 0


def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0


def _normalize_key(key):
    key = key.strip().lower().replace(" ", "_")
    return _KEY_ALIASES.get(key, key)


def _normalize_row(collection_id, row):
    row = {_normalize_key(k): v for k, v in row.items()}

    # enforce types
    if collection_id == BATTING_COLLECTION:
        row["runs"] = safe_int(row.get("runs"))
        row["balls_faced"] = safe_int(row.get("balls_faced"))
        row["fours"] = safe_int(row.get("fours"))
        row["sixes"] = safe_int(row.get("sixes"))
        row["strike_rate"] = safe_float(row.get("strike_rate"))
        row["is_out"]      = safe_int(row.get("is_out"))

    if collection_id == BOWLING_COLLECTION:
        row["runs_conceded"] = safe_int(row.get("runs_conceded"))
        row["deliveries"] = safe_int(row.get("deliveries"))
        row["legal_deliveries"] = safe_int(row.get("legal_deliveries"))
        row["wickets"] = safe_int(row.get("wickets"))
        row["economy"]      = safe_float(row.get("economy"))
        row["extras_given"] = safe_int(row.get("extras_given"))
    return {k: v for k, v in row.items() if not k.startswith("$")}


def _fetch_all(collection_id):
    results = []
    cursor = None

    while True:
        queries = [Query.limit(_PAGE_SIZE)]
        if cursor:
            queries.append(Query.cursor_after(cursor))

        res = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=collection_id,
            queries=queries,
        )

        # ✅ FIXED: Proper handling of DocumentList
        if hasattr(res, "documents"):
            docs = res.documents
        elif isinstance(res, dict):
            docs = res.get("documents", [])
        else:
            docs = []

        if not docs:
            break

        for doc in docs:
            if hasattr(doc, "to_dict"):
                raw_doc = doc.to_dict()
            elif isinstance(doc, dict):
                raw_doc = doc
            elif hasattr(doc, "model_dump"):
                raw_doc = doc.model_dump()
            else:
                raw_doc = {}

            # Appwrite SDK now nests user columns under `data`.
            payload = raw_doc.get("data") if isinstance(raw_doc.get("data"), dict) else raw_doc
            results.append(_normalize_row(collection_id, payload))

        if len(docs) < _PAGE_SIZE:
            break

        last_doc = docs[-1]
        if hasattr(last_doc, "to_dict"):
            last_doc_data = last_doc.to_dict()
        elif isinstance(last_doc, dict):
            last_doc_data = last_doc
        elif hasattr(last_doc, "model_dump"):
            last_doc_data = last_doc.model_dump(by_alias=True)
        else:
            last_doc_data = {}

        cursor = last_doc_data.get("$id") or last_doc_data.get("id")

        if not cursor:
            break

    logger.info(f"Fetched {len(results)} from {collection_id}")
    return results

_matches = None
_batting = None
_bowling = None


def get_matches():
    global _matches
    if _matches is None:
        _matches = _fetch_all(MATCHES_COLLECTION)
    return _matches


def get_batting():
    global _batting
    if _batting is None:
        _batting = _fetch_all(BATTING_COLLECTION)
    return _batting


def get_bowling():
    global _bowling
    if _bowling is None:
        _bowling = _fetch_all(BOWLING_COLLECTION)
    return _bowling