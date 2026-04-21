"""
Taskiq broker + result backend built on top of Redis streams.

Copied into src/config/taskiq/broker.py by the initial-setup skill on demand.
Do not edit this template inside the skill — adjust the copy in src/config/taskiq/.
"""

import taskiq_fastapi
from taskiq import SmartRetryMiddleware
from taskiq.serializers.orjson_serializer import ORJSONSerializer
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from src.config.settings import app_config

taskiq_backend = RedisAsyncResultBackend(
    f"{app_config.redis_url}/{app_config.taskiq_redis_db}",
    serializer=ORJSONSerializer(),
    result_ex_time=60 * 60 * 24 * 5,
)

taskiq_broker = (
    RedisStreamBroker(
        f"{app_config.redis_url}/{app_config.taskiq_redis_db}",
    )
    .with_result_backend(taskiq_backend)
    .with_serializer(ORJSONSerializer())
    .with_middlewares(
        SmartRetryMiddleware(
            default_retry_count=1,
            default_delay=10,
            use_jitter=True,
            use_delay_exponent=True,
            max_delay_exponent=120,
        ),
    )
)

taskiq_fastapi.init(taskiq_broker, "src.main:app")
