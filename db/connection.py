# db/connection.py
from typing import Any, Dict
from pymongo import MongoClient

_client = None
_db = None

def get_db(secrets: Dict[str, Any]):
    """Return a cached db handle built from Streamlit secrets."""
    global _client, _db
    if _db is not None:
        return _db

    username = secrets["mongo_username"]
    password = secrets["mongo_password"]
    cluster_url = secrets["mongo_cluster_url"]
    db_name = secrets["database_name"]

    uri = f"mongodb+srv://{username}:{password}@{cluster_url}/?retryWrites=true&w=majority"
    _client = MongoClient(uri)
    _db = _client[db_name]
    return _db