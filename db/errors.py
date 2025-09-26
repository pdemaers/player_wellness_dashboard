# db/errors.py
class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class ApplicationError(Exception):
    """Base exception for database operations."""
    pass