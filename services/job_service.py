import json
import uuid
from extensions import redis_client

class JobService:
    @staticmethod
    def create_job(task_type, user_id):
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "type": task_type,
            "user_id": user_id,
            "status": "PENDING",
            "progress": 0,
            "result_url": None,
            "error": None
        }
        redis_client.setex(f"job:{job_id}", 86400, json.dumps(job_data)) # 24h TTL
        return job_id

    @staticmethod
    def update_status(job_id, status, progress=None, result_url=None, error=None):
        job_key = f"job:{job_id}"
        job_data = redis_client.get(job_key)
        if job_data:
            job_data = json.loads(job_data)
            job_data["status"] = status
            if progress is not None: job_data["progress"] = progress
            if result_url: job_data["result_url"] = result_url
            if error: job_data["error"] = error
            redis_client.setex(job_key, 86400, json.dumps(job_data))

    @staticmethod
    def get_status(job_id):
        job_data = redis_client.get(f"job:{job_id}")
        return json.loads(job_data) if job_data else None
