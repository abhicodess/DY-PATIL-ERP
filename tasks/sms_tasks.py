from extensions import celery
from services.sms.factory import SMSFactory
from utils.pg_wrapper import exe, qone
import json
import os
import logging

logger = logging.getLogger("sms_tasks")

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def send_async_sms(self, recipient: str, template_slug: str, context: dict, **kwargs):
    """
    Asynchronously send SMS using Celery with exponential retry and logging.
    """
    logger.info(f"Asynchronously sending SMS to {recipient} with template {template_slug}")
    
    # 1. Fetch Template
    tpl = qone("SELECT body FROM sms_templates WHERE slug=%s AND is_active=True", (template_slug,))
    if not tpl:
        error_msg = f"Template '{template_slug}' not found or inactive"
        logger.error(error_msg)
        try:
            exe(
                "INSERT INTO sms_logs (recipient, message, provider, status, error_log) VALUES (%s, %s, %s, %s, %s)",
                (recipient, f"Template: {template_slug}", "unknown", "failed", error_msg)
            )
        except Exception as le:
            logger.error(f"Failed to log template missing to sms_logs: {le}")
        return {"success": False, "error": error_msg}
    
    # 2. Render Template
    message = tpl['body']
    for key, val in context.items():
        message = message.replace(f"{{{{{key}}}}}", str(val))
    
    # 3. Choose Provider via Factory
    provider_name = os.environ.get("SMS_PROVIDER", "dummy")
    try:
        provider = SMSFactory.get_provider()
    except Exception as e:
        error_msg = f"Failed to get SMS provider: {str(e)}"
        logger.error(error_msg)
        try:
            exe(
                "INSERT INTO sms_logs (recipient, message, provider, status, error_log) VALUES (%s, %s, %s, %s, %s)",
                (recipient, message, provider_name, "failed", error_msg)
            )
        except Exception:
            pass
        
        countdown = (2 ** self.request.retries) * 10
        raise self.retry(exc=e, countdown=countdown)

    # 4. Log the 'sending' status
    log_id = None
    try:
        log_row = qone(
            "INSERT INTO sms_logs (recipient, message, provider, status) VALUES (%s, %s, %s, %s) RETURNING id",
            (recipient, message, provider_name, 'sending')
        )
        if log_row:
            log_id = log_row['id']
    except Exception as le:
        logger.error(f"Failed to write initial sms_log: {le}")

    # 5. Physical Send
    try:
        result = provider.send_sms(recipient, message)
        
        # 6. Update Log with Result
        status = 'delivered' if result['success'] else 'failed'
        if log_id:
            try:
                exe(
                    "UPDATE sms_logs SET status=%s, provider_ref=%s, meta_data=%s, error_log=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (status, result['id'], json.dumps(result['raw']), result['error'], log_id)
                )
            except Exception as le:
                logger.error(f"Failed to update sms_logs with result: {le}")
        
        if not result['success']:
            raise Exception(result['error'] or "Provider failed to deliver SMS")
            
        return {**result, "log_id": str(log_id) if log_id else None}
        
    except Exception as e:
        error_msg = f"SMS delivery failed: {str(e)}"
        logger.error(error_msg)
        
        if log_id:
            try:
                exe(
                    "UPDATE sms_logs SET status=%s, error_log=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                    ('failed', error_msg, log_id)
                )
            except Exception:
                pass
                
        countdown = (2 ** self.request.retries) * 10
        raise self.retry(exc=e, countdown=countdown)
