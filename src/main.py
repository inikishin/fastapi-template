import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.v1 import base
from core import config

logger = logging.getLogger(__name__)

app = FastAPI(
    title=config.PROJECT_NAME,
    docs_url=config.DOCS_URL,
    openapi_url=config.OPENAPI_URL,
    default_response_class=ORJSONResponse,
)

app.include_router(base.router, prefix='/api/v1')

if __name__ == '__main__':
    logger.info('Start server...')
    uvicorn.run(
        'main:app',
        host=config.PROJECT_HOST,
        port=config.PROJECT_PORT,
        reload=True,
    )
