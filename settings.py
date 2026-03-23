from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    anthropic_api_key: str

    # Postgres (used by LangGraph checkpointer & lead storage)
    database_url: str

    # Telegram notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
