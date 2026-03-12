from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://labelcheck:labelcheck@localhost:5432/labelcheck"

    # Kimi Moonshot (legacy)
    moonshot_api_key: str = ""
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    moonshot_model: str = "kimi-k2.5"

    # Google Gemini (primary for label analysis)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # EAEU Registry
    eaeu_api_base_url: str = "https://nsi.eaeunion.org/api/v1"
    eaeu_sgr_dict_code: str = "1995"

    # Telegram
    telegram_bot_token: str = ""
    backend_url: str = "http://localhost:8000"

    # File storage
    upload_dir: str = "./uploads"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
