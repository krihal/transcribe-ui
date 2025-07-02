import requests

from nicegui import ui
from utils.common import API_URL
from utils.common import get_auth_header
from utils.common import page_init
from utils.video import create_video_proxy
from utils.transcript import TranscriptEditor
from utils.srt import SRTEditor

create_video_proxy()


def export_file(data: str, filename: str) -> None:
    ui.download.content(data, filename)


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


def save_file(job_id: str, data: str) -> None:
    data["format"] = "json"
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    requests.put(
        f"{API_URL}/api/v1/transcriber/{job_id}/result",
        headers=headers,
        json=data,
    )

    ui.notify(
        "File saved successfully",
        type="positive",
        position="bottom",
        icon="check_circle",
    )


def create() -> None:
    @ui.page("/txt")
    def result(uuid: str, filename: str, language: str, model: str) -> None:
        page_init()

        try:
            response = requests.get(
                f"{API_URL}/api/v1/transcriber/{uuid}/result/txt",
                headers=get_auth_header(),
            )
            response_srt = requests.get(
                f"{API_URL}/api/v1/transcriber/{uuid}/result/srt",
                headers=get_auth_header(),
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            ui.notify(f"Error: Failed to get result: {e}", type="negative")
            return

        data = response.json()
        data_srt = response_srt.json()
        editor = TranscriptEditor(data["result"])
        editor_srt = SRTEditor()

        async def select_from_video(autoscroll: bool) -> None:
            if autoscroll:
                await editor_srt.select_caption_from_video(autoscroll)
                await editor.select_segment_from_video(autoscroll)

        ui.add_css(".q-editor__toolbar { display: none }")

        with ui.splitter(value=60).classes("w-full h-screen") as splitter:
            with splitter.before:
                with ui.tabs().classes("w-full") as tabs:
                    srt = ui.tab("SRT")
                    transcript = ui.tab("Transcript")

                with ui.tab_panels(tabs, value=srt).classes("w-full h-full"):
                    with ui.tab_panel(srt).classes("w-full h-full"):
                        with ui.row().classes("justify-between items-center mb-4"):
                            with ui.button("Save", icon="save").style(
                                "width: 150px;"
                            ).props("color=primary flat") as save:
                                save.on_click(
                                    lambda: save_file(uuid, editor.get_json_data())
                                )

                            with ui.dropdown_button("Export", icon="share").props(
                                "color=primary flat"
                            ):
                                export_button_srt = ui.button(
                                    "Export as SRT", icon="share"
                                ).style("width: 150px;")
                                export_button_srt.props("color=primary flat")
                                export_button_srt.on(
                                    "click", lambda: editor_srt.export("srt", filename)
                                )

                                export_button_vtt = ui.button(
                                    "Export as VTT", icon="share"
                                ).style("width: 150px;")
                                export_button_vtt.props("color=primary flat")
                                export_button_vtt.on(
                                    "click", lambda: editor_srt.export("vtt", filename)
                                )

                            validate = ui.button("Validate", icon="check").props(
                                "color=primary flat"
                            )
                            validate.on("click", lambda: editor_srt.validate_captions())

                        editor_srt.create_search_panel()
                        with ui.scroll_area().style("height: calc(100vh - 200px);"):
                            editor_srt.main_container = ui.column().classes(
                                "w-full h-full"
                            )
                        editor_srt.parse_srt(data_srt["result"])
                        editor_srt.refresh_display()

                    with ui.tab_panel(transcript).classes("w-full h-full"):
                        with ui.row().classes("justify-between items-center mb-4"):
                            with ui.button("Save", icon="save").style(
                                "width: 150px;"
                            ).props("color=primary flat") as save:
                                save.on_click(
                                    lambda: save_file(uuid, editor.get_json_data())
                                )

                            with ui.dropdown_button("Export", icon="share").props(
                                "color=primary flat"
                            ):
                                export_button_txt = ui.button(
                                    "Export as TXT", icon="share"
                                ).style("width: 150px;")
                                export_button_txt.props("color=primary flat")
                                export_button_txt.on(
                                    "click", lambda: editor.export("txt", filename)
                                )

                                export_button_json = ui.button(
                                    "Export as JSON", icon="share"
                                ).style("width: 150px;")
                                export_button_json.props("color=primary flat")
                                export_button_json.on(
                                    "click", lambda: editor.export("json", filename)
                                )

                        editor.create_search_panel()
                        with ui.scroll_area().style("height: calc(100vh - 200px);"):
                            editor.render()

            with splitter.after:
                with ui.card().classes("w-full h-full"):
                    autoscroll = ui.switch("Autoscroll")
                    ui.label("Video Preview").classes("text-lg font-bold mb-4")
                    video = ui.video(
                        f"/video/{uuid}",
                        controls=True,
                        autoplay=False,
                        loop=False,
                    ).classes("w-full")

                    editor.set_video_player(video)
                    editor_srt.set_video_player(video)
                    video.on(
                        "timeupdate",
                        lambda: select_from_video(autoscroll.value),
                    )

                    video.style("align-self: flex-start;")

                    ui.separator()
                    ui.html(f"<b>UUID:</b> {uuid}").classes("text-sm")
                    ui.html(f"<b>Filename:</b> {filename}").classes("text-sm")
                    ui.html(f"<b>Language:</b> {language}").classes("text-sm")
                    ui.html(f"<b>Model:</b> {model}").classes("text-sm")
