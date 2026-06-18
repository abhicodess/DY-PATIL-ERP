from repositories.faculty_repository import FacultyRepository
from werkzeug.security import generate_password_hash, check_password_hash
import os

class FacultyService:
    def __init__(self):
        self.repository = FacultyRepository()

    def get_all_faculty(self, filters=None):
        filters = filters or {}
        return self.repository.search(
            q=filters.get('q'),
            dept=filters.get('dept')
        )

    def create_faculty(self, data):
        if not data.get('password'):
            data['password'] = os.environ.get("DEFAULT_FACULTY_PASSWORD")
            if not data['password']:
                raise RuntimeError("DEFAULT_FACULTY_PASSWORD must be set in environment variables")
        
        data['password'] = generate_password_hash(data['password'])
        return self.repository.create(**data)

    def update_faculty(self, faculty_id, data):
        if data.get('password'):
            data['password'] = generate_password_hash(data['password'])
        return self.repository.update(faculty_id, **data)

    def delete_faculty(self, faculty_id):
        return self.repository.delete(faculty_id)

    def verify_credentials(self, email, password):
        faculty = self.repository.get_by_email(email)
        if faculty and check_password_hash(faculty.password, password):
            return faculty
        return None
