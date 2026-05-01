import json
import logging
import os
import signal
import time

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from features import compute_transaction_features
from redis_store import FeatureStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger("feature-engineering")

KAFKA_BOOTSTRAP   = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_RAW         = os.getenv("KAFKA_TOPIC_RAW",    "transactions-raw")
TOPIC_SCORED_IN   = os.getenv("KAFKA_TOPIC_FEATURES", "transactions-scored")
REDIS_HOST        = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT        = int(os.getenv("REDIS_PORT", "6379"))
GROUP_ID          = "feature-engineering-group"

_running = True

def _shutdown(sig, frame):
    global _running
    logger.info("Shutdown signal — stopping consumer")
    _running = False

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT,  _shutdown)


def make_consumer() -> KafkaConsumer:
    for attempt in range(10):
        try:
            return KafkaConsumer(
                TOPIC_RAW,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=GROUP_ID,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                max_poll_records=50,
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


def main():
    store    = FeatureStore(host=REDIS_HOST, port=REDIS_PORT)
    consumer = make_consumer()
    producer = make_producer()

    logger.info("Feature engineering service started — consuming from %s", TOPIC_RAW)
    processed = 0

    try:
        while _running:
            records = consumer.poll(timeout_ms=1000)
            for partition, messages in records.items():
                for msg in messages:
                    txn = msg.value
                    try:
                        user_id = txn["user_id"]

                        # Update rolling features in Redis
                        user_features = store.update_user_features(user_id, txn)

                        # Get velocity count (transactions in last 10 min)
                        velocity = store.get_velocity_count(user_id, window_minutes=10)

                        # Build full feature vector
                        feature_vector = compute_transaction_features(
                            txn, user_features, velocity
                        )

                        # Publish enriched event for ML scoring service
                        producer.send(
                            topic=TOPIC_SCORED_IN,
                            key=user_id,
                            value=feature_vector,
                        )

                        processed += 1
                        if processed % 100 == 0:
                            logger.info("Processed %d transactions", processed)

                    except Exception as e:
                        logger.error(
                            "Error processing txn %s: %s",
                            txn.get("transaction_id", "?"), e,
                        )
    finally:
        consumer.close()
        producer.flush()
        producer.close()
        logger.info("Feature engineering stopped — total processed: %d", processed)


if __name__ == "__main__":
    main()