from extensions import celery
from utils.pg_wrapper import qry, get_public_db
from services.email_service import EmailService
from utils.version_router import VERSION_CONFIGS
from utils.deprecation_headers import DEPRECATION_CONFIG

@celery.task(bind=True, max_retries=3)
def notify_deprecated_version_consumers(self, version: str):
    """
    Selects all api_consumers currently calling the deprecated version and sends warnings.
    """
    email_service = EmailService()
    
    # Query api_consumers table in public schema
    consumers = qry("SELECT name, contact_email, current_version FROM public.api_consumers WHERE current_version = %s", (version,))
    
    config = DEPRECATION_CONFIG.get(version)
    if not config:
        return f"No deprecation configuration found for version {version}"

    # Extract sunset date from config or set fallback
    sunset_date = config.get("Sunset", "2026-01-01")
    migration_guide = config.get("Link", "").split(";")[0].replace("<", "").replace(">", "")
    if not migration_guide:
        migration_guide = "https://yourerp.com/docs/migration/v1-to-v2"

    sent_count = 0
    for consumer in consumers:
        email_service.send_deprecation_warning(
            contact_email=consumer["contact_email"],
            version=version,
            sunset_date=sunset_date,
            migration_guide=migration_guide
        )
        sent_count += 1
        
    return f"Notified {sent_count} consumers of version {version} deprecation"
