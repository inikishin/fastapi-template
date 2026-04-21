import logging

import uvicorn
from fastapi import FastAPI

from src.api.v1.user.views import user_router
from src.config.settings import app_config

logger = logging.getLogger(__name__)

app = FastAPI(
    title=app_config.project_title,
    docs_url=app_config.project_docs_url,
    openapi_url=app_config.project_openapi_url,
    version=app_config.project_docs_version,
)

app.include_router(user_router, prefix="/api/v1")

if __name__ == "__main__":
    logger.info("Start server...")
    uvicorn.run(
        "main:app",
        host=app_config.project_host,
        port=app_config.project_port,
        reload=True,
    )
