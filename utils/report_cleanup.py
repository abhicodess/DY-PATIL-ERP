import os
import logging
from datetime import datetime
from celery_app import celery
from utils.pg_wrapper import qry, exe

logger = logging.getLogger("reports_cleanup")

def delete_expired_reports():
    """
    Finds and deletes files for reports that have passed their expires_at time.
    Updates the database status to 'expired' and cleans up paths.
    """
    logger.info("Executing database scan for expired reports...")
    now = datetime.now()
    
    # Find all done/expired reports that have expired and still have a file path
    expired_rows = qry(
        """
        SELECT id, job_id, file_path, file_size 
        FROM reports 
        WHERE expires_at < %s AND status NOT IN ('failed', 'expired')
        """,
        (now,)
    )
    
    deleted_count = 0
    bytes_freed = 0
    
    for r in expired_rows:
        file_path = r["file_path"]
        job_id = str(r["job_id"])
        
        if file_path and os.path.exists(file_path):
            try:
                size = os.path.getsize(file_path)
                os.remove(file_path)
                bytes_freed += size
                deleted_count += 1
                logger.info(f"Removed expired file from disk: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path} for job {job_id}: {e}")
                
        # Update status to 'expired' in DB
        exe(
            """
            UPDATE reports 
            SET status = 'expired', file_path = NULL, error_msg = 'Report file expired and cleared'
            WHERE id = %s
            """,
            (r["id"],)
        )
        
    mb_freed = bytes_freed / (1024 * 1024)
    logger.info(f"Expired reports cleanup finished. Cleared {deleted_count} files, freed {mb_freed:.2f} MB.")
    return {
        "deleted_count": deleted_count,
        "mb_freed": mb_freed
    }

@celery.task(name="utils.report_cleanup.delete_expired_reports_task")
def delete_expired_reports_task():
    """Celery wrapper task for cleanups."""
    return delete_expired_reports()

@celery.task(base=celery.Task, name="utils.report_cleanup.dispatch_tenant_report_cleanups")
def dispatch_tenant_report_cleanups():
    """Global task to dispatch cleanup for all active tenants."""
    from utils.pg_wrapper import get_public_db
    with get_public_db() as cur:
        cur.execute("SELECT id FROM public.tenants WHERE is_active = true")
        tenants = cur.fetchall()
        for t in tenants:
            delete_expired_reports_task.delay(_tenant_id=t['id'])
