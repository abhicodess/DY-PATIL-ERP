import logging
import traceback
from flask import render_template, request, jsonify

def init_error_handlers(app):
    """
    Stabilizes the application with global error handling and logging.
    """
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error_404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Full traceback logging for development/admin audit
        err_msg = traceback.format_exc()
        logging.getLogger(__name__).error(f"Internal Server Error: {request.path}\n{err_msg}")
        
        # Safe fallback for users
        return render_template('error_500.html', error=str(error)), 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        """Catch-all for any unhandled exception."""
        logging.error(f"Unhandled Exception: {e}", exc_info=True)
        
        if request.path.startswith('/api/'):
            return jsonify({
                "status": "error",
                "message": "An internal system error occurred.",
                "details": str(e)
            }), 500
            
        return render_template('error_500.html', error="An unexpected system error occurred. Please try again later."), 500

    logging.info("Enterprise Error Handlers Initialized.")
