import os
from logging import config as logging_config

from core.logger import LOGGING

logging_config.dictConfig(LOGGING)

PROJECT_NAME = 'FastAPI Template'
PROJECT_HOST = '0.0.0.0'
PROJECT_PORT = 8000

DOCS_URL = '/api/openapi'
OPENAPI_URL = '/api/openapi.json'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
