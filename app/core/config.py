from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Pydantic 提供的配置基类，自动从环境变量和 .env 文件加载配置
# 支持环境变量优先加载，.env 文件中的配置会覆盖环境变量中的配置

# 配置模型，指定环境变量文件路径、编码和额外配置
# extra="ignore" 表示忽略 .env 文件中未定义的环境变量
# extra="allow" 表示允许 .env 文件中未定义的环境变量
class Settings(BaseSettings):
    """从环境变量中加载应用程序设置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(
        default="“AI代理后端”",
        description="应用程序名称，用于在OpenAPI文档中显示",
    )

    app_version: str = Field(
        default="0.1.0",
        description="应用程序版本号，用于在OpenAPI文档中显示",
    )

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
        description="OpenAI兼容模型提供者的API密钥",
    )

    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
        description="OpenAI兼容API的基础URL",
    )

    model_name: str = Field(
        default="gpt-4o-mini",
        validation_alias="MODEL_NAME",
        description="默认的聊天模型名称",
    )



    openweather_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENWEATHER_API_KEY",
        description="OpenWeatherMap API密钥",
    )

    embedding_model: str = Field(
        default="BAAI/bge-small-zh-v1.5",
        validation_alias="EMBEDDING_MODEL",
        description="本地文本嵌入模型名称",
    )

    def require_openai_api_key(self) -> SecretStr:
        """返回OpenAI兼容模型提供者的API密钥，或抛出运行时错误"""
        if self.openai_api_key is None:
            raise RuntimeError(
                "OPENAI_API_KEY is required."
            )
        return self.openai_api_key

    def require_openweather_api_key(self) -> SecretStr:
        """返回OpenWeatherMap API密钥，或抛出运行时错误"""
        if self.openweather_api_key is None:
            raise RuntimeError(
                "OPENWEATHER_API_KEY is required for weather requests."
            )
        return self.openweather_api_key


@lru_cache
def get_settings() -> Settings:
    """返回缓存的应用程序设置"""
    return Settings()