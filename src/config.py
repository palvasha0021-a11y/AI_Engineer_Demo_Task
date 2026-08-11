import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pipeline Configuration loaded from environment variables and .env file."""
    
    # LLM API Keys
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""

    # LLM Models
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_MODEL: str = "llama3-70b-8843"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Services & Auth
    GITHUB_TOKEN: str = ""
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_SHEET_ID: str = ""

    # Pipeline Concurrency & Network Limits
    CONCURRENCY_LIMIT: int = 10
    HTTP_TIMEOUT: int = 15
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 1.5
    MAX_CHUNK_SIZE: int = 4000
    FRESHNESS_HOURS: int = 24
    DEFAULT_RECORD_LIMIT: int = 10

    # Paths
    OUTPUT_DIR: str = "data/output"
    DATABASE_PATH: str = "data/pipeline_storage.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_output_path() -> Path:
        path = Path("data/output")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_db_path() -> Path:
        path = Path("data/pipeline_storage.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
