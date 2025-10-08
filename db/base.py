# db/base.py
from typing import Any, Dict, Iterable
from pymongo.collection import Collection
from .errors import DatabaseError

class BaseRepository:
    def __init__(self, db, collection_name: str):
        self.db = db
        self.col: Collection = db[collection_name]

    def find_safe(self, filt: Dict[str, Any], proj: Dict[str, int] | None = None) -> list[Dict[str, Any]]:
        try:
            return list(self.col.find(filt, proj))
        except Exception as e:
            raise DatabaseError(f"[{self.col.name}] find failed: {e}") from e

    def insert_one_safe(self, doc: Dict[str, Any]):
        try:
            return self.col.insert_one(doc)
        except Exception as e:
            raise DatabaseError(f"[{self.col.name}] insert failed: {e}") from e

    def update_one_safe(self, filt: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        try:
            return self.col.update_one(filt, update, upsert=upsert)
        except Exception as e:
            raise DatabaseError(f"[{self.col.name}] update failed: {e}") from e

    def bulk_write_safe(self, ops: Iterable[Any]):
        try:
            return self.col.bulk_write(list(ops))
        except Exception as e:
            raise DatabaseError(f"[{self.col.name}] bulk_write failed: {e}") from e