"""
Kafka producer.

Copied into src/config/kafka/producer.py by the initial-setup skill on demand.
Do not edit this template inside the skill — adjust the copy in src/config/kafka/.
"""

import json

from aiokafka import AIOKafkaProducer
from aiokafka.helpers import create_ssl_context

from src.config.logger import LoggerProvider
from src.config.settings import app_config

log = LoggerProvider().get_logger(__name__)


class KafkaProducer:
    """Thin wrapper around AIOKafkaProducer with JSON serialization."""

    def __init__(
        self,
        bootstrap_servers: str | None,
        sasl_plain_username: str | None,
        sasl_plain_password: str | None,
        security_protocol: str | None,
        sasl_mechanism: str | None,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.sasl_plain_username = sasl_plain_username
        self.sasl_plain_password = sasl_plain_password
        self.security_protocol = security_protocol
        self.sasl_mechanism = sasl_mechanism
        self.producer: AIOKafkaProducer | None = None

    async def start(self):
        """Create and start the Kafka producer."""
        assert self.bootstrap_servers is not None
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                sasl_plain_username=self.sasl_plain_username,
                sasl_plain_password=self.sasl_plain_password,
                security_protocol=self.security_protocol,
                sasl_mechanism=self.sasl_mechanism,
                ssl_context=create_ssl_context(),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            )
            await self.producer.start()
        except Exception as e:
            self.producer = None
            log.error(f"Failed to start Kafka producer: {e}")

    async def stop(self):
        """Stop the producer."""
        if self.producer:
            await self.producer.stop()

    async def send(self, topic: str, message: dict | list):
        """Publish a JSON message to the given Kafka topic."""
        if self.producer is None:
            log.warning("Kafka producer is not initialized, message not sent")
            raise RuntimeError("Kafka producer is not initialized")
        await self.producer.send_and_wait(topic, message)


async def get_kafka_producer() -> KafkaProducer:
    """FastAPI dependency that returns a fresh KafkaProducer instance."""
    return KafkaProducer(
        bootstrap_servers=app_config.kafka_addr,
        sasl_plain_username=app_config.kafka_sasl_username,
        sasl_plain_password=app_config.kafka_sasl_password,
        security_protocol=app_config.kafka_security_protocol,
        sasl_mechanism=app_config.kafka_sasl_mechanism,
    )
