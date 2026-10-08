
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    app_name: str = "Agentic Enterprise Knowledge Copilot"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # LLM configuration
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-3.5-flash"

    # Weather Tool — OpenWeatherMap API key (free tier: 60 calls/min, no IP rate-limiting)
    # Sign up at https://openweathermap.org/api → "Current Weather Data" free plan.
    # If not set, the tool falls back to the keyless Open-Meteo API.
    openweathermap_api_key: Optional[str] = None


    # Database configuration
    database_url: str = "postgresql://aegis_readonly:aegis_readonly_password@localhost:5432/aegisdb"

    # Vector store configuration (Qdrant)
    qdrant_url: Optional[str] = None
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "enterprise_documents"
    qdrant_prefer_memory: bool = False

    # Redis cache configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Model configuration
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_enabled: bool = True
    # Set USE_GEMINI_EMBEDDINGS=true on Render (512MB) to use Gemini API for
    # embeddings instead of local sentence-transformers, eliminating PyTorch
    # from the runtime and saving ~250MB of RAM.
    use_gemini_embeddings: bool = False
    embedding_vector_size: int = 384   # 384 for local MiniLM, 768 for Gemini

    # Observability & Tracing (LangSmith / Jaeger)
    langsmith_tracing: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "agentic-enterprise-copilot"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # Jaeger Distributed Tracing
    jaeger_enabled: bool = False
    jaeger_host: str = "localhost"
    jaeger_port: int = 4318
    jaeger_endpoint: str = "http://localhost:4318/v1/traces"
    jaeger_ui_url: str = "http://localhost:16686"
    jaeger_username: str = ""   # Grafana Cloud: numeric instance ID
    jaeger_password: str = ""   # Grafana Cloud: API token / password

    # Guardrails
    guardrails_enabled: bool = True
    injection_strictness: float = 0.85

    # Evaluation
    eval_golden_set_path: str = "app/evaluation/golden_dataset.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Warn loudly if running in production with localhost DB/Redis (common Render misconfiguration)
if settings.environment == "production":
    if "localhost" in settings.database_url or "127.0.0.1" in settings.database_url:
        logger.error(
            "MISCONFIGURATION: DATABASE_URL still points to localhost in production! "
            "Set DATABASE_URL from Render's managed PostgreSQL connection string."
        )
    if "localhost" in settings.redis_url or "127.0.0.1" in settings.redis_url:
        logger.error(
            "MISCONFIGURATION: REDIS_URL still points to localhost in production! "
            "Set REDIS_URL from Render's managed Redis connection string."
        )
