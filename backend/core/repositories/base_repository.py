# backend/core/repositories/base_repository.py
from backend.core.extensions import db

class BaseRepository:
    @staticmethod
    def execute(query, params=None):
        """Execute a raw SQL query and return the result."""
        return db.session.execute(query, params or ())

    @staticmethod
    def fetch_all(query, params=None):
        """Fetch all rows for a query."""
        result = db.session.execute(query, params or ())
        return result.mappings().all()

    @staticmethod
    def fetch_one(query, params=None):
        """Fetch a single row."""
        result = db.session.execute(query, params or ())
        return result.mappings().fetchone()

    @staticmethod
    def commit():
        """Explicit commit for transactional operations."""
        db.session.commit()
