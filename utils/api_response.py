import datetime
import uuid
from flask import jsonify, g

def get_request_id():
    """Retrieve current request ID from Flask g, or generate a new one if not present."""
    try:
        if not hasattr(g, 'request_id'):
            g.request_id = str(uuid.uuid4())
        return g.request_id
    except RuntimeError:
        # Working outside request context
        return str(uuid.uuid4())

def success_response(data, message="", status=200, meta=None):
    """
    Returns a standardized JSON success response.
    """
    response_meta = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "version": "1.0",
        "request_id": get_request_id()
    }
    if meta:
        response_meta.update(meta)

    payload = {
        "success": True,
        "message": message,
        "data": data,
        "meta": response_meta
    }
    return jsonify(payload), status

def error_response(message, code, status=400, errors=None):
    """
    Returns a standardized JSON error response.
    """
    response_meta = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "request_id": get_request_id()
    }

    payload = {
        "success": False,
        "error": {
          "code": code,
          "message": message,
          "errors": errors or []
        },
        "meta": response_meta
    }
    return jsonify(payload), status

def paginated_response(data, total, page, per_page, message=""):
    """
    Wraps success_response to include pagination metadata.
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    meta = {
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }
    return success_response(data, message=message, status=200, meta=meta)
