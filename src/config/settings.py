import os

from pydantic_settings import BaseSettings

DOCS_URL = "/api/openapi"
OPENAPI_URL = "/api/openapi.json"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppConfig(BaseSettings):
    project_title: str = "Start FastAPI service"
    project_host: str = "0.0.0.0"
    project_port: int = 8000
    project_docs_url: str = "/api/openapi"
    project_docs_version: str = "1.0.0"
    project_openapi_url: str = "/api/openapi.json"

    db_driver_name: str = "postgresql+asyncpg"
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "template"
    db_user: str = "demo"
    db_pass: str = "demo"
    db_show_queries: bool = False

    @property
    def get_db_creds(self):
        return {
            "drivername": self.db_driver_name,
            "username": self.db_user,
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "password": self.db_pass,
        }

    class Config:
        env_file = ".env"


app_config = AppConfig()
