from nicegui import ui
from utils.common import (
    page_init,
    jobs_get,
    jobs_columns,
    table_click,
    table_transcribe,
    table_upload,
    table_delete,
)


def create() -> None:
    @ui.refreshable
    @ui.page("/home")
    def home() -> None:
        """
        Main page of the application.
        """
        page_init()

        table = ui.table(
            columns=jobs_columns,
            rows=jobs_get(),
            selection="multiple",
            pagination=10,
        )

        ui.add_head_html(
            """
            <style>
                .table-style td {
                    background: #eeeeee;
                }
            </style>
        """
        )
        table.style("width: 100%; height: calc(100vh - 130px); box-shadow: none;")
        table.on("rowClick", table_click)
        table.classes("text-h2 table-style")
        table.add_slot(
            "body-cell-status",
            """
            <q-td key="status" :props="props">
                <q-badge v-if="{Completed: 'green', Uploaded: 'orange', Failed: 'red', Transcribing: 'orange', Pending: 'blue'}[props.value]" :color="{Completed: 'green', Uploaded: 'orange', Failed: 'red', Transcribing: 'orange', Pending: 'blue'}[props.value]">
                    {{props.value}}
                </q-badge>
                <p v-else>
                    {{props.value}}
                </p>
            </q-td>
            """,
        )
        table.add_slot(
            "body-cell-format",
            """
            <q-td key="format" :props="props">
                <q-badge v-if="{SRT: 'blue', TXT: 'grey'}[props.value]" :color="{SRT: 'blue', TXT: 'grey'}[props.value]">
                    {{props.value}}
                </q-badge>
                <p v-else>
                    {{props.value}}
                </p>
            </q-td>
            """,
        )

        with table.add_slot("top-left"):
            ui.label("My files").classes("text-h5")

        with table.add_slot("top-right"):
            with ui.row().classes("items-center"):
                with ui.button("Upload", icon="upload") as upload:
                    upload.props("color=primary flat")
                    upload.on("click", lambda: table_upload(table))
                with ui.button("Transcribe", icon="play_circle") as transcribe:
                    transcribe.props("color=primary flat")
                    transcribe.on(
                        "click", lambda: table_transcribe(table), table.selected
                    )
                with ui.button("Delete", icon="delete") as refresh:
                    refresh.props("color=primary flat")
                    refresh.on("click", lambda: table_delete(table.selected))
                with ui.input(placeholder="Search").props("type=search").bind_value(
                    table, "filter"
                ).add_slot("append"):
                    ui.icon("search")

        def update_rows():
            """
            Update the rows in the table.
            """
            table.update_rows(jobs_get(), clear_selection=False)

        ui.timer(5.0, lambda: update_rows())
