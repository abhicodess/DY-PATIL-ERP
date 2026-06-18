import os
from utils.tenant_context import get_current_tenant

class TenantStorage:
    BASE_PATH = '/app/uploads'
    
    @staticmethod
    def upload_path(filename: str) -> str:
        tenant = get_current_tenant()
        path = os.path.join(
            TenantStorage.BASE_PATH, 
            tenant['slug'], 
            filename
        )
        # Create directories recursively if they don't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    @staticmethod
    def download_url(filename: str) -> str:
        tenant = get_current_tenant()
        return f"/uploads/{tenant['slug']}/{filename}"

    @staticmethod
    def delete(filename: str):
        path = TenantStorage.upload_path(filename)
        if os.path.exists(path):
            os.remove(path)
