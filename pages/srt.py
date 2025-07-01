import requests

from nicegui import ui
from utils.common import API_URL
from utils.common import get_auth_header
from utils.common import page_init
from utils.video import create_video_proxy
from utils.srt import SRTEditor

create_video_proxy()


def save_srt(job_id: str, data: str, editor: SRTEditor) -> None:
    jsondata = {"format": "srt", "data": data}
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    requests.put(
        f"{API_URL}/api/v1/transcriber/{job_id}/result",
        headers=headers,
        json=jsondata,
    )

    ui.notify(
        "File saved successfully",
        type="positive",
        position="bottom",
        icon="check_circle",
    )


def create() -> None:
    @ui.page("/srt")
    def result(uuid: str, filename: str, model: str, language: str) -> None:
        """
        Display the result of the transcription job.
        """
        page_init()

        try:
            response = requests.get(
                f"{API_URL}/api/v1/transcriber/{uuid}/result/srt",
                headers=get_auth_header(),
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            ui.notify(f"Error: Failed to get result: {e}")
            return

        with ui.row():

            def export(srt_format: str):
                if srt_format == "srt":
                    srt_content = editor.export_srt()
                elif srt_format == "vtt":
                    srt_content = editor.export_vtt()

                ui.download(srt_content.encode(), filename=f"{filename}.{srt_format}")
                ui.notify("File exported successfully", type="positive")

            with ui.button("Save", icon="save").style("width: 150px;") as save_button:
                save_button.on(
                    "click",
                    lambda: save_srt(uuid, editor.export_srt(), editor),
                )
                save_button.props("color=primary flat")

            with ui.dropdown_button("Export", icon="share").props("color=primary flat"):
                export_button_srt = ui.button("Export as SRT", icon="share").style(
                    "width: 150px;"
                )
                export_button_srt.props("color=primary flat")
                export_button_srt.on("click", lambda: export("srt"))

                export_button_vtt = ui.button("Export as VTT", icon="share").style(
                    "width: 150px;"
                )
                export_button_vtt.props("color=primary flat")
                export_button_vtt.on("click", lambda: export("vtt"))

            with ui.button("Validate", icon="check").props(
                "color=primary flat"
            ) as validate_button:
                validate_button.on(
                    "click",
                    lambda: editor.validate_captions(),
                )

        ui.separator()

        with ui.splitter(value=60).classes("w-full h-full") as splitter:
            with splitter.before:
                with ui.card().classes("w-full h-full"):
                    editor = SRTEditor()
                    editor.create_search_panel()
                    with ui.scroll_area().style("height: calc(100vh - 200px);"):
                        editor.main_container = ui.column().classes("w-full h-full")
                    editor.parse_srt(data["result"])
                    editor.refresh_display()
                with splitter.after:
                    with ui.card().classes("w-full h-full"):
                        autoscroll = ui.switch("Autoscroll")
                        ui.label("Video Preview").classes("text-lg font-bold mb-4")
                        video = ui.video(
                            f"/video/{uuid}",
                            controls=True,
                            autoplay=False,
                            loop=False,
                        ).classes("w-full h-full")
                        editor.set_video_player(video)
                        video.on(
                            "timeupdate",
                            lambda: editor.select_caption_from_video(autoscroll.value),
                        )
                        ui.separator()
                        ui.html(f"<b>UUID:</b> {uuid}").classes("text-sm")
                        ui.html(f"<b>Filename:</b> {filename}").classes("text-sm")
                        ui.html(f"<b>Language:</b> {language}").classes("text-sm")
                        ui.html(f"<b>Model:</b> {model}").classes("text-sm")
                        html_wpm = ui.html(
                            f"<b>Words per minute:</b> {editor.get_words_per_minute():.2f}"
                        ).classes("text-sm")
                        editor.set_words_per_minute_element(html_wpm)
