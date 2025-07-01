from nicegui import ui
from utils.common import (
    page_init,
)
from utils.token import get_admin_status
import requests
from utils.settings import get_settings
from utils.token import get_auth_header
from datetime import datetime, timedelta
import json

settings = get_settings()


def get_statistics() -> dict:
    """
    Get statistics from the API.
    """
    response = requests.get(
        f"{settings.API_URL}/api/v1/statistics", headers=get_auth_header()
    )
    response.raise_for_status()
    data = response.json()
    return data


def format_seconds_to_duration(seconds: int) -> str:
    """
    Convert seconds to human readable duration.
    """
    if seconds == 0:
        return "0 minutes"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if remaining_seconds > 0:
        parts.append(f"{remaining_seconds}s")

    return " ".join(parts)


def format_last_login(last_login_str: str) -> str:
    """
    Format last login time to relative time.
    """
    try:
        last_login = datetime.fromisoformat(last_login_str.replace("Z", "+00:00"))
        now = datetime.now(last_login.tzinfo)
        diff = now - last_login

        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"
    except Exception:
        return last_login_str


def create_chart_data(active_users: list) -> dict:
    """
    Create chart data from active users.
    """
    transcription_data = []
    for user in active_users:
        seconds = int(user.get("transcribed_seconds", 0))
        transcription_data.append(
            {
                "user": user["username"].split("@")[0],  # Show username without domain
                "seconds": seconds,
                "formatted": format_seconds_to_duration(seconds),
            }
        )

    admin_count = sum(1 for user in active_users if user.get("admin", False))
    regular_count = len(active_users) - admin_count
    recent_activity = []
    now = datetime.now()

    for user in active_users:
        try:
            last_login = datetime.fromisoformat(
                user["last_login"].replace("Z", "+00:00")
            )
            days_ago = (now - last_login).days
            if days_ago <= 7:
                recent_activity.append(
                    {
                        "day": f"{days_ago} days ago" if days_ago > 0 else "Today",
                        "user": user["username"].split("@")[0],
                    }
                )
        except:
            pass

    return {
        "transcription": transcription_data,
        "user_types": [
            {"type": "Admin", "count": admin_count},
            {"type": "Regular", "count": regular_count},
        ],
        "recent_activity": recent_activity,
    }


def create() -> None:
    @ui.refreshable
    @ui.page("/admin")
    def home() -> None:
        """
        Admin dashboard page with statistics and charts.
        """
        if not get_admin_status():
            ui.navigate.to("/home")
            return

        page_init()

        try:
            statistics = get_statistics()
            result = statistics.get("result", {})

            total_users = result.get("total_users", 0)
            active_users = result.get("active_users", [])
            total_transcribed_seconds = result.get("total_transcribed_seconds", 0)

            with ui.row().classes("w-full gap-6 mb-8"):
                with ui.card().classes("metric-card flex-1"):
                    ui.html(f'<div class="metric-value">{total_users}</div>')
                    ui.html('<div class="metric-label">Total Users</div>')

                with ui.card().classes("metric-card flex-1"):
                    ui.html(
                        f'<div class="metric-value">{format_seconds_to_duration(total_transcribed_seconds)}</div>'
                    )
                    ui.html('<div class="metric-label">Total Transcription Time</div>')

            columns = [
                {
                    "name": "username",
                    "label": "Username",
                    "field": "username",
                    "align": "left",
                },
                {
                    "name": "realm",
                    "label": "Realm",
                    "field": "realm",
                    "align": "left",
                },
                {
                    "name": "admin",
                    "label": "Role",
                    "field": "admin",
                    "align": "center",
                },
                {
                    "name": "transcribed_seconds",
                    "label": "Total Transcription Time",
                    "field": "transcribed_seconds",
                    "align": "right",
                },
            ]

            table_data = []
            for user in active_users:
                table_data.append(
                    {
                        "username": user.get("username", "N/A"),
                        "realm": user.get("realm", "N/A"),
                        "admin": "👑 Admin" if user.get("admin", False) else "👤 User",
                        "transcribed_seconds": format_seconds_to_duration(
                            int(user.get("transcribed_seconds", 0))
                        ),
                        "last_login": format_last_login(
                            user.get("last_login", "Never")
                        ),
                    }
                )

            ui.table(columns=columns, rows=table_data, pagination=10).classes(
                "w-full h-full"
            )

        except Exception as e:
            with ui.column().classes("w-full items-center justify-center min-h-96"):
                ui.html('<div class="text-6xl mb-4">⚠️</div>')
                ui.html(
                    '<div class="text-2xl text-red-600 mb-2">Error Loading Dashboard</div>'
                )
                ui.html(f'<div class="text-gray-600">{str(e)}</div>')
                ui.button("🔄 Retry", on_click=home.refresh).classes("refresh-btn mt-4")
