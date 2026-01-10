from pathlib import Path

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

    # Admin settings
    admin_user_ids: str = Field(
        default="",
        description="Список Telegram user ID администраторов (через запятую в .env)",
    )
    temp_files_dir: Path = Field(
        default=Path("data/temp"),
        description="Директория для временных файлов",
    )

    @property
    def admin_user_ids_list(self) -> list[int]:
        """Парсит admin_user_ids из строки в список int."""
        if not self.admin_user_ids:
            return []
        try:
            return [int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()]
        except ValueError:
            return []


settings = Settings()
