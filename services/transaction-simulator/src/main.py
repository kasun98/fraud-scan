import logging
import signal
import sys
import time

import config
from generator import generate_transaction
from producer import make_producer, send_transaction

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("simulator")

_running = True


def _shutdown(sig, frame):
    global _running
    logger.info("Shutdown signal received — draining...")
    _running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT,  _shutdown)


def main():
    logger.info(
        "Starting simulator | rate=%.1f tps | fraud_rate=%.1f%%",
        config.TRANSACTIONS_PER_SECOND,
        config.FRAUD_RATE * 100,
    )

    producer     = make_producer(config.KAFKA_BOOTSTRAP_SERVERS)
    interval_sec = 1.0 / config.TRANSACTIONS_PER_SECOND
    sent = fraud = 0

    try:
        while _running:
            loop_start = time.monotonic()

            txn = generate_transaction(fraud_rate=config.FRAUD_RATE)
            send_transaction(producer, config.KAFKA_TOPIC_RAW, txn)

            sent += 1
            if txn["is_fraud"]:
                fraud += 1

            if sent % 100 == 0:
                logger.info(
                    "Progress: sent=%d fraud=%d (%.1f%%)",
                    sent, fraud, (fraud / sent) * 100,
                )

            # Precise rate limiting
            elapsed = time.monotonic() - loop_start
            sleep_time = interval_sec - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    finally:
        logger.info("Flushing producer — total sent=%d fraud=%d", sent, fraud)
        producer.flush()
        producer.close()
        logger.info("Simulator stopped cleanly")


if __name__ == "__main__":
    main()