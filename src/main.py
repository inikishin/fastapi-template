import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.v1 import base
from core.config import app_config

logger = logging.getLogger(__name__)

app = FastAPI(
    title=app_config.project_title,
    docs_url=app_config.project_docs_url,
    openapi_url=app_config.project_openapi_url,
    default_response_class=ORJSONResponse,
)

app.include_router(base.router, prefix="/api/v1")

if __name__ == "__main__":
    logger.info("Start server...")
    uvicorn.run(
        "main:app",
        host=app_config.project_host,
        port=app_config.project_port,
        reload=True,
    )
