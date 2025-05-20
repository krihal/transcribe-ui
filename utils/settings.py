import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator


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

    @field_validator("SCOPE", mode="before")
    @classmethod
    def decode_scope(cls, v: str) -> list[str]:
        return [str(x) for x in v.split(",")]

    @field_validator("UNRESTRICTED_ROUTES", mode="before")
    @classmethod
    def decode_unrestricted_routes(cls, v: str) -> list[str]:
        return [str(x) for x in v.split(",")]

    DEBUG: bool = True
    API_URL: str = "http://localhost:8000"
    STATIC_FILES: str = "static"

    # OIDC configuration.
    APP_AUTHORIZE_ROUTE: str = ""
    APP_LOGIN_ROUTE: str = ""
    APP_LOGOUT_ROUTE: str = ""
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    COOKIE_SECRET_KEY: str = ""
    POST_LOGOUT_URI: str = ""
    REDIRECT_URI: str = ""
    UNRESTRICTED_ROUTES: list[str] = ""
    WELL_KNOWN_OPENID_URL: str = ""
    SCOPE: list[str] = []


@lru_cache
def get_settings() -> Settings:
    """
    Get the settings for the application.
    """

    # Create static files directory if it doesn't exist
    if not os.path.exists(Settings().STATIC_FILES):
        os.makedirs(Settings().STATIC_FILES)

    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print(settings.model_dump())
