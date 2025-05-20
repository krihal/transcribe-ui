import requests
from nicegui import ui, app
from utils.common import API_URL, page_init


def save_file(data: str, filename: str) -> None:
    """
    Save the edited content to a file.
    """

    ui.download(filename, data)


def txt_editor(data) -> ui.editor:
    """
    Create a text editor with the given data.
    """
    editor = (
        ui.editor(
            value=data,
        )
        .style(
            "width: 100%; height: calc(100vh - 100px); white-space: pre-wrap; margin-top: 20px;"
        )
        .classes("no-border no-shadow")
    )

    return editor


def create() -> None:
    """
    Create the text page.
    """

    @ui.page("/txt")
    def result(uuid: str, filename: str) -> None:
        """
        Display the result of the transcription job.
        """

        app.add_static_files(url_path="/static", local_directory="static/")
        response = requests.get(f"{API_URL}/api/v1/transcriber/{uuid}/result")

        if response.status_code != 200:
            ui.notify("Error: Failed to get result")
            return

        data = response.content.decode("utf-8")

        page_init()

        # Create a toolbar with buttons on the top and the text under button icon
        with ui.row().classes("justify-between items-center"):
            ui.button("Files", icon="folder").on_click(
                lambda: ui.navigate.to("/home")
            ).style("width: 150px;")
            ui.button(
                "Export",
                icon="save",
                on_click=lambda: save_file(data, filename),
            ).style("width: 150px;")

        txt_editor(data)
