import jwt
import requests
import time

from nicegui import app
from nicegui import ui
from utils.settings import get_settings

settings = get_settings()


def token_refresh() -> None:
    """
    Refresh the token using the refresh token.
    """

    auth_token = app.storage.user.get("token")
    refresh_token = app.storage.user.get("refresh_token")

    try:
        # Get the expiration time from the JWT
        jwt_instance = jwt.JWT()
        jwt_decoded = jwt_instance.decode(auth_token, do_verify=False)
    except jwt.exceptions.JWTDecodeError:
        # Force the user to log out if the token is invalid
        ui.navigate.to(f"{settings.API_URL}/api/logout")
        return

    # Only refresh if the token is about to expire
    # within 20 seconds.
    if jwt_decoded["exp"] - int(time.time()) > 20:
        return

    try:
        # Make a request to refresh the token
        response = requests.post(
            f"{API_URL}/api/refresh",
            json={"token": refresh_token},
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        ui.navigate.to(f"{API_URL}/api/logout")
        return

    token = response.json().get("access_token")
    app.storage.user["token"] = token


def get_auth_header():
    """
    Get the authorization header for API requests.
    """

    token = app.storage.user.get("token")

    try:
        jwt_instance = jwt.JWT()
        jwt_instance.decode(token, do_verify=False)
    except Exception:
        # Fetch a new token if we for some reason have an invalid token
        ui.navigate.to(f"{settings.API_URL}/api/logout")
        return {}

    return {"Authorization": f"Bearer {token}"}


def get_user_info():
    """
    Get user information from token.
    """

    token = app.storage.user.get("token")

    if not token:
        return {}

    try:
        jwt_instance = jwt.JWT()
        decoded_token = jwt_instance.decode(token, do_verify=False)

        if "eduPersonPrincipalName" in decoded_token:
            username = decoded_token["eduPersonPrincipalName"]
        elif "preferred_username" in decoded_token:
            username = decoded_token["preferred_username"]
        elif "username" in decoded_token:
            username = decoded_token["username"]
        else:
            username = "Unknown"
    except Exception:
        return {}

    return username
