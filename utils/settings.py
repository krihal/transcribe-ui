from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_assignment=True,
        enable_decoding=False,
    )

    API_URL: str = ""
    OIDC_APP_LOGIN_ROUTE: str = ""
    OIDC_APP_LOGOUT_ROUTE: str = ""
    OIDC_APP_REFRESH_ROUTE: str = ""

    WHISPER_MODELS: list[str] = ["Tiny", "Base", "Small", "Medium", "Large"]
    WHISPER_LANGUAGES: list[str] = [
        "Swedish",
        "English",
        "Finnish",
        "Danish",
        "Norwegian",
    ]


@lru_cache
def get_settings() -> Settings:
    """
    Get the settings for the application.
    """

    return Settings()
