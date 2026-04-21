"""
Taskiq scheduler: combines Redis-backed cron sources with label-based sources.

Copied into src/config/taskiq/scheduler.py by the initial-setup skill on demand.
Do not edit this template inside the skill — adjust the copy in src/config/taskiq/.
"""

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisScheduleSource

from src.config.settings import app_config
from src.config.taskiq.broker import taskiq_broker

redis_source = RedisScheduleSource(
    f"{app_config.redis_url}/{app_config.taskiq_redis_db}",
)

scheduler = TaskiqScheduler(
    taskiq_broker,
    [
        redis_source,
        LabelScheduleSource(taskiq_broker),
    ],
)
