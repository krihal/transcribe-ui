import asyncio
import requests

from nicegui import app
from nicegui import ui
from typing import Optional
from utils.settings import get_settings
from utils.token import get_auth_header
from utils.token import get_user_info
from utils.token import token_refresh
from utils.token import get_admin_status

settings = get_settings()
API_URL = settings.API_URL

jobs_columns = [
    {
        "name": "filename",
        "label": "Filename",
        "field": "filename",
        "align": "left",
        "classes": "text-weight-medium",
    },
    {
        "name": "created_at",
        "label": "Created At",
        "field": "created_at",
        "align": "left",
    },
    {
        "name": "created_at",
        "label": "Updated At",
        "field": "updated_at",
        "align": "left",
    },
    {
        "name": "model_type",
        "label": "Model",
        "field": "model_type",
        "align": "left",
    },
    {
        "name": "language",
        "label": "Language",
        "field": "language",
        "align": "left",
    },
    {
        "name": "status",
        "label": "Status",
        "field": "status",
        "align": "left",
    },
]


def logout() -> None:
    """
    Log out the user by clearing the token and navigating to the logout endpoint.
    """

    app.storage.user.clear()
    ui.navigate.to(settings.OIDC_APP_LOGOUT_ROUTE)


def show_userinfo() -> None:
    """
    Show a dialog with user information and a logout button.
    """
    username, lifetime = get_user_info()

    with ui.dialog() as dialog:
        with ui.card().style("width: 50%; align-self: center; margin-top: 10%;"):
            ui.label("User Information").classes("text-h5")
            ui.separator()

            with ui.row().style("align-items: center; justify-content: center;"):
                with ui.column().classes("col-12 col-sm-6"):
                    ui.label(f"Username: {username}")
                with ui.column().classes("col-12 col-sm-6"):
                    ui.label(f"Token expires in {lifetime} seconds")

            ui.separator()
            ui.button(
                "Logout",
                icon="logout",
                on_click=lambda: logout(),
            ).props(
                "color=primary"
            ).style("margin-left: 10px;")

    dialog.open()


def page_init(header_text: Optional[str] = "") -> None:
    """
    Initialize the page with a header and background color.
    """

    def refresh():
        if not token_refresh():
            ui.navigate.to(settings.OIDC_APP_LOGOUT_ROUTE)

    if header_text:
        header_text = f" - {header_text}"

    is_admin = get_admin_status()
    if is_admin:
        header_text += " (ADMIN)"

    with ui.header().style(
        "background-color: #77aadb; display: flex; justify-content: space-between; align-items: center;"
    ):
        ui.label("Sunet Transcriber" + header_text).classes("text-h5 text-white")

        with ui.element("div").style("display: flex; gap: 0px;"):
            if is_admin:
                ui.button(
                    icon="settings",
                    on_click=lambda: ui.navigate.to("/admin"),
                ).props("flat color=red")
            ui.button(
                icon="home",
                on_click=lambda: ui.navigate.to("/home"),
            ).props("flat color=white")
            ui.button(
                icon="person",
                on_click=lambda: show_userinfo(),
            ).props("flat color=white")
            ui.button(
                icon="help",
                on_click=lambda: ui.navigate.to("/home"),
            ).props("flat color=white")

            ui.timer(30, refresh)
            ui.add_head_html("<style>body {background-color: #ffffff;}</style>")


def jobs_get() -> list:
    """
    Get the list of transcription jobs from the API.
    """
    jobs = []

    try:
        response = requests.get(
            f"{API_URL}/api/v1/transcriber", headers=get_auth_header()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    for idx, job in enumerate(response.json()["result"]["jobs"]):
        if job["status"] == "in_progress":
            job["status"] = "transcribing"

        job_data = {
            "id": idx,
            "uuid": job["uuid"],
            "filename": job["filename"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "language": job["language"].capitalize(),
            "status": job["status"].capitalize(),
            "model_type": job["model_type"].capitalize(),
        }

        jobs.append(job_data)

    # Sort jobs by created_at in descending order
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    return jobs


def table_click(event) -> None:
    """
    Handle the click event on the table rows.
    """

    status = event.args[1]["status"].lower()
    uuid = event.args[1]["uuid"]
    filename = event.args[1]["filename"]
    model_type = event.args[1]["model_type"]
    language = event.args[1]["language"]

    if status != "completed":
        return

    # Dialog to pick which format to open, TXT or SRT
    with ui.dialog() as dialog:
        with ui.card().style(
            "background-color: white; align-self: center; border: 0; width: 100%;"
        ):
            # Information about the transcription
            ui.label(f"Transcription for {filename}").classes(
                "text-h6 q-mb-md text-primary"
            )
            ui.label(f"UUID: {uuid}")
            ui.label(f"Model: {model_type}")
            ui.label(f"Language: {language}")
            ui.label("Status: Completed")
            ui.label("Select the format to edit the transcription.").classes(
                "text-subtitle2 q-mb-md"
            )
            with ui.row().classes("justify-end"):
                ui.button(
                    "TXT",
                    icon="text_fields",
                    on_click=lambda: ui.navigate.to(
                        f"/txt?uuid={uuid}&filename={filename}&model={model_type}&language={language}"
                    ),
                ).props("color=primary")
                ui.button(
                    "SRT",
                    icon="subtitles",
                    on_click=lambda: ui.navigate.to(
                        f"/srt?uuid={uuid}&filename={filename}&model={model_type}&language={language}"
                    ),
                ).props("color=primary")
                ui.button(
                    "Close",
                    icon="cancel",
                ).on("click", lambda: dialog.close())
        dialog.open()


def post_file(file: str, filename: str) -> None:
    """
    Post a file to the API.
    """
    files_json = {"file": (filename, file.read())}

    try:
        response = requests.post(
            f"{API_URL}/api/v1/transcriber", files=files_json, headers=get_auth_header()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        ui.notify(
            f"Error when uploading file: {str(e)}", type="negative", position="top"
        )
        return

    return True


async def upload_file(files) -> None:
    """
    Upload a file to the server.
    """
    try:
        for file, filename in zip(files.contents, files.names):
            await asyncio.to_thread(post_file, file, filename)
            ui.notify(f"Uploaded: {filename}", position="top")
    except Exception as e:
        ui.notify(f"Error: Failed to save file {filename}: {e}")
        return


def table_upload(table) -> None:
    """
    Handle the click event on the Upload button.
    """
    with ui.dialog() as dialog:
        with ui.card().style(
            "background-color: white; align-self: center; border: 0; width: 100%; height: 30%;"
        ):
            ui.upload(
                on_multi_upload=lambda file: upload_file(file),
                multiple=True,
                max_files=5,
                label="Upload file",
            ).style(
                "width: 100%; align-self: center; border-radius: 10px; height: 100%;"
            )
            ui.separator()
            ui.button(
                "Done",
                icon="check_circle",
                on_click=lambda: dialog.close(),
            ).props("color=primary").style("margin-left: 10px; margin-bottom: 10px;")

        dialog.open()


def table_transcribe(table) -> None:
    """
    Handle the click event on the Transcribe button.
    """

    selected_rows = table.selected

    if not selected_rows:
        ui.notify("Error: No files selected", type="negative", position="top")
        return

    with ui.dialog() as dialog:
        with ui.card().style(
            "background-color: white; align-self: center; border: 0;"
        ).classes("w-full no-shadow no-border"):
            with ui.row().classes("w-full"):
                ui.label("Transcription Settings").style("width: 100%;").classes(
                    "text-h6 q-mb-md text-primary"
                )
                ui.label(
                    "Select the language, model, and number of speakers for transcription."
                )
                with ui.column().classes("col-12 col-sm-24"):
                    ui.label("Language").classes("text-subtitle2 q-mb-sm")
                    language = ui.select(
                        settings.WHISPER_LANGUAGES,
                        label="Select language",
                    ).classes("w-full")

                with ui.column().classes("col-12 col-sm-24"):
                    ui.label("Model").classes("text-subtitle2 q-mb-sm")
                    model = ui.select(
                        settings.WHISPER_MODELS,
                        label="Select model",
                    ).classes("w-full")
                # Number of speakers
                with ui.column().classes("col-12 col-sm-24"):
                    ui.label("Number of speakers (0 for automatic)").classes(
                        "text-subtitle2 q-mb-sm"
                    )
                    speakers = ui.number(value="0").classes("w-full")
            with ui.row():
                ui.button(
                    "Start",
                    icon="play_circle_filled",
                    on_click=lambda: start_transcription(
                        selected_rows,
                        language.value,
                        model.value,
                        speakers.value,
                        dialog,
                    ),
                ).props("color=primary")
                ui.button(
                    "Cancel",
                    icon="cancel",
                ).on("click", lambda: dialog.close())

        dialog.open()


def table_delete(selected_rows: list) -> None:
    """
    Handle the click event on the Delete button.
    """

    if not selected_rows:
        ui.notify("Error: No files selected", type="negative", position="top")
        return

    with ui.dialog() as dialog:
        with ui.card().style(
            "background-color: white; align-self: center; border: 0; width: 100%;"
        ):
            ui.label("Are you sure you want to delete the selected files?").classes(
                "text-h6 q-mb-md text-primary"
            )
            with ui.row().classes("justify-end"):
                ui.button(
                    "Delete",
                    icon="delete",
                    on_click=lambda: __delete_files(selected_rows, dialog),
                ).props("color=negative")
                ui.button(
                    "Cancel",
                    icon="cancel",
                ).on("click", lambda: dialog.close())

        dialog.open()


def __delete_files(rows: list, dialog: ui.dialog) -> bool:
    try:
        for row in rows:
            uuid = row["uuid"]
            response = requests.delete(
                f"{API_URL}/api/v1/transcriber/{uuid}",
                headers=get_auth_header(),
            )
            response.raise_for_status()
        ui.notify("Files deleted successfully", type="positive", position="top")
    except requests.exceptions.RequestException as e:
        ui.notify(
            f"Error: Failed to delete files: {str(e)}", type="negative", position="top"
        )
        return False

    dialog.close()


def start_transcription(
    rows: list, language: str, model: str, speakers: str, dialog: ui.dialog
) -> None:
    # Get selected values
    selected_language = language
    selected_model = model

    try:
        for row in rows:
            uuid = row["uuid"]

            try:
                response = requests.put(
                    f"{API_URL}/api/v1/transcriber/{uuid}",
                    json={
                        "language": f"{selected_language}",
                        "model": f"{selected_model}",
                        "speakers": int(speakers),
                        "status": "pending",
                    },
                    headers=get_auth_header(),
                )
                response.raise_for_status()
            except requests.exceptions.RequestException:
                ui.notify(
                    "Error: Failed to start transcription.",
                    type="negative",
                    position="top",
                )
                return

        dialog.close()

    except Exception as e:
        ui.notify(f"Error: {str(e)}", type="negative", position="top")
