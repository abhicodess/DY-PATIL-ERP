from extensions import db
from datetime import datetime

class NotificationToken(db.Model):
    __tablename__ = 'notification_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    fcm_token = db.Column(db.String(255), unique=True, nullable=False)
    device_type = db.Column(db.String(20)) # ios, android, web
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
