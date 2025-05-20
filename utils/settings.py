import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Settings for the application.
    """

    @field_validator("OIDC_SCOPE", mode="before")
    @classmethod
    def decode_scope(cls, v: str) -> list[str]:
        return [str(x) for x in v.split(",")]

    @field_validator("OIDC_UNRESTRICTED_ROUTES", mode="before")
    @classmethod
    def decode_unrestricted_routes(cls, v: str) -> list[str]:
        return [str(x) for x in v.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_assignment=True,
        enable_decoding=False,
    )

    API_DEBUG: bool = True
    API_STATIC_FILES: str = ""
    API_URL: str = ""

    # OIDC configuration.
    OIDC_APP_AUTHORIZE_ROUTE: str = ""
    OIDC_APP_LOGIN_ROUTE: str = ""
    OIDC_APP_LOGOUT_ROUTE: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_COOKIE_SECRET_KEY: str = ""
    OIDC_METADATA_URL: str = ""
    OIDC_POST_LOGOUT_URI: str = ""
    OIDC_REDIRECT_URI: str = ""
    OIDC_SCOPE: list[str] = []
    OIDC_UNRESTRICTED_ROUTES: list[str] = ""


@lru_cache
def get_settings() -> Settings:
    """
    Get the settings for the application.
    """

    # Create static files directory if it doesn't exist
    if not os.path.exists(Settings().API_STATIC_FILES):
        os.makedirs(Settings().API_STATIC_FILES)

    return Settings()
