import os
import json
import logging
import requests
from extensions import db
from utils.pg_wrapper import exe, qone

logger = logging.getLogger("notification_service")

class NotificationService:
    @staticmethod
    def get_unread_count():
        try:
            return 0
        except Exception:
            return 0

    @staticmethod
    def send_notification(user_id, role, message):
        pass

    @staticmethod
    def send_whatsapp(phone: str, template_name: str, params: dict) -> dict:
        """
        Send WhatsApp notification via Gupshup API with SMS fallback on failure.
        """
        logger.info(f"Attempting to send WhatsApp message to {phone} with template {template_name}")
        
        # 1. Fetch template from DB
        tpl = qone("SELECT body FROM whatsapp_templates WHERE template_name = %s AND is_active = True", (template_name,))
        if not tpl:
            error_msg = f"WhatsApp template '{template_name}' not found or inactive."
            logger.warning(f"{error_msg} Falling back to SMS.")
            
            from services.sms_service import SMSService
            sms_res = SMSService.send_immediate(phone, template_name, params)
            
            try:
                exe(
                    """
                    INSERT INTO communications_log (type, recipient, template_name, message, status, provider, error_log)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    ("whatsapp", phone, template_name, "N/A", "failed", "gupshup", f"{error_msg} Fallback to SMS result: {sms_res}")
                )
            except Exception as le:
                logger.error(f"Failed to write communications_log: {le}")
                
            return {
                "success": sms_res.get("success", False),
                "channel": "sms_fallback",
                "sms_result": sms_res,
                "error": error_msg
            }

        # 2. Render Template
        message = tpl['body']
        for key, val in params.items():
            message = message.replace(f"{{{{{key}}}}}", str(val))

        # 3. Log initial status 'sending' to communications_log
        log_id = None
        try:
            log_row = qone(
                """
                INSERT INTO communications_log (type, recipient, template_name, message, status, provider)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                ("whatsapp", phone, template_name, message, "sending", "gupshup")
            )
            if log_row:
                log_id = log_row['id']
        except Exception as le:
            logger.error(f"Failed to log initial whatsapp send: {le}")

        # 4. Make HTTP POST call to Gupshup API
        api_key = os.environ.get("GUPSHUP_API_KEY", "dummy_key")
        source = os.environ.get("GUPSHUP_SOURCE", "919999999999")
        app_name = os.environ.get("GUPSHUP_APP_NAME", "DYPatilERP")
        
        url = "https://api.gupshup.io/wa/api/v1/msg"
        headers = {
            "apikey": api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "channel": "whatsapp",
            "source": source,
            "destination": phone,
            "src.name": app_name,
            "message": json.dumps({"type": "text", "text": message})
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            res_data = {}
            try:
                res_data = response.json()
            except Exception:
                res_data = {"raw_text": response.text}

            if 200 <= response.status_code < 300 and "error" not in str(res_data).lower():
                provider_ref = res_data.get("messageId") or res_data.get("id") or "GUPSHUP_REF"
                
                if log_id:
                    exe(
                        """
                        UPDATE communications_log
                        SET status = %s, provider_ref = %s, meta_data = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        ("sent", provider_ref, json.dumps(res_data), log_id)
                    )
                return {
                    "success": True,
                    "channel": "whatsapp",
                    "provider_ref": provider_ref,
                    "response": res_data
                }
            else:
                raise Exception(f"Gupshup API returned status {response.status_code}: {res_data}")

        except Exception as e:
            error_msg = f"WhatsApp delivery failed: {str(e)}"
            logger.warning(f"{error_msg} Falling back to SMS.")
            
            if log_id:
                try:
                    exe(
                        """
                        UPDATE communications_log
                        SET status = %s, error_log = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        ("failed", error_msg, log_id)
                    )
                except Exception as le:
                    logger.error(f"Failed to update communications_log: {le}")

            from services.sms_service import SMSService
            sms_res = SMSService.send_immediate(phone, template_name, params)
            
            return {
                "success": sms_res.get("success", False),
                "channel": "sms_fallback",
                "sms_result": sms_res,
                "error": error_msg
            }
