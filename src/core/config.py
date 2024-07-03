import os
from logging import config as logging_config

from pydantic import BaseSettings

from core.logger import LOGGING

logging_config.dictConfig(LOGGING)


DOCS_URL = "/api/openapi"
OPENAPI_URL = "/api/openapi.json"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppConfig(BaseSettings):
    project_title: str = "FastAPI Template"
    project_host: str = "0.0.0.0"
    project_port: int = 8000
    project_docs_url: str = "/api/openapi"
    project_openapi_url: str = "/api/openapi.json"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "template"
    db_user: str = "demo"
    db_pass: str = "demo"
    db_show_queries: bool = True

    class Config:
        env_file = ".env"


app_config = AppConfig()
