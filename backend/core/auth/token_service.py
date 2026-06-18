# backend/core/auth/token_service.py
import jwt
import datetime
from flask import current_app

class TokenService:
    @staticmethod
    def generate_tokens(user_id, role):
        """
        Generates an Access Token and a Refresh Token.
        Access: Short-lived (15 min)
        Refresh: Long-lived (7 days)
        """
        secret = current_app.config.get("SECRET_KEY", "prod-secret-change-me")
        
        access_payload = {
            "sub": user_id,
            "role": role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
            "iat": datetime.datetime.utcnow(),
            "type": "access"
        }
        
        refresh_payload = {
            "sub": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
            "iat": datetime.datetime.utcnow(),
            "type": "refresh"
        }
        
        access_token = jwt.encode(access_payload, secret, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, secret, algorithm="HS256")
        
        return access_token, refresh_token

    @staticmethod
    def decode_token(token):
        """
        Decodes a JWT token. Returns payload or None if invalid.
        """
        try:
            secret = current_app.config.get("SECRET_KEY", "prod-secret-change-me")
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return {"error": "token_expired"}
        except jwt.InvalidTokenError:
            return {"error": "token_invalid"}
        except Exception:
            return {"error": "decoding_failed"}
