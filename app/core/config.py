from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Pydantic 提供的配置基类，自动从环境变量和 .env 文件加载配置
# 支持环境变量优先加载，.env 文件中的配置会覆盖环境变量中的配置
class Settings(BaseSettings):
    """应用配置"""
    # 配置模型，指定环境变量文件路径、编码和额外配置
    # extra="ignore" 表示忽略 .env 文件中未定义的环境变量
    # extra="allow" 表示允许 .env 文件中未定义的环境变量
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="AI Agent Backend",
        description="应用名称")
    
    app_version: str = Field(
        default="0.1.0",
        description="应用版本")
    
    openai_api_key: str = Field(
        validation_alias="OPENAI_API_KEY",
        description="OpenAI API 密钥")
    
    openai_api_base: str = Field(
        validation_alias="OPENAI_BASE_URL",
        description="OpenAI API 基础 URL")
    
    model_name: str = Field(
        validation_alias="MODEL_NAME",
        default="deepseek-chat",
        description="默认模型名称")
    
    openweather_api_key: str = Field(
        validation_alias="OPENWEATHER_API_KEY",
        description="OpenWeather API 密钥")
    
@lru_cache
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()