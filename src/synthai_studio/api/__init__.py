"""SynthAI Studio REST API package.

Pre-conditions:
    - FastAPI installed.
Post-conditions:
    - Exposes application factory.
"""

from synthai_studio.api.main import app, create_app

__all__ = ["app", "create_app"]
