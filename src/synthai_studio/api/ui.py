"""Typed UI router, static asset loader, and templates mounting for SynthAI Studio.

Pre-conditions:
    - templates/index.html and static/ assets reside relative to this package directory.
    - FastAPI and Starlette are installed in the active environment.
Post-conditions:
    - Exposes directory resolvers, cached index.html loader, and static mounting helper.
"""

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

__all__ = [
    "API_PACKAGE_DIR",
    "TEMPLATES_DIR",
    "STATIC_DIR",
    "get_templates_dir",
    "get_static_dir",
    "load_studio_index_html",
    "mount_studio_ui",
]

API_PACKAGE_DIR: Path = Path(__file__).resolve().parent
TEMPLATES_DIR: Path = API_PACKAGE_DIR / "templates"
STATIC_DIR: Path = API_PACKAGE_DIR / "static"


def get_templates_dir() -> Path:
    """Return the absolute path to the templates directory.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns Path pointing to synthai_studio/api/templates.
    """
    return TEMPLATES_DIR


def get_static_dir() -> Path:
    """Return the absolute path to the static assets directory.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns Path pointing to synthai_studio/api/static.
    """
    return STATIC_DIR


@lru_cache(maxsize=1)
def load_studio_index_html() -> str:
    """Read and cache the modular HTML5 index.html template from disk.

    Pre-conditions:
        - templates/index.html exists under TEMPLATES_DIR.
    Post-conditions:
        - Returns the UTF-8 text content of the index.html template.
    """
    template_path = get_templates_dir() / "index.html"
    if not template_path.is_file():
        raise FileNotFoundError(f"Template index.html not found at {template_path}")
    return template_path.read_text(encoding="utf-8")


def mount_studio_ui(application: FastAPI) -> None:
    """Mount static assets directory and register interactive UI root route.

    Pre-conditions:
        - application is an active FastAPI application instance.
        - STATIC_DIR exists.
    Post-conditions:
        - Mounts /static route with StaticFiles handler.
        - Registers GET / returning HTMLResponse with modular index.html content.
    """
    static_path = get_static_dir()
    if static_path.is_dir():
        application.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @application.get("/", response_class=HTMLResponse)
    async def index_ui() -> HTMLResponse:
        """Render the 5-Step Interactive SynthAI Studio Web UI console.

        Pre-conditions:
            - templates/index.html is accessible.
        Post-conditions:
            - Returns 200 OK HTMLResponse containing the single-page application.
        """
        return HTMLResponse(content=load_studio_index_html(), status_code=200)
