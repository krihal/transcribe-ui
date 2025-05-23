import requests
from nicegui import ui
from utils.common import page_init, API_URL, get_auth_header

# Set up global state
expanded_row = None  # Track which row is currently expanded
edit_inputs = {}  # Store input elements for the currently edited row
data = []
edit_panel = None
video = None
table = None
table_page = None


def format_time(time_str):
    """
    Format the time for display
    """
    
    parts = time_str.split(",")
    if len(parts) == 2:
        return f"{parts[0]}<span class='text-gray-500'>,{parts[1]}</span>"
    return time_str


def is_valid_time(time_str):
    """
    Validate the SRT timestamp format
    """
    
    try:
        parts = time_str.split(",")
        if len(parts) != 2:
            return False

        time_parts = parts[0].split(":")
        if len(time_parts) != 3:
            return False

        hours, minutes, seconds = map(int, time_parts)
        milliseconds = int(parts[1])

        return (
            0 <= hours <= 99
            and 0 <= minutes <= 59
            and 0 <= seconds <= 59
            and 0 <= milliseconds <= 999
        )
    except Exception:
        return False


def calculate_duration(start_time, end_time):
    """
    Calculate duration between two timestamps
    """
    try:
        # Parse start time
        start_parts = start_time.split(",")
        start_time_parts = start_parts[0].split(":")
        start_h, start_m, start_s = map(int, start_time_parts)
        start_ms = int(start_parts[1])
        start_total_ms = ((start_h * 3600) + (start_m * 60) + start_s) * 1000 + start_ms

        # Parse end time
        end_parts = end_time.split(",")
        end_time_parts = end_parts[0].split(":")
        end_h, end_m, end_s = map(int, end_time_parts)
        end_ms = int(end_parts[1])
        end_total_ms = ((end_h * 3600) + (end_m * 60) + end_s) * 1000 + end_ms

        # Calculate difference
        diff_ms = end_total_ms - start_total_ms

        # Format result
        if diff_ms < 0:
            return "Invalid (end before start)"

        diff_s, ms = divmod(diff_ms, 1000)
        diff_m, diff_s = divmod(diff_s, 60)

        if diff_m > 0:
            return f"{diff_m}m {diff_s}s {ms}ms"
        else:
            return f"{diff_s}s {ms}ms"
    except Exception:
        return "Invalid format"


@ui.refreshable
def render_data_table():
    """
    Render the data table with expandable rows
    """
    global expanded_row, edit_inputs, data, table

    with ui.card().classes("w-full no-shadow no-border"):
        # No data message
        if len(data) == 0:
            with ui.row().classes("w-full p-8 text-center text-gray-500"):
                ui.label('No subtitle entries. Click "Add New" to create one.').classes(
                    "text-lg"
                )

        with ui.row().classes("w-full items-center justify-between p-2"):
            table = (
                ui.table(
                    rows=data,
                    columns=[
                        {
                            "name": "index",
                            "label": "Index",
                            "align": "left",
                            "field": "index",
                        },
                        {
                            "name": "start_time",
                            "label": "Start Time",
                            "align": "left",
                            "field": "start_time",
                        },
                        {
                            "name": "end_time",
                            "label": "End Time",
                            "align": "left",
                            "field": "end_time",
                        },
                        {
                            "name": "text",
                            "label": "Text",
                            "align": "left",
                            "field": "text",
                            "style": "text-wrap: wrap; heigh: auto; white-space: pre-line;",
                        },
                    ],
                    row_key="index",
                )
                .classes("w-full max-h-50")
                .style(
                    "width: 100%; height: calc(100vh - 130px); overflow: auto; box-shadow: none;"
                )
            )

            with table.add_slot("top-right"):
                with ui.row().classes("items-center gap-2"):
                    with ui.input(placeholder="Search").props("type=search").bind_value(
                        table, "filter"
                    ).add_slot("append"):
                        ui.icon("search")

            table.on("rowClick", lambda e: show_edit_panel(e))


def save_edit(index, text, start_time, end_time):
    """
    Save the edited data
    """
    global edit_inputs, expanded_row, data

    # Validate time formats
    if not is_valid_time(start_time) or not is_valid_time(end_time):
        ui.notify("Invalid time format! Use HH:MM:SS,mmm", type="negative")
        return

    # Find and update item
    for item in data:
        if item["index"] == index:
            item["start_time"] = start_time
            item["end_time"] = end_time
            item["text"] = text
            break

    ui.notify("Changes saved successfully", type="positive")
    render_data_table.refresh()


def delete_entry(index):
    """
    Delete an entry from the data
    """
    global expanded_row, edit_inputs, data

    # Find the item to remove
    for i, item in enumerate(data):
        if item["index"] == index:
            data.pop(i)
            break

    # Reset expanded row if it was deleted
    if expanded_row == index:
        expanded_row = None

    # Remove from edit inputs if present
    if index in edit_inputs:
        del edit_inputs[index]

    # Re-index remaining items
    for i, item in enumerate(data):
        item["index"] = i + 1

    ui.notify("Entry deleted", type="info")
    render_data_table.refresh()


def add_new_entry(index: int):
    """
    Add a new entry to the data
    """
    global data, expanded_row, edit_inputs

    if index == -1:
        index = 0

    # Get default start time from the last entry end time if available
    default_start = data[-1]["end_time"] if data else "00:00:00,000"

    # Create new entry
    new_entry = {
        "index": None,
        "start_time": default_start,
        "end_time": default_start,
        "text": "New subtitle text",
    }

    # Add to data to index position in list
    data.insert(index, new_entry)

    # Auto-expand and edit the new entry
    expanded_row = index
    edit_inputs[index] = {}

    # Set new index for all items
    for i, item in enumerate(data):
        item["index"] = i

    # Sort data by index
    data = sorted(data, key=lambda d: d["index"])

    expanded_row = None

    render_data_table.refresh()


def parse_srt(data):
    """
    Parse SRT data into a structured format
    """
    parsed_data = []
    lines = data.splitlines()

    for i in range(0, len(lines), 4):
        if i + 3 < len(lines):
            index = int(lines[i])
            time_range = lines[i + 1].split(" --> ")
            start_time = time_range[0].strip()
            end_time = time_range[1].strip()
            text = lines[i + 2].strip()

            parsed_data.append(
                {
                    "index": index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": text,
                }
            )

    return parsed_data

def seek_video(row: dict) -> None:
    """
    Seek the video to the specified start time
    """

    global video

    start_time = row["start_time"].split(",")[0]
    start_time_parts = start_time.split(":")
    start_time_seconds = (
        int(start_time_parts[0]) * 3600
        + int(start_time_parts[1]) * 60
        + int(start_time_parts[2])
    )

    video.seek(start_time_seconds)




def show_edit_panel(event) -> None:
    """
    Show the edit panel for the selected row.
    """
    edit_panel.style("display: block;")
    edit_panel.clear()

    row = event.args[1]

    seek_video(row)

    with edit_panel as edit:
        edit.classes("w-full p-4 bg-gray-100")
        ui.label(f"Edit Subtitle {row["index"]}").classes("text-h6")

        with ui.row().classes("w-full"):
            start_time = ui.input(
                label="Start Time",
                value=row["start_time"],
                placeholder="HH:MM:SS,mmm",
            ).classes("col-3")
            end_time = ui.input(
                label="End Time",
                value=row["end_time"],
                placeholder="HH:MM:SS,mmm",
            ).classes("col-3")

        with ui.row():
            text = ui.textarea(
                label="Text",
                value=row["text"],
                placeholder="Subtitle text",
            ).classes("w-full")

        # Row a little bit further down
        with ui.row().style("margin-top: 20px;"):
            ui.button(
                icon="add_circle",
                on_click=lambda: add_new_entry(row["index"] + 1),
            ).props("color=primary")
            ui.button(
                icon="delete",
                on_click=lambda: delete_entry(row["index"]),
            ).props("color=negative")            
            ui.button(
                icon="save",
                on_click=lambda: save_edit(row["index"], text.value, start_time.value, end_time.value),
            ).props("color=primary")


def export_srt() -> None:
    """
    Export data in SRT format
    """
    srt_content = ""
    for item in sorted(data, key=lambda x: x["index"]):
        srt_content += f"{item['index']}\n"
        srt_content += f"{item['start_time']} --> {item['end_time']}\n"
        srt_content += f"{item['text']}\n\n"

    ui.download("subtitles.srt", srt_content)
    ui.notify("SRT file ready for download", type="positive")


def create() -> None:
    @ui.page("/srt")
    def result(uuid: str, filename: str) -> None:
        """
        Display the result of the transcription job.
        """
        global data, edit_panel, video, table, table_page

        page_init()

        try:
            response = requests.get(f"{API_URL}/api/v1/transcriber/{uuid}/result", headers=get_auth_header())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            ui.notify(f"Error: Failed to get result: {e}")
            return

        data = response.content.decode()
        data = parse_srt(data)

        # Create a toolbar with buttons on the top and the text under button icon
        with ui.row().classes("justify-between items-center"):
            ui.button("Files", icon="folder").on_click(
                lambda: ui.navigate.to("/home")
            ).style("width: 150px;")
            ui.button(
                "Export SRT",
                icon="save",
                on_click=export_srt,
            ).style("width: 150px;")

        # Split screen in 2/3 and 1/3
        with ui.splitter(value=70) as splitter:
            with splitter.before:
                with ui.card().classes("w-full"):
                    render_data_table()

            with splitter.after:
                # Add transcription information
                ui.label("Transcription Information").classes("text-h6 q-mb-md")
                ui.separator()
                video = ui.video(
                    f"{API_URL}/static/{uuid}",
                    autoplay=False,
                    controls=True,
                    muted=False,
                ).style("width: 75%; align-self: center;")

                ui.separator()
                with ui.row() as edit_panel:
                    edit_panel.style("display: none;")
