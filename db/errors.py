class DatabaseError(Exception):
    """Errors raised when MongoDB operations fail."""


class ApplicationError(Exception):
    """Errors raised in our own application logic (not DB-related)."""