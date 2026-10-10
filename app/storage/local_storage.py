import os
from .interface import StorageInterface
from app.core.config import settings

class LocalStorage(StorageInterface):
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.STORAGE_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        
    def save_file(self, content: bytes, filename: str) -> str:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(self.base_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path
        
    def get_file_path(self, filename: str) -> str:
        safe_filename = os.path.basename(filename)
        return os.path.join(self.base_dir, safe_filename)
