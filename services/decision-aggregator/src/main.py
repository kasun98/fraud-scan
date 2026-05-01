import json
import logging
import os
import signal
import time

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from alerting import fire_alerts
from database import save_decision

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger("decision-aggregator")

KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_DECISIONS  = os.getenv("KAFKA_TOPIC_DECISIONS",   "fraud-decisions")
TOPIC_ALERTS     = os.getenv("KAFKA_TOPIC_ALERTS",      "fraud-alerts")
GROUP_ID         = "decision-aggregator-group"

_running = True


def _shutdown(sig, frame):
    global _running
    logger.info("Shutdown signal received")
    _running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT,  _shutdown)


def make_consumer() -> KafkaConsumer:
    for attempt in range(10):
        try:
            return KafkaConsumer(
                TOPIC_DECISIONS,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=GROUP_ID,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
        except KafkaError as e:
            logger.warning("Kafka not ready (%d/10): %s", attempt + 1, e)
            time.sleep(3)
    raise RuntimeError("Cannot connect to Kafka")


def make_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        compression_type="gzip",
    )


def process_decision(decision: dict, producer: KafkaProducer) -> None:
    transaction_id = decision.get("transaction_id", "?")
    verdict        = decision.get("decision", "APPROVE")

    logger.info(
        "Processing decision %s | verdict=%s | score=%.4f",
        transaction_id, verdict, decision.get("final_score", 0),
    )

    # 1. Write to Postgres audit log
    save_decision(decision)

    # 2. Fire alerts for BLOCK decisions
    fire_alerts(decision)

    # 3. Publish to fraud-alerts topic for downstream consumers
    if verdict in ("BLOCK", "REVIEW"):
        producer.send(
            topic=TOPIC_ALERTS,
            key=decision.get("user_id", ""),
            value={
                "transaction_id": transaction_id,
                "user_id":        decision.get("user_id"),
                "decision":       verdict,
                "final_score":    decision.get("final_score"),
                "triggered_rules": decision.get("triggered_rules", []),
                "amount":         decision.get("amount"),
                "timestamp":      decision.get("timestamp"),
            },
        )


def main():
    consumer = make_consumer()
    producer = make_producer()
    logger.info("Decision aggregator started — consuming from %s", TOPIC_DECISIONS)
    processed = 0

    try:
        while _running:
            records = consumer.poll(timeout_ms=1000)
            for partition, messages in records.items():
                for msg in messages:
                    try:
                        process_decision(msg.value, producer)
                        processed += 1
                        if processed % 50 == 0:
                            logger.info("Processed %d decisions", processed)
                    except Exception as e:
                        logger.error("Error processing decision: %s", e)
    finally:
        consumer.close()
        producer.flush()
        producer.close()
        logger.info("Decision aggregator stopped — total: %d", processed)


if __name__ == "__main__":
    main()