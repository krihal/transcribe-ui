from nicegui import ui, app
from pages.srt import create as create_srt
from pages.home import create as create_files_table
from pages.txt import create as create_txt
from utils.oidc import is_authenticated, get_auth_config

create_files_table()
create_srt()
create_txt()


@ui.page("/")
def index() -> None:
    """
    Index page with login.
    """
    authenticated = is_authenticated()

    if authenticated:
        ui.navigate.to("/home")
        return

    with ui.card() as card:
        card.style("width: 50%; align-self: center; height: 50vh; margin-top: 10%;")
        ui.label("Welcome to SUNET Transcriber").classes("text-h5").style(
            "margin: auto;"
        )
        ui.image("static/sunet_logo.svg").style(
            "width: 200px; height: auto; margin: auto; magin-top: auto;"
        )
        ui.button(
            "Login with SSO",
            icon="login",
            on_click=lambda: ui.navigate.to("/login"),
        ).style("margin-top: auto; margin-bottom: 5px;")


app.add_static_files(url_path="/static", local_directory="static/")
ui.run(
    storage_secret=get_auth_config().cookie_secret_key,
    title="SUNET Transcriber",
    port=8888,
)
