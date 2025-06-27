import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application configuration settings (Pydantic v2 style)
    """

    # Application settings
    APP_NAME: str = "Portfolio Analysis Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost/portfolio_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_EXPIRE_TIME: int = 3600

    # API Keys for market data providers
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    YAHOO_FINANCE_API_KEY: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    TWELVEDATA_API_KEY: Optional[str] = None
    QUANDL_API_KEY: Optional[str] = None

    # Rate limiting
    API_RATE_LIMIT: int = 100
    MARKET_DATA_RATE_LIMIT: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Security
    SECRET_KEY: str = "your-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # Portfolio analysis settings
    MAX_HOLDINGS_PER_ANALYSIS: int = 1000
    DEFAULT_ANALYSIS_PERIOD_DAYS: int = 252
    MONTE_CARLO_SIMULATIONS: int = 1000

    # Tax calculation settings
    TAX_YEAR: int = 2024
    DEFAULT_CURRENCY: str = "INR"

    # Performance settings
    ASYNC_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 10
    CACHE_TTL: int = 3600

    # ✅ Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    @validator('DATABASE_URL')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'sqlite://')):
            raise ValueError('DATABASE_URL must start with postgresql:// or sqlite://')
        return v

    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of: {valid_levels}')
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
