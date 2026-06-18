# backend/core/repositories/auth_repository.py
from backend.core.repositories.base_repository import BaseRepository

class AuthRepository(BaseRepository):
    @staticmethod
    def get_user_by_email(email):
        """
        Fetches user credentials and role for authentication.
        Works across admins, faculty, and students (assuming a unified users table or union).
        For this implementation, we assume a 'users' table with 'password_hash' and 'role'.
        """
        sql = "SELECT id, email, password_hash, role, name FROM users WHERE email = %s"
        return AuthRepository.fetch_one(sql, (email,))

    @staticmethod
    def update_last_login(user_id):
        sql = "UPDATE users SET last_login = NOW() WHERE id = %s"
        AuthRepository.execute(sql, (user_id,))
        AuthRepository.commit()
