from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bulk Certificate Generator"
    DATABASE_URL: str = "sqlite:///./bulk_certs.db"
    STORAGE_DIR: str = "./storage"
    MAX_RECIPIENTS_PER_REQUEST: int = 5000
    PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

# Ensure storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

# Ensure DB parent directory exists if using sqlite file
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    # Note: sqlite:////absolute/path gets converted to /absolute/path correctly
    if os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
