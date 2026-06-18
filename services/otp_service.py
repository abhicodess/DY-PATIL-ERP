import secrets
import datetime
from utils.pg_wrapper import exe, qone
from services.sms_service import SMSService

class OTPService:
    @staticmethod
    def generate_and_send_otp(phone: str) -> dict:
        """
        Creates a 6-digit OTP and sends it via SMS.
        Valid for 10 minutes.
        """
        # 1. Generate 6-digit code
        otp = str(secrets.randbelow(900000) + 100000)
        
        # 2. Set expiry (10 minutes from now)
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        # 3. Store in Postgres
        # We invalidate any previous unverified OTPs for this phone
        exe("UPDATE otp_verifications SET is_verified=True WHERE phone=%s AND is_verified=False", (phone,))
        
        exe(
            "INSERT INTO otp_verifications (phone, otp_code, expires_at) VALUES (%s, %s, %s)",
            (phone, otp, expires_at)
        )
        
        # 4. Use SMSService to send
        # Prerequisite: Create an 'otp_msg' template in DB
        # Body: "Your ERP verification code is {{otp}}. Valid for 10 minutes."
        result = SMSService.queue_sms(phone, "otp_msg", {"otp": otp})
        
        return {"success": result['success'], "msg": "OTP sent successfully" if result['success'] else result['error']}

    @staticmethod
    def verify_otp(phone: str, code: str) -> dict:
        """
        Verifies if the code is correct and not expired.
        """
        record = qone(
            "SELECT * FROM otp_verifications WHERE phone=%s AND otp_code=%s AND is_verified=False AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1",
            (phone, code)
        )
        
        if not record:
            return {"success": False, "error": "Invalid or expired OTP"}
        
        # Mark as used/verified
        exe("UPDATE otp_verifications SET is_verified=True WHERE id=%s", (record['id'],))
        
        return {"success": True, "msg": "OTP Verified"}
