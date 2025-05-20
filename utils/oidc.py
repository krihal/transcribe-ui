from nicegui import app
from EasyOIDC import Config, SessionHandler
from EasyOIDC.frameworks.nicegui import NiceGUIOIDClient
from utils.settings import get_settings

settings = get_settings()
session_storage = SessionHandler(mode="redis", namespace=__name__)
auth_config = Config(
    authorization_endpoint=None,
    client_id=settings.OIDC_CLIENT_ID,
    client_secret=settings.OIDC_CLIENT_SECRET,
    cookie_secret_key=settings.OIDC_COOKIE_SECRET_KEY,
    well_known_openid_url=settings.OIDC_METADATA_URL,
    redirect_uri=settings.OIDC_REDIRECT_URI,
    app_login_route=settings.OIDC_APP_LOGIN_ROUTE,
    app_logout_route=settings.OIDC_APP_LOGOUT_ROUTE,
    app_authorize_route=settings.OIDC_APP_AUTHORIZE_ROUTE,
    unrestricted_routes=settings.OIDC_UNRESTRICTED_ROUTES,
    post_logout_uri=settings.OIDC_POST_LOGOUT_URI,
    scope=settings.OIDC_SCOPE,
)

auth = NiceGUIOIDClient(app, auth_config=auth_config, session_storage=session_storage)


def get_auth() -> NiceGUIOIDClient:
    """
    Get the auth object.
    """
    return auth


def get_auth_config() -> Config:
    """
    Get the auth configuration.
    """
    return auth_config


def is_authenticated() -> bool:
    """
    Check if the user is authenticated.
    """
    return auth.is_authenticated()


def require_authentication(fn) -> callable:
    """
    Decorator to require authentication for a function.
    """

    async def wrapper(*args, **kwargs) -> None:
        if not auth.is_authenticated():
            auth.redirect_to_login()
        else:
            return await fn(*args, **kwargs)

    return wrapper


def validate_authentication() -> None:
    """
    Validate authentication.
    """
    if not auth.is_authenticated():
        auth.redirect_to_login()
        return None


def get_userinfo() -> dict:
    """
    Get the current user.
    """
    return auth.get_userinfo()


def get_jwt() -> str:
    """
    Get the current JWT.
    """
    pass


def get_auth_header() -> dict:
    """
    Get the current JWT.
    """
    jwt = auth.get_token("")[0]["access_token"]
    return {"Authorization": f"Bearer {jwt}"}
