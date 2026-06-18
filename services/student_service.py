from repositories.student_repository import StudentRepository
from werkzeug.security import generate_password_hash, check_password_hash
from utils.cache import erp_cache
import os

class StudentService:
    def __init__(self):
        self.repository = StudentRepository()

    @erp_cache.cached(ttl=300, key_prefix="student_list")
    def get_all_students(self, filters=None):
        filters = filters or {}
        return self.repository.search(
            q=filters.get('q'),
            dept=filters.get('dept'),
            year=filters.get('year'),
            division=filters.get('division')
        )

    def create_student(self, data):
        # Map legacy keys for backward-compatibility
        if 'roll_no' in data and 'roll' not in data:
            data['roll'] = data.pop('roll_no')
        if 'dept' in data and 'department' not in data:
            data['department'] = data.pop('dept')

        if not data.get('password'):
            data['password'] = os.environ.get("DEFAULT_STUDENT_PASSWORD")
            if not data['password']:
                raise RuntimeError("DEFAULT_STUDENT_PASSWORD must be set in environment variables")
        
        data['password'] = generate_password_hash(data['password'])
        student = self.repository.create(**data)
        # Invalidate student list cache
        erp_cache.invalidate_pattern("student_list:*")
        return student

    def update_student(self, student_id, data):
        if data.get('password'):
            data['password'] = generate_password_hash(data['password'])
        res = self.repository.update(student_id, **data)
        erp_cache.invalidate_pattern("student_list:*")
        return res

    def delete_student(self, student_id):
        res = self.repository.delete(student_id)
        erp_cache.invalidate_pattern("student_list:*")
        return res

    def start_bulk_import(self, file_path, user_id):
        from tasks.student_tasks import process_student_import
        from services.job_service import JobService
        
        job_id = JobService.create_job("STUDENT_IMPORT", user_id)
        process_student_import.delay(job_id, file_path)
        return job_id

    def verify_credentials(self, identifier, password):
        # Try PRN first
        student = self.repository.get_by_prn(identifier)
        if not student:
            # Fallback to Roll
            student = self.repository.get_by_roll(identifier)
        
        if student and check_password_hash(student.password, password):
            return student
        return None
