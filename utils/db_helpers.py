
import os
import logging
from utils.pg_wrapper import qry, qone, exe

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_query(sql, params=()):
    """Safely execute a select and return all rows."""
    try:
        return qry(sql, params)
    except Exception as e:
        logger.error(f"DB Query Error: {e} | SQL: {sql}")
        return []

def safe_fetch_one(sql, params=()):
    """Safely fetch a single row."""
    try:
        return qone(sql, params)
    except Exception as e:
        logger.error(f"DB Fetch One Error: {e} | SQL: {sql}")
        return None

def safe_fetch_scalar(sql, params=(), default=0):
    """Safely fetch a single mapping value (like COUNT)."""
    try:
        row = qone(sql, params)
        if row:
            # Return the first value of the dictionary
            return list(row.values())[0]
        return default
    except Exception as e:
        logger.error(f"DB Scalar Error: {e} | SQL: {sql}")
        return default

def safe_execute(sql, params=()):
    """Safely execute an INSERT/UPDATE/DELETE."""
    try:
        return exe(sql, params)
    except Exception as e:
        logger.error(f"DB Execute Error: {e} | SQL: {sql}")
        return None

def log_audit(faculty_id, action, details):
    """Specific logger for the attendance audit table."""
    try:
        exe("INSERT INTO attendance_audit(faculty_id, action, details) VALUES(%s, %s, %s)",
            (faculty_id, action, details))
    except Exception as e:
        logger.error(f"Audit Log Error: {e}")
