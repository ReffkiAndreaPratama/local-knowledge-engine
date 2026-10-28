"""Application configuration."""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "Local Knowledge Engine"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./data/knowledge.db"

    # Security
    SECRET_KEY: str = "change-this-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # File Processing
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = ".pdf,.txt,.md,.docx,.csv,.json,.html,.py,.js,.ts,.jsx,.tsx,.java,.cpp,.c,.h,.go,.rs,.rb,.php"
    ALLOWED_IMPORT_DIRS: str = ""
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Embeddings
    ENABLE_SEMANTIC_SEARCH: bool = False
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cpu"

    # AI Assistant
    ENABLE_AI_ASSISTANT: bool = False
    AI_PROVIDER: str = "ollama"
    AI_MODEL: str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: str = ""

    # Privacy
    DISABLE_TELEMETRY: bool = True
    REQUIRE_AI_CONSENT: bool = True
    STORE_SEARCH_HISTORY: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get list of allowed extensions."""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get the CORS origins as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
