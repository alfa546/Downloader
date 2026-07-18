from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "MediaForge")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    
    # Use SQLite for Celery instead of Redis to run natively on Windows without Docker
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "sqla+sqlite:///celerydb.sqlite")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "db+sqlite:///celeryresults.sqlite")
    
    STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", "../storage")).resolve()

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
