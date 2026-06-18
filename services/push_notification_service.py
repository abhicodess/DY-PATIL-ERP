import firebase_admin
from firebase_admin import messaging, credentials
from models.notifications import NotificationToken
from extensions import db

class PushNotificationService:
    def __init__(self):
        # Initialized elsewhere usually, but for completeness:
        # cred = credentials.Certificate('path/to/firebase-key.json')
        # firebase_admin.initialize_app(cred)
        pass

    def register_token(self, user_id, role, fcm_token, device_type):
        token = NotificationToken.query.filter_by(fcm_token=fcm_token).first()
        if not token:
            token = NotificationToken(
                user_id=user_id, 
                role=role, 
                fcm_token=fcm_token, 
                device_type=device_type
            )
            db.session.add(token)
            db.session.commit()
        return token

    def send_to_user(self, user_id, title, body):
        tokens = NotificationToken.query.filter_by(user_id=user_id).all()
        fcm_tokens = [t.fcm_token for t in tokens]
        
        if not fcm_tokens: return
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=fcm_tokens,
        )
        response = messaging.send_multicast(message)
        return response
    
    def send_to_topic(self, topic, title, body):
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic=topic,
        )
        response = messaging.send(message)
        return response
