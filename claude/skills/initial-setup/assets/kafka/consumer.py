"""
Kafka consumer.

Copied into src/config/kafka/consumer.py by the initial-setup skill on demand.
Do not edit this template inside the skill — adjust the copy in src/config/kafka/.
"""

import json

from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context

from src.config.logger import LoggerProvider
from src.config.settings import app_config

log = LoggerProvider().get_logger(__name__)


def safe_json_deserializer(v: bytes):
    """Safely deserialize JSON, returning None for empty or invalid messages."""
    if not v:
        log.warning("Received empty message, skipping")
        return None
    try:
        return json.loads(v.decode("utf-8"))
    except json.JSONDecodeError as e:
        log.warning(f"Failed to decode message: {v!r}, error: {e}")
        return None


class KafkaConsumer:
    """Thin wrapper around AIOKafkaConsumer with a safe deserializer and a stop flag."""

    def __init__(
        self,
        topics: list[str],
        bootstrap_servers: str | None,
        group_id: str | None,
        sasl_plain_username: str | None,
        sasl_plain_password: str | None,
        security_protocol: str | None,
        sasl_mechanism: str | None,
    ):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.sasl_plain_username = sasl_plain_username
        self.sasl_plain_password = sasl_plain_password
        self.security_protocol = security_protocol
        self.sasl_mechanism = sasl_mechanism
        self.consumer: AIOKafkaConsumer | None = None
        self._stopping = False

    async def start(self):
        """Create the underlying consumer and start it."""
        assert self.bootstrap_servers is not None
        self._stopping = False
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                sasl_plain_username=self.sasl_plain_username,
                sasl_plain_password=self.sasl_plain_password,
                security_protocol=self.security_protocol,
                sasl_mechanism=self.sasl_mechanism,
                value_deserializer=safe_json_deserializer,
                auto_offset_reset="earliest",
                ssl_context=create_ssl_context(),
            )
            await self.consumer.start()
            log.info(f"Kafka consumer started, subscribed to: {self.topics}")
        except Exception as e:
            self.consumer = None
            log.error(f"Failed to start Kafka consumer: {e}")

    async def stop(self):
        """Stop the consumer."""
        self._stopping = True
        if self.consumer:
            await self.consumer.stop()
            log.info("Kafka consumer stopped")

    async def consume(self):
        """Iterate over incoming messages; stops when self._stopping is set."""
        if self.consumer:
            log.info("Start consuming messages")
            async for message in self.consumer:
                if self._stopping:
                    break
                if message.value is None:
                    continue
                yield message.value


TOPICS_TO_READ: list[str] = []


kafka_consumer = KafkaConsumer(
    topics=TOPICS_TO_READ,
    bootstrap_servers=app_config.kafka_addr,
    group_id=app_config.kafka_group_id,
    sasl_plain_username=app_config.kafka_sasl_username,
    sasl_plain_password=app_config.kafka_sasl_password,
    security_protocol=app_config.kafka_security_protocol,
    sasl_mechanism=app_config.kafka_sasl_mechanism,
)


async def consume_messages():
    """Main consumer loop — logs every received message."""
    log.info("Started consumer loop")
    try:
        async for message in kafka_consumer.consume():
            log.info(f"Received message: {message}")
    except Exception as e:
        log.error(f"Kafka consumer: error occurred {e}")
