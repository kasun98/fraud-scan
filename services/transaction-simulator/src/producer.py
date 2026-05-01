import json
import logging
import time
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


def make_producer(bootstrap_servers: str) -> KafkaProducer:
    """Create a Kafka producer with retry logic."""
    for attempt in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",                  # wait for all replicas to ack
                retries=5,
                max_in_flight_requests_per_connection=1,
                compression_type="gzip",
                linger_ms=5,                 # batch for 5ms before sending
            )
            logger.info("Kafka producer connected to %s", bootstrap_servers)
            return producer
        except KafkaError as e:
            logger.warning("Kafka not ready (attempt %d/10): %s", attempt + 1, e)
            time.sleep(3)
    raise RuntimeError("Could not connect to Kafka after 10 attempts")


def send_transaction(
    producer: KafkaProducer,
    topic: str,
    transaction: dict[str, Any],
) -> None:
    """Send a single transaction to Kafka, keyed by user_id for ordering."""
    future = producer.send(
        topic=topic,
        key=transaction["user_id"],
        value=transaction,
    )
    try:
        record_metadata = future.get(timeout=10)
        logger.debug(
            "Sent txn %s → topic=%s partition=%d offset=%d",
            transaction["transaction_id"],
            record_metadata.topic,
            record_metadata.partition,
            record_metadata.offset,
        )
    except KafkaError as e:
        logger.error("Failed to send transaction %s: %s",
                     transaction["transaction_id"], e)
        raise