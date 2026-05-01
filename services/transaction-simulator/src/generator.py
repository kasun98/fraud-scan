import random
import uuid
from datetime import datetime, timezone
from typing import Any

from fraud_patterns import apply_fraud_pattern

MERCHANTS = [
    {"id": "merch-001", "name": "Amazon",           "category": "ecommerce",     "country": "US"},
    {"id": "merch-002", "name": "Netflix",           "category": "streaming",     "country": "US"},
    {"id": "merch-003", "name": "Whole Foods",       "category": "grocery",       "country": "US"},
    {"id": "merch-004", "name": "Shell Petrol",      "category": "fuel",          "country": "GB"},
    {"id": "merch-005", "name": "Uber",              "category": "transport",     "country": "US"},
    {"id": "merch-006", "name": "Apple Store",       "category": "electronics",   "country": "US"},
    {"id": "merch-007", "name": "Tesco",             "category": "grocery",       "country": "GB"},
    {"id": "merch-008", "name": "Booking.com",       "category": "travel",        "country": "NL"},
    {"id": "merch-009", "name": "Steam",             "category": "digital_goods", "country": "US"},
    {"id": "merch-010", "name": "Local Restaurant",  "category": "dining",        "country": "US"},
]

USERS = [f"user-{str(i).zfill(4)}" for i in range(1, 201)]   # 200 synthetic users

COUNTRIES = ["US", "GB", "DE", "FR", "IN", "SG", "AU", "CA", "JP", "BR"]
CITIES    = ["New York", "London", "Berlin", "Paris", "Mumbai",
             "Singapore", "Sydney", "Toronto", "Tokyo", "São Paulo"]

# Normal spend distribution per merchant category
AMOUNT_RANGES = {
    "ecommerce":     (10,   500),
    "streaming":     (8,    20),
    "grocery":       (20,   200),
    "fuel":          (30,   120),
    "transport":     (5,    80),
    "electronics":   (100,  2000),
    "digital_goods": (1,    60),
    "travel":        (150,  3000),
    "dining":        (15,   150),
    "money_transfer":(100,  5000),
}


def generate_transaction(fraud_rate: float = 0.02) -> dict[str, Any]:
    merchant   = random.choice(MERCHANTS)
    user_id    = random.choice(USERS)
    country    = random.choice(COUNTRIES)
    city_idx   = COUNTRIES.index(country) if country in COUNTRIES else 0
    city       = CITIES[city_idx]
    category   = merchant["category"]
    lo, hi     = AMOUNT_RANGES.get(category, (10, 500))

    txn: dict[str, Any] = {
        "transaction_id":    str(uuid.uuid4()),
        "user_id":           user_id,
        "session_id":        str(uuid.uuid4()),
        "amount":            round(random.uniform(lo, hi), 2),
        "currency":          "USD",
        "merchant_id":       merchant["id"],
        "merchant_name":     merchant["name"],
        "merchant_category": category,
        "merchant_country":  merchant["country"],
        "user_country":      country,
        "user_city":         city,
        "latitude":          round(random.uniform(-60, 70), 4),
        "longitude":         round(random.uniform(-130, 130), 4),
        "payment_method":    random.choice(["credit_card", "debit_card", "digital_wallet"]),
        "channel":           random.choice(["web", "mobile", "pos"]),
        "device_id":         f"device-{uuid.uuid4().hex[:12]}",
        "ip_address":        f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "event_type":        "transaction.initiated",
        "is_fraud":          False,
        "fraud_pattern":     None,
        "metadata":          {
            "simulator_version": "1.0.0",
            "generated":         True,
        },
    }

    # Inject fraud pattern at configured rate
    if random.random() < fraud_rate:
        txn = apply_fraud_pattern(txn)

    return txn