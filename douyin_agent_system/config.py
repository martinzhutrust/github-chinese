from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "抖音来客后台智能体系统"
    app_version: str = "1.0.0"

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-8"
    max_tokens: int = 4096

    # 来客后台 API
    laike_api_base: str = "https://api.laike.douyin.com"
    laike_api_key: str = ""

    # 抖音电商 API
    douyin_shop_app_id: str = ""
    douyin_shop_app_secret: str = ""

    # Redis（任务队列 / 缓存）
    redis_url: str = "redis://localhost:6379/0"

    # 日志
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
