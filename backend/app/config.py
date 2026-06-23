# 系统配置管理入口
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = "postgresql://context_platform:context_platform_dev@localhost:5432/context_platform"
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 3600

    # =========================================================================
    # JWT
    # =========================================================================
    jwt_secret_key: str = "change-me-to-a-random-secret-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # =========================================================================
    # Redis
    # =========================================================================
    redis_url: str = "redis://localhost:6379/0"

    # =========================================================================
    # Qdrant
    # =========================================================================
    qdrant_url: str = "http://localhost:6333"

    # =========================================================================
    # LLM
    # =========================================================================
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # =========================================================================
    # Embedding
    # =========================================================================
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    rate_limit_default: str = "600 per minute"
    rate_limit_hourly: str = "10000 per hour"

    # =========================================================================
    # Deduplication
    # =========================================================================
    dedup_similarity_threshold: float = 0.85

    # =========================================================================
    # Confidence Engine — Time-based Decay
    # =========================================================================
    confidence_decay_start_months: float = 6.0
    confidence_decay_rate_per_month: float = 0.03
    confidence_decay_min_score: float = 0.20

    # =========================================================================
    # Confidence Engine — Multi-source Corroboration
    # =========================================================================
    confidence_corroboration_max_boost: float = 0.45

    # =========================================================================
    # Confidence Engine — Contradiction
    # =========================================================================
    confidence_conflict_penalty: float = 0.10

    # =========================================================================
    # Confidence Engine — Review Upgrade
    # =========================================================================
    confidence_review_upgrade_level: str = "L3"
    confidence_review_upgrade_score: float = 0.78

    # =========================================================================
    # Lifecycle Management
    # =========================================================================
    lifecycle_auto_decay_months: int = 6

    # =========================================================================
    # Conflict Detection
    # =========================================================================
    conflict_similarity_threshold: float = 0.75

    # =========================================================================
    # External Integrations — Timeouts
    # =========================================================================
    feishu_api_timeout: float = 30.0
    feishu_bot_timeout: float = 10.0
    ima_api_timeout: float = 30.0
    email_fetch_max: int = 50
    email_fetch_days: int = 7

    # =========================================================================
    # External Integrations — API Keys & URLs
    # =========================================================================
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_bot_webhook: str = ""
    ima_api_key: str = ""
    ima_base_url: str = ""
    stock_data_api_key: str = ""
    stock_data_base_url: str = ""
    email_imap_host: str = ""
    email_imap_user: str = ""
    email_imap_password: str = ""

    # =========================================================================
    # Sub-component config
    # =========================================================================
    context_platform_config_path: str = ""

    # =========================================================================
    # Configuration Sections (for config_service)
    # =========================================================================
    config_valid_sections: str = (
        "confidence_engine,ingestion,search,llm,security,"
        "lifecycle,notification,export,integration,embedding"
    )

    # =========================================================================
    # Logging
    # =========================================================================
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
