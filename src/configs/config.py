from pydantic_settings import BaseSettings, SettingsConfigDict


class Configs(BaseSettings):
    back_url: str
    tg_bot_token: str
    vk_bot_token: str
    model_config = SettingsConfigDict(
        env_file="../../.docker/.env",
        env_file_encoding="utf-8"
    )
