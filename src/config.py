from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Bot
    telegram_bot_token: str = Field(..., description="Токен Telegram бота")

    # Mistral AI
    mistral_api_key: str = Field(..., description="API ключ Mistral AI")


settings = Settings()