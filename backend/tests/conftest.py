import os
import sys

# Make the backend/ package importable when tests are run from any directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app
from config import Config


@pytest.fixture()
def app():
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_generated_audio():
    """Ensure each test starts and ends with an empty generated_audio/ dir."""
    yield
    for name in os.listdir(Config.GENERATED_AUDIO_DIR):
        if name != ".gitkeep":
            try:
                os.remove(os.path.join(Config.GENERATED_AUDIO_DIR, name))
            except OSError:
                pass
