from flask import jsonify

class ApiResponse:
    """Standardized API Response format."""
    
    @staticmethod
    def success(data=None, message="Success", status_code=200, meta=None):
        response = {
            "status": "success",
            "message": message,
            "data": data
        }
        if meta:
            response["meta"] = meta
        return jsonify(response), status_code

    @staticmethod
    def error(message="An error occurred", status_code=400, details=None):
        response = {
            "status": "error",
            "message": message
        }
        if details:
            response["details"] = details
        return jsonify(response), status_code

    @staticmethod
    def unauthorized(message="Unauthorized"):
        return ApiResponse.error(message, 401)

    @staticmethod
    def forbidden(message="Forbidden"):
        return ApiResponse.error(message, 403)

    @staticmethod
    def not_found(message="Resource not found"):
        return ApiResponse.error(message, 404)
