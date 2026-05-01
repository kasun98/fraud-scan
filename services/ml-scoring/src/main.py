import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from pydantic import BaseModel

from rules import evaluate_all_rules, compute_rules_score
from scorer import FraudScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger("ml-scoring")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_IN        = os.getenv("KAFKA_TOPIC_FEATURES",  "transactions-scored")
TOPIC_OUT       = os.getenv("KAFKA_TOPIC_DECISIONS", "fraud-decisions")
GROUP_ID        = "ml-scoring-group"
FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.55"))

scorer:   FraudScorer   | None = None
producer: KafkaProducer | None = None
_running  = True


def make_producer() -> KafkaProducer:
    for attempt in range(10):
        try:
            p = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                compression_type="gzip",
            )
            logger.info("Kafka producer connected")
            return p
        except KafkaError as e:
            logger.warning("Producer not ready (%d/10): %s", attempt + 1, e)
            time.sleep(3)
    raise RuntimeError("Cannot connect Kafka producer")


def make_consumer() -> KafkaConsumer:
    for attempt in range(10):
        try:
            c = KafkaConsumer(
                TOPIC_IN,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=GROUP_ID,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                max_poll_records=20,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
            logger.info("Kafka consumer connected — group=%s topic=%s", GROUP_ID, TOPIC_IN)
            return c
        except KafkaError as e:
            logger.warning("Consumer not ready (%d/10): %s", attempt + 1, e)
            time.sleep(3)
    raise RuntimeError("Cannot connect Kafka consumer")


def score_one(features: dict) -> dict:
    """Score a single feature vector — pure function, no side effects."""
    start = time.monotonic()

    ml_result   = scorer.score(features)
    ml_score    = ml_result["fraud_probability"]
    velocity    = features.get("velocity_10min", 0)
    rule_hits   = evaluate_all_rules(features, velocity)
    rules_score = compute_rules_score(rule_hits)
    final_score = round(ml_score * 0.7 + rules_score * 0.3, 6)

    if final_score >= 0.7:
        decision = "BLOCK"
    elif final_score >= 0.6:
        decision = "REVIEW"
    else:
        decision = "APPROVE"

    elapsed_ms = round((time.monotonic() - start) * 1000, 2)

    return {
        "transaction_id":    features.get("transaction_id"),
        "user_id":           features.get("user_id"),
        "ml_score":          round(ml_score, 6),
        "rules_score":       round(rules_score, 6),
        "final_score":       final_score,
        "decision":          decision,
        "triggered_rules":   [r.rule_name for r in rule_hits if r.triggered],
        "is_fraud":          decision == "BLOCK",
        "processing_ms":     elapsed_ms,
        "amount":            features.get("amount", 0),
        "currency":          features.get("currency", "USD"),
        "merchant_name":     features.get("merchant_name", ""),
        "merchant_category": features.get("merchant_category", ""),
        "merchant_country":  features.get("merchant_country", ""),
        "user_country":      features.get("user_country", ""),
        "payment_method":    features.get("payment_method", ""),
        "channel":           features.get("channel", ""),
        "created_at_epoch":  features.get("created_at_epoch"),
    }


def consumer_loop():
    """Runs in background thread — consumes features, produces decisions."""
    global _running
    consumer = make_consumer()
    processed = 0

    try:
        while _running:
            records = consumer.poll(timeout_ms=500)
            for partition, messages in records.items():
                for msg in messages:
                    try:
                        result = score_one(msg.value)
                        producer.send(
                            topic=TOPIC_OUT,
                            key=result["user_id"],
                            value=result,
                        )
                        processed += 1
                        if processed % 100 == 0:
                            logger.info(
                                "Scored %d transactions | last decision=%s | %.2fms",
                                processed,
                                result["decision"],
                                result["processing_ms"],
                            )
                    except Exception as e:
                        logger.error("Score error for %s: %s",
                                     msg.value.get("transaction_id", "?"), e)
    finally:
        consumer.close()
        logger.info("Consumer loop stopped — total scored: %d", processed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scorer, producer, _running
    _running = True
    scorer   = FraudScorer()
    producer = make_producer()

    # Start Kafka consumer in background thread
    t = threading.Thread(target=consumer_loop, daemon=True, name="kafka-consumer")
    t.start()
    logger.info("ML scoring service ready — consumer thread started")

    yield

    _running = False
    producer.flush()
    producer.close()
    logger.info("ML scoring service stopped")


app = FastAPI(title="ML Fraud Scoring API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── Pydantic models for REST endpoint ────────────────────────────────────────

class ScoreRequest(BaseModel):
    transaction_id:       str
    user_id:              str
    amount:               float = 0.0
    currency:             str   = "USD"
    merchant_name:        str   = ""
    merchant_category:    str   = ""
    merchant_country:     str   = ""
    user_country:         str   = ""
    payment_method:       str   = ""
    channel:              str   = ""
    txn_count_user:       int   = 0
    hours_since_last_txn: float = -1
    amount_deviation:     float = 0
    geo_distance_km:      float = 0
    is_new_device:        int   = 0
    is_high_risk_country: int   = 0
    is_cross_border:      int   = 0
    velocity_10min:       int   = 0
    created_at_epoch:     float | None = None


class ScoreResponse(BaseModel):
    transaction_id:  str
    user_id:         str
    ml_score:        float
    rules_score:     float
    final_score:     float
    decision:        str
    triggered_rules: list[str]
    is_fraud:        bool
    processing_ms:   float


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": scorer is not None}


@app.post("/api/v1/score", response_model=ScoreResponse)
async def score_transaction(req: ScoreRequest):
    """Direct REST endpoint — for testing only. Pipeline uses Kafka."""
    if scorer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    result = score_one(req.model_dump())
    return ScoreResponse(**{k: result[k] for k in ScoreResponse.model_fields})