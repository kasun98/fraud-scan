import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer
from kafka.errors import KafkaError

from models import TransactionEvent, TransactionResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger("transaction-api")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC     = os.getenv("KAFKA_TOPIC_RAW", "transactions-raw")

producer: KafkaProducer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    logger.info("Connecting to Kafka at %s", KAFKA_BOOTSTRAP)

    for attempt in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=5,
                compression_type="gzip",
            )
            logger.info("Kafka producer connected")
            break
        except KafkaError as e:
            logger.warning("Kafka not ready (attempt %d/10): %s", attempt + 1, e)
            time.sleep(3)
    else:
        raise RuntimeError("Cannot connect to Kafka after 10 attempts")

    yield

    if producer:
        producer.flush()
        producer.close()
        logger.info("Kafka producer closed")


app = FastAPI(
    title="Transaction Ingestion API",
    description="Webhook endpoint for real-time financial transaction events",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
def health():
    return {
        "status": "ok",
        "kafka_connected": producer is not None,
        "topic": KAFKA_TOPIC,
    }


@app.get("/ready", tags=["ops"])
def ready():
    if producer is None:
        raise HTTPException(status_code=503, detail="Kafka not connected")
    return {"status": "ready"}


@app.post(
    "/api/v1/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["transactions"],
    summary="Ingest a single transaction event",
)
async def ingest_transaction(event: TransactionEvent):
    if producer is None:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    payload = event.to_kafka_payload()

    try:
        future = producer.send(
            topic=KAFKA_TOPIC,
            key=event.user_id,
            value=payload,
        )
        record = future.get(timeout=10)
        logger.info(
            "Ingested txn %s -> partition=%d offset=%d",
            event.transaction_id,
            record.partition,
            record.offset,
        )
        return TransactionResponse(
            transaction_id=str(event.transaction_id),
            status="accepted",
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            message="Transaction queued for fraud analysis",
        )
    except KafkaError as e:
        logger.error("Kafka send failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Kafka error: {e}")


@app.post(
    "/api/v1/transactions/batch",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["transactions"],
    summary="Ingest a batch of transaction events (max 100)",
)
async def ingest_batch(events: list[TransactionEvent]):
    if producer is None:
        raise HTTPException(status_code=503, detail="Kafka producer not ready")

    if len(events) > 100:
        raise HTTPException(status_code=400, detail="Max batch size is 100")

    results = []
    for event in events:
        payload = event.to_kafka_payload()
        try:
            future = producer.send(
                topic=KAFKA_TOPIC,
                key=event.user_id,
                value=payload,
            )
            record = future.get(timeout=10)
            results.append({
                "transaction_id": str(event.transaction_id),
                "status": "accepted",
                "partition": record.partition,
                "offset": record.offset,
            })
        except KafkaError as e:
            results.append({
                "transaction_id": str(event.transaction_id),
                "status": "failed",
                "error": str(e),
            })

    producer.flush()
    accepted = sum(1 for r in results if r["status"] == "accepted")
    failed   = sum(1 for r in results if r["status"] == "failed")
    logger.info("Batch complete: accepted=%d failed=%d", accepted, failed)

    return {
        "processed": len(results),
        "accepted": accepted,
        "failed": failed,
        "results": results,
    }