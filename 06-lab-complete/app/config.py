"""
Config — 12-Factor: mọi cấu hình đọc từ biến môi trường.
"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.environ.get("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.environ.get("AGENT_API_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10")))
    daily_budget_usd: float = field(default_factory=lambda: float(os.environ.get("DAILY_BUDGET_USD", os.environ.get("MONTHLY_BUDGET_USD", "1.0"))))


settings = Settings()
