from functools import lru_cache

from openai import OpenAI
from app.core.config import Settings, get_settings


@lru_cache()
def get_openai_client() -> OpenAI:
    """获取OpenAI客户端实例"""
    settings: Settings = get_settings()
    api_key = settings.require_openai_api_key()
    return OpenAI(
        api_key=api_key.get_secret_value(),
        base_url=settings.openai_api_base,
        timeout=settings.model_request_timeout_seconds,
        max_retries=settings.model_max_retries,
    )
