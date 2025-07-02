import json
from nicegui import ui
from typing import Any
from typing import Dict
from typing import List
import re


class TranscriptSegment:
    def __init__(self, speaker: str, text: str, start: float = 0.0, end: float = 0.0):
        self.speaker = speaker
        self.text = text
        self.start = start
        self.end = end
        self.duration = end - start
        self.is_selected = False
        self.is_highlighted = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
        }


class TranscriptEditor:
    def __init__(self, data: str):
        self.original_data = json.loads(data)
        self.segments: List[TranscriptSegment] = []
        self.speakers = set()
        self.container = None
        self.parse_segments()
        self.video_player = None
        self.autoscroll = False
        self.selected_segment: TranscriptSegment = None

        # Search functionality attributes
        self.search_term = ""
        self.case_sensitive = False
        self.search_results = []
        self.current_search_index = -1
        self.search_info_label = None

    async def select_segment_from_video(self, autoscroll: bool) -> None:
        if not autoscroll:
            return

        self.autoscroll = autoscroll

        current_time = await ui.run_javascript(
            """(() => { return document.querySelector("video").currentTime })()"""
        )

        caption = self.get_segment_from_time(current_time)

        if caption:
            if self.selected_segment != caption:
                self.select_segment(caption, None)

    def select_segment(self, caption: TranscriptSegment, action_col: ui.column) -> None:
        if self.selected_segment:
            self.selected_segment.is_selected = False

        caption.is_selected = True
        self.selected_segment = caption

        if self.video_player:
            self.video_player.seek(caption.start)

        if action_col:
            action_col.visible = True

        self.refresh_ui()

    def get_segment_from_time(self, time: float) -> TranscriptSegment:
        for segment in self.segments:
            if segment.start <= time <= segment.end:
                return segment

        return None

    def set_video_player(self, player) -> None:
        self.video_player = player

    def parse_segments(self):
        if not self.original_data.get("segments"):
            return

        raw_segments = self.original_data["segments"]

        if not raw_segments:
            return

        concatenated = []
        current = raw_segments[0].copy()

        for segment in raw_segments[1:]:
            if segment["speaker"] == current["speaker"]:
                current["text"] += " " + segment["text"]
                current["end"] = segment["end"]
                current["duration"] = current["end"] - current["start"]
            else:
                concatenated.append(current)
                current = segment.copy()

        concatenated.append(current)

        for seg in concatenated:
            if seg.get("text", "").strip():
                self.segments.append(
                    TranscriptSegment(
                        speaker=seg["speaker"],
                        text=seg["text"],
                        start=seg.get("start", 0.0),
                        end=seg.get("end", 0.0),
                    )
                )
                self.speakers.add(seg["speaker"])

    def add_segment(self, speaker: str, text: str, position: int = None):
        if position is None:
            position = len(self.segments)

        new_segment = TranscriptSegment(speaker, text)

        self.segments.insert(position, new_segment)
        self.speakers.add(speaker)
        self.refresh_ui()

    def remove_segment(self, index: int):
        if 0 <= index < len(self.segments):
            self.segments.pop(index)
            self.refresh_ui()

    def update_segment(self, index: int, speaker: str = None, text: str = None):
        if 0 <= index < len(self.segments):
            if speaker is not None:
                self.segments[index].speaker = speaker
                self.speakers.add(speaker)
            if text is not None:
                self.segments[index].text = text

    def move_segment(self, from_index: int, to_index: int):
        if 0 <= from_index < len(self.segments) and 0 <= to_index < len(self.segments):
            segment = self.segments.pop(from_index)

            self.segments.insert(to_index, segment)
            self.refresh_ui()

    def get_export_data(self) -> str:
        result = []

        for segment in self.segments:
            result.append(
                f"{segment.start} -> {segment.end}, {segment.speaker}: {segment.text}"
            )

        return "\n\n".join(result)

    def get_json_data(self) -> str:
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "speaker_count": len(self.speakers),
            "full_transcription": " ".join(seg.text for seg in self.segments),
        }

    def refresh_ui(self):
        if self.container:
            self.container.clear()
            with self.container:
                self._render_segments()

    # Search functionality methods
    def search_captions(self, search_term: str) -> None:
        """Search for text in captions and highlight results."""
        self.search_term = search_term.strip()
        self.search_results = []
        self.current_search_index = -1

        # Clear previous highlights
        for segment in self.segments:
            segment.is_highlighted = False

        if not self.search_term:
            self._update_search_info()
            self.refresh_ui()
            return

        # Perform search
        search_pattern = self.search_term
        if not self.case_sensitive:
            search_pattern = search_pattern.lower()

        for i, segment in enumerate(self.segments):
            text_to_search = segment.text
            if not self.case_sensitive:
                text_to_search = text_to_search.lower()

            if search_pattern in text_to_search:
                self.search_results.append(i)
                segment.is_highlighted = True

        # Navigate to first result if any found
        if self.search_results:
            self.current_search_index = 0
            self._scroll_to_current_result()

        self._update_search_info()
        self.refresh_ui()

    def navigate_search_results(self, direction: int) -> None:
        """Navigate through search results."""
        if not self.search_results:
            return

        self.current_search_index = (self.current_search_index + direction) % len(
            self.search_results
        )
        self._scroll_to_current_result()
        self._update_search_info()

    def _scroll_to_current_result(self) -> None:
        """Scroll to and select the current search result."""
        if self.search_results and 0 <= self.current_search_index < len(
            self.search_results
        ):
            segment_index = self.search_results[self.current_search_index]
            segment = self.segments[segment_index]
            self.select_segment(segment, None)

    def _update_search_info(self) -> None:
        """Update the search information label."""
        if self.search_info_label:
            if not self.search_term:
                self.search_info_label.text = ""
            elif not self.search_results:
                self.search_info_label.text = "No results found"
            else:
                current = self.current_search_index + 1
                total = len(self.search_results)
                self.search_info_label.text = f"{current} of {total} results"

    def replace_in_current_caption(self, replacement: str) -> None:
        """Replace the search term in the currently selected caption."""
        if not self.search_term or not self.selected_segment:
            ui.notify("No search term or selected segment", type="warning")
            return

        segment = self.selected_segment
        flags = re.IGNORECASE if not self.case_sensitive else 0

        # Check if the selected segment contains the search term
        if re.search(re.escape(self.search_term), segment.text, flags):
            # Perform replacement
            new_text = re.sub(
                re.escape(self.search_term), replacement, segment.text, flags=flags
            )

            # Update the segment
            segment_index = self.segments.index(segment)
            self.update_segment(segment_index, text=new_text)

            # Refresh search results
            self.search_captions(self.search_term)

            ui.notify("Replacement completed", type="positive")
        else:
            ui.notify("Search term not found in selected segment", type="warning")

    def replace_all(self, replacement: str) -> None:
        """Replace all occurrences of the search term."""
        if not self.search_term:
            ui.notify("No search term specified", type="warning")
            return

        replacement_count = 0
        flags = re.IGNORECASE if not self.case_sensitive else 0

        for i, segment in enumerate(self.segments):
            if re.search(re.escape(self.search_term), segment.text, flags):
                new_text = re.sub(
                    re.escape(self.search_term), replacement, segment.text, flags=flags
                )
                self.update_segment(i, text=new_text)
                replacement_count += 1

        if replacement_count > 0:
            # Refresh search results
            self.search_captions(self.search_term)
            ui.notify(f"Replaced {replacement_count} occurrences", type="positive")
        else:
            ui.notify("No occurrences found to replace", type="warning")

    def _create_segment_ui(self, segment: TranscriptSegment, index: int):
        segment_class = "cursor-pointer border-0 transition-all duration-200 w-full"

        if segment.is_selected:
            segment_class += " border-blue-500 bg-blue-50 shadow-none"
        elif segment.is_highlighted:
            segment_class += " border-yellow-400 bg-yellow-50 hover:border-yellow-500"
        else:
            segment_class += " hover:border-gray-300 hover:shadow-md shadow-none"

        with ui.column().classes("w-full mb-4 p-4"):
            with ui.row().classes("w-full") as segment_row:
                segment_row.classes(segment_class)

                with ui.button(icon="add").props("flat round"):
                    with ui.menu():
                        with ui.column():
                            new_speaker_input = ui.input("New Speaker")
                            ui.button(
                                "Add",
                                on_click=lambda: self._add_new_speaker(
                                    new_speaker_input.value,
                                    speaker_select,
                                    index,
                                ),
                            )

                with ui.column().classes("flex-grow"):
                    with ui.row().classes("items-center gap-2 w-32"):
                        speaker_select = ui.select(
                            options=list(self.speakers),
                            value=segment.speaker,
                            with_input=True,
                        ).style("font-family: verdana; font-size: 10px;")
                        speaker_select.on_value_change(
                            lambda e, idx=index: self.update_segment(
                                idx, speaker=e.value
                            )
                        )

                with ui.row().classes("items-center w-2/3") as text_row:
                    ui.label(f"{segment.start:.2f} - {segment.end:.2f}").classes(
                        "text-sm text-gray-500"
                    ).classes(segment_class)

                    text_editor = (
                        ui.editor(value=segment.text, placeholder="Enter text...")
                        .style("font-family: verdana; border: 0; width: 100%;")
                        .props("min-height=0")
                        .classes(segment_class)
                    )
                    text_editor.on_value_change(
                        lambda e, idx=index: self.update_segment(idx, text=e.value)
                    )

                    text_row.on(
                        "click",
                        lambda e, idx=index: (
                            self.select_segment(segment, action_col),
                        ),
                    )
                with ui.column().classes("flex-shrink-0 gap-1") as action_col:
                    action_col.visible = segment.is_selected

                    ui.button(
                        icon="keyboard_arrow_up",
                        on_click=lambda idx=index: self.move_segment(
                            idx, max(0, idx - 1)
                        ),
                    ).props("flat round").set_enabled(index > 0)
                    ui.button(
                        icon="keyboard_arrow_down",
                        on_click=lambda idx=index: self.move_segment(
                            idx, min(len(self.segments) - 1, idx + 1)
                        ),
                    ).props("flat round").set_enabled(index < len(self.segments) - 1)
                    ui.button(
                        icon="add_circle",
                        color="positive",
                        on_click=lambda idx=index: self._show_insert_dialog(idx),
                    ).props("flat round")
                    ui.button(
                        icon="delete",
                        color="negative",
                        on_click=lambda idx=index: self._confirm_delete(idx),
                    ).props("flat round")

    def _add_new_speaker(self, speaker_name: str, speaker_select, segment_index: int):
        if speaker_name and speaker_name not in self.speakers:
            self.speakers.add(speaker_name)
            speaker_select.options = list(self.speakers)
            speaker_select.value = speaker_name
            self.update_segment(segment_index, speaker=speaker_name)

    def _confirm_delete(self, index: int):
        with ui.dialog().props("persistent") as dialog, ui.card():
            ui.label("Are you sure you want to delete this segment?")
            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Delete",
                    color="negative",
                    on_click=lambda: (self.remove_segment(index), dialog.close()),
                )

        dialog.open()

    def _show_insert_dialog(self, position: int):
        with ui.dialog().props("persistent") as dialog:
            with ui.card().classes("w-full max-w-2xl"):
                ui.label("Insert New Segment")

                speaker_input = ui.select(
                    options=list(self.speakers), label="Speaker"
                ).classes("w-full")

                text_input = ui.textarea("Text").classes("w-full")

                position_select = ui.select(
                    options=["Before this segment", "After this segment"],
                    value="After this segment",
                    label="Position",
                )

                with ui.row():
                    ui.button("Cancel", on_click=dialog.close)
                    ui.button(
                        "Insert",
                        color="positive",
                        on_click=lambda: self._do_insert(
                            dialog,
                            speaker_input.value,
                            text_input.value,
                            position,
                            position_select.value,
                        ),
                    )
            dialog.open()

    def _do_insert(
        self, dialog, speaker: str, text: str, base_position: int, position_type: str
    ):
        if not speaker or not text:
            ui.notify("Please provide both speaker and text", type="warning")
            return

        insert_pos = (
            base_position
            if position_type == "Before this segment"
            else base_position + 1
        )

        self.add_segment(speaker, text, insert_pos)

        dialog.close()

        ui.notify("Segment inserted successfully", type="positive")

    def _render_segments(self):
        if not self.segments:
            ui.label("No segments found").classes("text-center text-gray-500")
            return

        for i, segment in enumerate(self.segments):
            self._create_segment_ui(segment, i)

    def render(self):
        ui.add_css(
            """
            .q-textarea .q-field__control { 
                font-family: 'Courier New', monospace; 
                font-size: 14px; 
            }
        """
        )

        self.container = ui.column().classes("w-full")

        with self.container:
            self._render_segments()

    def _show_add_segment_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Add New Segment")

            speaker_input = ui.select(
                options=list(self.speakers), label="Speaker"
            ).classes("w-full")

            new_speaker_input = ui.input("New Speaker").classes("w-full")
            text_input = ui.textarea("Text").classes("w-full")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Add",
                    color="positive",
                    on_click=lambda: (
                        self.add_segment(
                            speaker_input.value or new_speaker_input.value,
                            text_input.value,
                        ),
                        dialog.close(),
                        ui.notify("Segment added successfully", type="positive"),
                    ),
                )
        dialog.open()

    def create_search_panel(self) -> None:
        """
        Create the search panel UI.
        """

        with ui.expansion("Search & Replace").classes("w-full").style(
            "background-color: #eff4fb;"
        ):
            with ui.row().classes("w-full gap-2 mb-2"):
                search_input = (
                    ui.input(
                        placeholder="Search in captions...", value=self.search_term
                    )
                    .classes("flex-1")
                    .props("outlined dense")
                )

                ui.button("Search", icon="search", color="primary").props("dense").on(
                    "click", lambda: self.search_captions(search_input.value)
                )

                ui.checkbox("Case sensitive").bind_value_to(self, "case_sensitive").on(
                    "update:model-value",
                    lambda: self.search_captions(search_input.value)
                    if self.search_term
                    else None,
                )

            # Search navigation
            with ui.row().classes("w-full gap-2 mb-2"):
                ui.button("Previous", icon="keyboard_arrow_up", color="grey").props(
                    "dense flat"
                ).on("click", lambda: self.navigate_search_results(-1))
                ui.button("Next", icon="keyboard_arrow_down", color="grey").props(
                    "dense flat"
                ).on("click", lambda: self.navigate_search_results(1))

                self.search_info_label = ui.label("").classes(
                    "text-sm text-gray-600 self-center"
                )

            # Replace functionality
            with ui.row().classes("w-full gap-2"):
                replace_input = (
                    ui.input(
                        placeholder="Replace with...",
                    )
                    .classes("flex-1")
                    .props("outlined dense")
                )

                ui.button("Replace Current", color="orange").props("dense").on(
                    "click",
                    lambda: self.replace_in_current_caption(replace_input.value),
                )
                ui.button("Replace All", color="red").props("dense").on(
                    "click", lambda: self.replace_all(replace_input.value)
                )

            # Enter key support for search
            search_input.on(
                "keydown.enter", lambda: self.search_captions(search_input.value)
            )

    def export(self, txt_format: str, filename: str):
        """
        Export the transcript in the specified format.
        """
        filename = filename.rsplit(".", 1)[0]

        match txt_format:
            case "txt":
                content = self.get_export_data()
            case "json":
                content = json.dumps(self.get_json_data(), indent=4, ensure_ascii=False)
            case _:
                ui.notify(f"Unsupported format: {txt_format}", type="negative")
                return

        ui.download(content.encode(), filename=f"{filename}.{txt_format}")
        ui.notify("File exported successfully", type="positive")
