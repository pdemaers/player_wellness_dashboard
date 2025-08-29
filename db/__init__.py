# db/__init__.py

"""Database package for Player Wellness Dashboard.

Contains:
    - MongoWrapper: main access layer to MongoDB
    - DatabaseError: wrapper for pymongo exceptions
"""

from .mongo_wrapper import MongoWrapper, DatabaseError

__all__ = ["MongoWrapper", "DatabaseError"]