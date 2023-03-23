import os
import sys

from fastapi.testclient import TestClient
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.append(SRC_DIR)

from main import app


@pytest.fixture
def api_client():
    client = TestClient(app)
    yield client
