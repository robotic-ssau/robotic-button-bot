from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Configs(BaseSettings):
    back_url: str
    tg_bot_token: str = ""
    vk_bot_token: str = ""

    # Файл со списком советовцев (Фамилия, VK id, TG id, флаг админа)
    council_csv: Path = PROJECT_ROOT / "data" / "council.csv"
    # Язык файла локализации: src/i18n/locales/<locale>.json
    locale: str = "ru"

    # Логирование
    log_dir: Path = PROJECT_ROOT / "logs"
    log_level: str = "INFO"
    # Сколько дней хранить файлы логов (0 — хранить все)
    log_retention_days: int = 30

    # Таймаут запросов к сервису состояния лаборатории, секунды
    lab_api_timeout: float = 5.0

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".docker" / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("council_csv", "log_dir")
    @classmethod
    def _resolve_relative(cls, value: Path) -> Path:
        return value if value.is_absolute() else PROJECT_ROOT / value

    @field_validator("log_level")
    @classmethod
    def _upper_level(cls, value: str) -> str:
        return value.upper()


@lru_cache(maxsize=1)
def get_configs() -> Configs:
    return Configs()
