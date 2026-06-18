import os
import json
from .sms.factory import SMSFactory
from utils.pg_wrapper import exe, qone

class SMSService:
    @staticmethod
    def send_immediate(recipient: str, template_slug: str, context: dict) -> dict:
        """
        Synchronous SMS sending. 
        Useful for OTPs where immediate feedback is needed.
        """
        # 1. Fetch Template
        tpl = qone("SELECT body FROM sms_templates WHERE slug=%s AND is_active=True", (template_slug,))
        if not tpl:
            return {"success": False, "error": f"Template '{template_slug}' not found or inactive"}
        
        # 2. Render Template
        message = tpl['body']
        for key, val in context.items():
            message = message.replace(f"{{{{{key}}}}}", str(val))
        
        # 3. Choose Provider via Factory
        provider = SMSFactory.get_provider()
        provider_name = os.environ.get("SMS_PROVIDER", "dummy")
        
        # 4. Log the 'queued' status
        log_row = qone(
            "INSERT INTO sms_logs (recipient, message, provider, status) VALUES (%s, %s, %s, %s) RETURNING id",
            (recipient, message, provider_name, 'sending')
        )
        log_id = log_row['id'] if log_row else None
        
        # 5. Physical Send
        result = provider.send_sms(recipient, message)
        
        # 6. Update Log with Result
        status = 'delivered' if result['success'] else 'failed'
        exe(
            "UPDATE sms_logs SET status=%s, provider_ref=%s, meta_data=%s, error_log=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (status, result['id'], json.dumps(result['raw']), result['error'], log_id)
        )
        
        return {**result, "log_id": str(log_id)}

    @staticmethod
    def queue_sms(recipient: str, template_slug: str, context: dict):
        """
        Asynchronously queue SMS sending via Celery.
        """
        from utils.tenant_context import get_tenant_id
        try:
            tenant_id = get_tenant_id()
        except Exception:
            tenant_id = 1  # Default/fallback tenant ID for testing/CLI
            
        from tasks.sms_tasks import send_async_sms
        return send_async_sms.delay(recipient, template_slug, context, _tenant_id=tenant_id)
