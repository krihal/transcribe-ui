import jwt
import requests
import time

from nicegui import app
from nicegui import ui
from typing import Optional
from utils.settings import get_settings


settings = get_settings()


def token_refresh() -> None:
    """
    Refresh the token using the refresh token.
    """

    token_auth = app.storage.user.get("token")
    token_refresh = app.storage.user.get("refresh_token")

    try:
        jwt_instance = jwt.JWT()
        jwt_decoded = jwt_instance.decode(token_auth, do_verify=False)
    except Exception:
        return None

    # Only refresh if the token is about to expire within 20 seconds.
    if jwt_decoded["exp"] - int(time.time()) > 20:
        return None

    try:
        response = requests.post(
            settings.OIDC_APP_REFRESH_ROUTE,
            json={"token": token_refresh},
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    token = response.json().get("access_token")
    app.storage.user["token"] = token

    return token


def get_auth_header() -> dict[str, str]:
    """
    Get the authorization header for API requests.
    """

    token = app.storage.user.get("token")

    try:
        jwt_instance = jwt.JWT()
        jwt_instance.decode(token, do_verify=False)
    except Exception:
        return None

    return {"Authorization": f"Bearer {token}"}


def get_user_info() -> tuple[str, int] | None:
    """
    Get user information from token.
    """

    token = app.storage.user.get("token")

    if not token:
        return None, None

    try:
        jwt_instance = jwt.JWT()
        decoded_token = jwt_instance.decode(token, do_verify=False)
        lifetime = decoded_token["exp"] - int(time.time())

        if "eduPersonPrincipalName" in decoded_token:
            username = decoded_token["eduPersonPrincipalName"]
        elif "preferred_username" in decoded_token:
            username = decoded_token["preferred_username"]
        elif "username" in decoded_token:
            username = decoded_token["username"]
        else:
            username = "Unknown"
    except Exception:
        return None, None

    return username, lifetime


def get_admin_status() -> bool:
    """
    Check if the user is an admin based on the token.
    """

    try:
        response = requests.get(
            f"{settings.API_URL}/api/v1/me", headers=get_auth_header()
        )
        response.raise_for_status()
        data = response.json()

        return data["result"]["admin"]

    except requests.exceptions.RequestException:
        return False

    return True
