import requests
from nicegui import ui, app
from utils.common import page_init, API_URL, get_auth_header
from typing import List, Optional
import re
from fastapi.responses import Response
from fastapi import Request

# Set up global state
expanded_row = None  # Track which row is currently expanded
edit_inputs = {}  # Store input elements for the currently edited row
data = []
edit_panel = None
video = None
table = None
table_page = None

#!/usr/bin/env python3
"""
Advanced SRT Subtitle Editor using NiceGUI
Features: Split, Add, Remove captions with intuitive UI and Search functionality
"""


class SRTCaption:
    def __init__(self, index: int, start_time: str, end_time: str, text: str):
        self.index = index
        self.start_time = start_time
        self.end_time = end_time
        self.text = text
        self.is_selected = False
        self.is_highlighted = False  # For search highlighting

    def to_srt_format(self) -> str:
        return f"{self.index}\n{self.start_time} --> {self.end_time}\n{self.text}\n"

    def get_start_seconds(self) -> float:
        """Convert timestamp to seconds for calculations"""
        time_parts = self.start_time.replace(",", ".").split(":")
        hours = float(time_parts[0])
        minutes = float(time_parts[1])
        seconds = float(time_parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def get_end_seconds(self) -> float:
        """Convert timestamp to seconds for calculations"""
        time_parts = self.end_time.replace(",", ".").split(":")
        hours = float(time_parts[0])
        minutes = float(time_parts[1])
        seconds = float(time_parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def matches_search(self, search_term: str, case_sensitive: bool = False) -> bool:
        """Check if caption matches search term"""
        if not search_term:
            return False

        text = self.text if case_sensitive else self.text.lower()
        term = search_term if case_sensitive else search_term.lower()
        return term in text


class SRTEditor:
    def __init__(self):
        self.captions: List[SRTCaption] = []
        self.selected_caption: Optional[SRTCaption] = None
        self.caption_cards = {}
        self.main_container = None
        self.search_term = ""
        self.search_results = []
        self.current_search_index = 0
        self.case_sensitive = False
        self.search_container = None
        self.__video_player = None

    def set_video_player(self, player) -> None:
        self.__video_player = player

    def parse_srt(self, srt_content: str) -> None:
        self.captions = []

        caption_blocks = re.split(r"\n\s*\n", srt_content.strip())

        for block in caption_blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue

            try:
                index = int(lines[0])
                timestamp_line = lines[1]
                text = "\n".join(lines[2:])

                # Parse timestamp
                if " --> " in timestamp_line:
                    start_time, end_time = timestamp_line.split(" --> ")
                    caption = SRTCaption(
                        index, start_time.strip(), end_time.strip(), text
                    )
                    self.captions.append(caption)
            except (ValueError, IndexError):
                continue

        self.renumber_captions()

    def renumber_captions(self) -> None:
        """Renumber all captions sequentially"""
        for i, caption in enumerate(self.captions, 1):
            caption.index = i

    def format_time_display(self, timestamp: str) -> str:
        """Format timestamp for display"""
        return timestamp.replace(",", ".")

    def seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds back to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        milliseconds = int((secs % 1) * 1000)
        secs = int(secs)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def search_captions(self, search_term: str) -> None:
        """Search for captions containing the search term"""
        self.search_term = search_term
        self.search_results = []

        # Clear previous highlights
        for caption in self.captions:
            caption.is_highlighted = False

        if not search_term.strip():
            self.refresh_display()
            self.update_search_info()
            return

        # Find matching captions
        for i, caption in enumerate(self.captions):
            if caption.matches_search(search_term, self.case_sensitive):
                self.search_results.append(i)
                caption.is_highlighted = True

        self.current_search_index = 0
        self.refresh_display()
        self.update_search_info()

        if self.search_results:
            # Scroll to first result
            self.scroll_to_result(0)
            ui.notify(f"Found {len(self.search_results)} matches", type="positive")
        else:
            ui.notify("No matches found", type="info")

    def navigate_search_results(self, direction: int) -> None:
        """Navigate through search results (direction: 1 for next, -1 for previous)"""
        if not self.search_results:
            return

        self.current_search_index = (self.current_search_index + direction) % len(
            self.search_results
        )
        self.scroll_to_result(self.current_search_index)
        self.update_search_info()

    def scroll_to_result(self, result_index: int) -> None:
        """Scroll to a specific search result"""
        if not self.search_results or result_index >= len(self.search_results):
            return

        caption_index = self.search_results[result_index]
        # Select the caption to make it visible
        if caption_index < len(self.captions):
            self.select_caption(self.captions[caption_index])

    def replace_in_current_caption(self, replacement: str) -> None:
        """Replace search term in currently selected caption"""
        if not self.selected_caption or not self.search_term:
            ui.notify("No caption selected or search term empty", type="warning")
            return

        if self.selected_caption.matches_search(self.search_term, self.case_sensitive):
            if self.case_sensitive:
                new_text = self.selected_caption.text.replace(
                    self.search_term, replacement
                )
            else:
                # Case-insensitive replacement
                pattern = re.compile(re.escape(self.search_term), re.IGNORECASE)
                new_text = pattern.sub(replacement, self.selected_caption.text)

            self.selected_caption.text = new_text
            self.refresh_display()
            ui.notify("Replacement made", type="positive")
        else:
            ui.notify("Current caption doesn't contain search term", type="warning")

    def replace_all(self, replacement: str) -> None:
        """Replace search term in all matching captions"""
        if not self.search_term:
            ui.notify("No search term entered", type="warning")
            return

        count = 0
        for caption in self.captions:
            if caption.matches_search(self.search_term, self.case_sensitive):
                if self.case_sensitive:
                    caption.text = caption.text.replace(self.search_term, replacement)
                else:
                    pattern = re.compile(re.escape(self.search_term), re.IGNORECASE)
                    caption.text = pattern.sub(replacement, caption.text)
                count += 1

        if count > 0:
            # Refresh search results
            self.search_captions(self.search_term)
            ui.notify(f"Replaced {count} occurrences", type="positive")
        else:
            ui.notify("No matches found to replace", type="info")

    def update_search_info(self) -> None:
        """Update search information display"""
        if hasattr(self, "search_info_label") and self.search_info_label:
            if self.search_results:
                info_text = f"{self.current_search_index + 1} of {len(self.search_results)} matches"
            else:
                info_text = "No matches" if self.search_term else ""
            self.search_info_label.set_text(info_text)

    def get_highlighted_text(self, text: str) -> str:
        """Get text with search term highlighted (for display purposes)"""
        if not self.search_term or not text:
            return text

        if self.case_sensitive:
            highlighted = text.replace(
                self.search_term,
                f'<mark style="background-color: yellow; padding: 2px;">{self.search_term}</mark>',
            )
        else:
            pattern = re.compile(f"({re.escape(self.search_term)})", re.IGNORECASE)
            highlighted = pattern.sub(
                r'<mark style="background-color: yellow; padding: 2px;">\1</mark>', text
            )

        return highlighted

    def split_caption(self, caption: SRTCaption) -> None:
        """Split a caption into two parts"""
        text_lines = caption.text.split("\n")

        if len(text_lines) == 1:
            # Split single line in half
            text = caption.text
            mid_point = len(text) // 2
            # Find nearest space to split at
            while mid_point > 0 and text[mid_point] != " ":
                mid_point -= 1
            if mid_point == 0:
                mid_point = len(text) // 2

            first_part = text[:mid_point].strip()
            second_part = text[mid_point:].strip()
        else:
            # Split at middle line
            mid_line = len(text_lines) // 2
            first_part = "\n".join(text_lines[:mid_line])
            second_part = "\n".join(text_lines[mid_line:])

        # Calculate time split
        start_seconds = caption.get_start_seconds()
        end_seconds = caption.get_end_seconds()
        mid_seconds = (start_seconds + end_seconds) / 2

        # Update first caption
        caption.text = first_part
        caption.end_time = self.seconds_to_timestamp(mid_seconds)

        # Create second caption
        new_caption = SRTCaption(
            caption.index + 1,
            self.seconds_to_timestamp(mid_seconds),
            self.seconds_to_timestamp(end_seconds),
            second_part,
        )

        # Insert new caption
        caption_index = self.captions.index(caption)
        self.captions.insert(caption_index + 1, new_caption)

        self.renumber_captions()
        self.refresh_display()

    def add_caption_after(self, caption: SRTCaption) -> None:
        """Add a new caption after the selected one"""
        # Calculate new caption timing
        start_seconds = caption.get_end_seconds()

        # Find next caption or add 3 seconds if it's the last one
        caption_index = self.captions.index(caption)
        if caption_index < len(self.captions) - 1:
            next_caption = self.captions[caption_index + 1]
            end_seconds = next_caption.get_start_seconds()
        else:
            end_seconds = start_seconds + 3.0

        # Create new caption
        new_caption = SRTCaption(
            caption.index + 1,
            self.seconds_to_timestamp(start_seconds),
            self.seconds_to_timestamp(end_seconds),
            "New caption text",
        )

        # Insert new caption
        self.captions.insert(caption_index + 1, new_caption)

        self.renumber_captions()
        self.refresh_display()

    def remove_caption(self, caption: SRTCaption) -> None:
        """Remove a caption"""
        if len(self.captions) > 1:  # Don't remove if it's the only caption
            self.captions.remove(caption)
            self.renumber_captions()
            self.refresh_display()
        else:
            ui.notify("Cannot remove the only remaining caption", type="warning")

    def select_caption(self, caption: SRTCaption) -> None:
        """Select/deselect a caption"""
        if self.selected_caption:
            self.selected_caption.is_selected = False

        if self.selected_caption == caption:
            self.selected_caption = None
        else:
            caption.is_selected = True
            self.selected_caption = caption

            # Get caption start time
            if self.__video_player:
                start_seconds = caption.get_start_seconds()
                self.__video_player.seek(start_seconds)

        self.refresh_display()

    def update_caption_text(self, caption: SRTCaption, new_text: str) -> None:
        """Update caption text"""
        caption.text = new_text
        self.refresh_display()

    def update_caption_timing(
        self, caption: SRTCaption, start_time: str, end_time: str
    ) -> None:
        """Update caption timing"""
        caption.start_time = start_time
        caption.end_time = end_time
        self.refresh_display()

    def export_srt(self) -> str:
        """Export captions to SRT format"""
        return "\n\n".join(caption.to_srt_format() for caption in self.captions)

    def create_search_panel(self) -> None:
        """Create the search panel UI"""
        with ui.expansion("Search & Replace").classes("w-full").style(
            "color: #4a90e2;"
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

    def create_caption_card(self, caption: SRTCaption) -> ui.card:
        """Create a visual card for a caption"""
        card_class = "cursor-pointer border-0 transition-all duration-200 w-full"

        if caption.is_selected:
            card_class += " border-blue-500 bg-blue-50 shadow-lg"
        elif caption.is_highlighted:
            card_class += " border-yellow-400 bg-yellow-50 hover:border-yellow-500"
        else:
            card_class += " hover:border-gray-300 hover:shadow-md shadow-none"

        with ui.card().classes(card_class) as card:
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(f"#{caption.index}").classes("font-bold text-sm text-gray-500")
                ui.label(
                    f"{self.format_time_display(caption.start_time)} → {self.format_time_display(caption.end_time)}"
                ).classes("text-xs text-gray-400 font-mono")

            # Caption text (editable when selected)
            if caption.is_selected:
                text_area = (
                    ui.textarea(value=caption.text)
                    .classes("w-full")
                    .props("outlined input-class=h-16")
                )
                text_area.on(
                    "blur", lambda e: self.update_caption_text(caption, e.sender.value)
                )

                # Timing editors
                with ui.row().classes("w-full gap-2 mt-2"):
                    start_input = (
                        ui.input("Start Time", value=caption.start_time)
                        .classes("flex-1")
                        .props("outlined dense")
                    )
                    end_input = (
                        ui.input("End Time", value=caption.end_time)
                        .classes("flex-1")
                        .props("outlined dense")
                    )

                def update_timing():
                    self.update_caption_timing(
                        caption, start_input.value, end_input.value
                    )

                start_input.on("blur", lambda: update_timing())
                end_input.on("blur", lambda: update_timing())

                # Action buttons
                with ui.row().classes("w-full gap-2 mt-3"):
                    ui.button("Split", icon="call_split", color="blue").props(
                        "flat dense"
                    ).on("click", lambda: self.split_caption(caption))
                    ui.button("Add After", icon="add", color="green").props(
                        "flat dense"
                    ).on("click", lambda: self.add_caption_after(caption))
                    ui.button("Remove", icon="delete", color="red").props(
                        "flat dense"
                    ).on("click", lambda: self.remove_caption(caption))
                    ui.button("Done", icon="check", color="grey").props(
                        "flat dense"
                    ).on("click", lambda: self.select_caption(caption))
            else:
                # Show text with search highlighting
                if caption.is_highlighted and self.search_term:
                    highlighted_text = self.get_highlighted_text(caption.text)
                    ui.html(highlighted_text).classes(
                        "text-sm leading-relaxed whitespace-pre-wrap"
                    )
                else:
                    ui.label(caption.text).classes(
                        "text-sm leading-relaxed whitespace-pre-wrap"
                    )

            card.on(
                "click",
                lambda: self.select_caption(caption)
                if not caption.is_selected
                else None,
            )

        return card

    def refresh_display(self) -> None:
        """Refresh the caption display"""
        if self.main_container:
            self.main_container.clear()
            with self.main_container:
                if not self.captions:
                    ui.label("No captions loaded").classes(
                        "text-gray-500 text-center p-8"
                    )
                else:
                    for caption in self.captions:
                        self.create_caption_card(caption)


@app.get("/video/{job_id}")
async def video_proxy(request: Request, job_id: str) -> Response:
    headers = dict(request.headers)
    headers["Authorization"] = get_auth_header().get("Authorization", "")

    response = requests.get(
        f"{API_URL}/api/v1/transcriber/{job_id}/videostream",
        headers=headers,
    )

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type"),
        headers=response.headers,
    )


def create() -> None:
    @ui.page("/srt")
    def result(uuid: str, filename: str) -> None:
        """
        Display the result of the transcription job.
        """
        global data, edit_panel, video, table, table_page

        page_init()

        try:
            response = requests.get(
                f"{API_URL}/api/v1/transcriber/{uuid}/result", headers=get_auth_header()
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            ui.notify(f"Error: Failed to get result: {e}")
            return

        data = response.content.decode()

        with ui.row().classes("justify-between items-center mb-4"):

            def export_srt():
                if "editor" in locals():
                    srt_content = editor.export_srt()
                    ui.download(srt_content.encode(), filename=f"{filename}.srt")
                    ui.notify("SRT file exported successfully", type="positive")
                else:
                    ui.notify("No editor available", type="warning")

            with ui.button_group().props("outline"):
                ui.button("Save", icon="save", on_click=export_srt).style(
                    "width: 150px;"
                )
                ui.button("Export", icon="share", on_click=export_srt).style(
                    "width: 150px;"
                )
        ui.separator()
        with ui.splitter(value=60).classes("w-full h-full") as splitter:
            with splitter.before:
                with ui.card().classes("w-full h-full"):
                    editor = SRTEditor()
                    editor.create_search_panel()
                    with ui.scroll_area().style("height: calc(100vh - 200px);"):
                        editor.main_container = ui.column().classes("w-full h-full")
                    editor.parse_srt(data)
                    editor.refresh_display()
                with splitter.after:
                    with ui.card().classes("w-full h-full"):
                        ui.label("Video Preview").classes("text-lg font-bold mb-4")
                        video = ui.video(
                            f"/video/{uuid}",
                            controls=True,
                            autoplay=False,
                            loop=False,
                        ).classes("w-full h-full")
                        editor.set_video_player(video)
