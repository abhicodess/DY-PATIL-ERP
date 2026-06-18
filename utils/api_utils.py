from flask import jsonify

def json_success(data=None, message="Success", status_code=200):
    """Returns a standardized JSON success response."""
    response = {
        "ok": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def json_error(error_message="An error occurred", status_code=400, details=None):
    """Returns a standardized JSON error response."""
    response = {
        "ok": False,
        "error": error_message
    }
    if details is not None:
        response["details"] = details
    return jsonify(response), status_code
