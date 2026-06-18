from flask import request
from flask_socketio import Namespace, join_room, leave_room
from flask_jwt_extended import decode_token

class AttendanceNamespace(Namespace):
    def on_connect(self, auth=None):
        # Allow connecting if auth token is verified
        if not auth or 'token' not in auth:
            return False  # Reject connection
        
        try:
            token = auth['token']
            # Decode and verify the JWT token
            decode_token(token)
        except Exception:
            return False  # Reject connection
            
    def on_join(self, data):
        session_id = data.get('session_id')
        if session_id:
            join_room(f"session_{session_id}")
            
    def on_leave(self, data):
        session_id = data.get('session_id')
        if session_id:
            leave_room(f"session_{session_id}")
