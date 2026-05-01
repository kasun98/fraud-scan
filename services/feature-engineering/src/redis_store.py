import json
import logging
from datetime import datetime, timezone

import redis

logger = logging.getLogger("redis-store")


class FeatureStore:
    """
    Redis-backed feature store.
    Key pattern: features:{user_id}
    TTL: 24 hours — features expire if user is inactive
    """
    TTL_SECONDS = 86_400  # 24 hours

    def __init__(self, host: str, port: int = 6379):
        self.client = redis.Redis(
            host=host, port=port, decode_responses=True,
            socket_connect_timeout=5, socket_timeout=5,
        )
        self.client.ping()
        logger.info("Redis connected at %s:%d", host, port)

    def get_user_features(self, user_id: str) -> dict:
        key  = f"features:{user_id}"
        data = self.client.get(key)
        return json.loads(data) if data else {}

    def update_user_features(self, user_id: str, txn: dict) -> dict:
        key      = f"features:{user_id}"
        existing = self.get_user_features(user_id)
        now      = datetime.now(timezone.utc)

        # Rolling window counters
        txn_count    = existing.get("txn_count", 0) + 1
        avg_amount   = existing.get("avg_amount", txn["amount"])
        avg_amount   = round(avg_amount * 0.95 + txn["amount"] * 0.05, 4)

        # Time since last transaction
        last_txn_iso = existing.get("last_txn_time")
        if last_txn_iso:
            last_txn_time    = datetime.fromisoformat(last_txn_iso)
            hours_since_last = (now - last_txn_time).total_seconds() / 3600
        else:
            hours_since_last = -1

        # Amount deviation from personal baseline
        amount_deviation = abs(txn["amount"] - avg_amount) / max(avg_amount, 1)

        # Device check
        usual_device = existing.get("usual_device", txn.get("device_id"))
        is_new_device = 1 if txn.get("device_id") != usual_device else 0

        features = {
            "user_id":             user_id,
            "txn_count_user":      txn_count,
            "avg_amount":          avg_amount,
            "hours_since_last_txn": round(hours_since_last, 4),
            "amount_deviation":    round(amount_deviation, 4),
            "is_new_device":       is_new_device,
            "usual_device":        usual_device,
            "last_txn_time":       now.isoformat(),
            "last_amount":         txn["amount"],
            "last_merchant":       txn.get("merchant_category", ""),
            "updated_at":          now.isoformat(),
        }

        self.client.setex(key, self.TTL_SECONDS, json.dumps(features))
        return features

    def get_velocity_count(self, user_id: str, window_minutes: int = 10) -> int:
        """Count transactions in the last N minutes using a Redis sorted set."""
        key = f"velocity:{user_id}"
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - (window_minutes * 60)

        # Remove old entries outside the window
        self.client.zremrangebyscore(key, "-inf", window_start)

        # Add current transaction
        self.client.zadd(key, {str(now): now})
        self.client.expire(key, window_minutes * 60 * 2)

        # Count in window
        return self.client.zcount(key, window_start, now)