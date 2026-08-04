from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://studyapp:studyapp_dev_pass@localhost:5432/studyassistant"
    REDIS_URL: str = "redis://localhost:6379/0"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_API_KEY: str = ""
    OLLAMA_CHAT_MODEL: str = "qwen2.5"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    JWT_SECRET: str = "CHANGE_ME_TO_A_RANDOM_SECRET_STRING"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    APP_NAME: str = "AI Study Assistant"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
