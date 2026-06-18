import logging
from tasks.base_task import TenantTask
from utils.pg_wrapper import exe
import sentry_sdk

logger = logging.getLogger("reports_engine")

class BaseReportTask(TenantTask):
    """
    Base task for all report generation jobs.
    Provides utility methods to update PostgreSQL status/progress,
    and handles global error tracking via Sentry.
    """
    def update_progress(self, job_id, percent, message=None):
        logger.info(f"Report Job {job_id} progress: {percent}% - {message or ''}")
        try:
            exe(
                """
                UPDATE reports 
                SET progress = %s, status = 'processing', error_msg = %s
                WHERE job_id = %s
                """,
                (int(percent), message, str(job_id))
            )
        except Exception as e:
            logger.error(f"Failed to update report progress in DB: {e}")

    def mark_done(self, job_id, file_path, file_size):
        logger.info(f"Report Job {job_id} marked DONE. Path: {file_path}")
        try:
            exe(
                """
                UPDATE reports 
                SET status = 'done', progress = 100, file_path = %s, file_size = %s, error_msg = NULL
                WHERE job_id = %s
                """,
                (file_path, int(file_size), str(job_id))
            )
        except Exception as e:
            logger.error(f"Failed to mark report done in DB: {e}")

    def mark_failed(self, job_id, error):
        logger.error(f"Report Job {job_id} marked FAILED. Error: {error}")
        try:
            exe(
                """
                UPDATE reports 
                SET status = 'failed', error_msg = %s
                WHERE job_id = %s
                """,
                (str(error), str(job_id))
            )
        except Exception as e:
            logger.error(f"Failed to mark report failed in DB: {e}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Triggered automatically if any report task encounters an unhandled exception.
        """
        logger.error(f"Task failure handler caught exception in {task_id}: {exc}", exc_info=True)
        # Capture error in Sentry
        sentry_sdk.capture_exception(exc)
        # Record failure in DB
        self.mark_failed(task_id, exc)
        super().on_failure(exc, task_id, args, kwargs, einfo)
