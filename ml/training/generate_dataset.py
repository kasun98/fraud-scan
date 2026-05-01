import csv
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTPUT_PATH = Path("ml/data/transactions_100k.csv")
NUM_RECORDS = 100_000
FRAUD_RATE  = 0.02
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

MERCHANTS = [
    {"id": "merch-001", "name": "Amazon",          "category": "ecommerce",     "country": "US"},
    {"id": "merch-002", "name": "Netflix",          "category": "streaming",     "country": "US"},
    {"id": "merch-003", "name": "Whole Foods",      "category": "grocery",       "country": "US"},
    {"id": "merch-004", "name": "Shell Petrol",     "category": "fuel",          "country": "GB"},
    {"id": "merch-005", "name": "Uber",             "category": "transport",     "country": "US"},
    {"id": "merch-006", "name": "Apple Store",      "category": "electronics",   "country": "US"},
    {"id": "merch-007", "name": "Tesco",            "category": "grocery",       "country": "GB"},
    {"id": "merch-008", "name": "Booking.com",      "category": "travel",        "country": "NL"},
    {"id": "merch-009", "name": "Steam",            "category": "digital_goods", "country": "US"},
    {"id": "merch-010", "name": "Local Restaurant", "category": "dining",        "country": "US"},
]

HIGH_RISK_COUNTRIES = ["NG", "RU", "BY", "KP", "IR"]
COUNTRIES = ["US", "GB", "DE", "FR", "IN", "SG", "AU", "CA", "JP", "BR"]
CITIES    = ["New York", "London", "Berlin", "Paris", "Mumbai",
             "Singapore", "Sydney", "Toronto", "Tokyo", "Sao Paulo"]

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

USERS = [f"user-{str(i).zfill(4)}" for i in range(1, 501)]  # 500 users

# Track per-user state for realistic feature generation
user_state: dict = {}


def get_user_state(user_id: str) -> dict:
    if user_id not in user_state:
        country_idx = random.randint(0, len(COUNTRIES) - 1)
        user_state[user_id] = {
            "home_country":   COUNTRIES[country_idx],
            "home_city":      CITIES[country_idx],
            "home_lat":       round(random.uniform(-50, 60), 4),
            "home_lon":       round(random.uniform(-120, 120), 4),
            "avg_amount":     round(random.uniform(50, 500), 2),
            "txn_count":      0,
            "last_txn_time":  None,
            "usual_device":   f"device-{uuid.uuid4().hex[:12]}",
        }
    return user_state[user_id]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)


def generate_normal_transaction(user_id: str, timestamp: datetime) -> dict:
    state    = get_user_state(user_id)
    merchant = random.choice(MERCHANTS)
    category = merchant["category"]
    lo, hi   = AMOUNT_RANGES.get(category, (10, 500))
    amount   = round(random.uniform(lo, hi), 2)

    lat = round(state["home_lat"] + random.uniform(-0.5, 0.5), 4)
    lon = round(state["home_lon"] + random.uniform(-0.5, 0.5), 4)

    hours_since_last = None
    if state["last_txn_time"]:
        delta = timestamp - state["last_txn_time"]
        hours_since_last = round(delta.total_seconds() / 3600, 4)

    geo_distance = haversine_km(state["home_lat"], state["home_lon"], lat, lon)
    amount_deviation = round(abs(amount - state["avg_amount"]) / max(state["avg_amount"], 1), 4)

    txn = {
        "transaction_id":        str(uuid.uuid4()),
        "user_id":               user_id,
        "session_id":            str(uuid.uuid4()),
        "amount":                amount,
        "currency":              "USD",
        "merchant_id":           merchant["id"],
        "merchant_name":         merchant["name"],
        "merchant_category":     category,
        "merchant_country":      merchant["country"],
        "user_country":          state["home_country"],
        "user_city":             state["home_city"],
        "latitude":              lat,
        "longitude":             lon,
        "payment_method":        random.choice(["credit_card", "debit_card", "digital_wallet"]),
        "channel":               random.choice(["web", "mobile", "pos"]),
        "device_id":             state["usual_device"],
        "ip_address":            f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "timestamp":             timestamp.isoformat(),
        "event_type":            "transaction.initiated",
        "is_fraud":              False,
        "fraud_pattern":         "",
        # --- engineered features (for training) ---
        "txn_count_user":        state["txn_count"],
        "hours_since_last_txn":  hours_since_last if hours_since_last is not None else -1,
        "amount_deviation":      amount_deviation,
        "geo_distance_km":       geo_distance,
        "is_new_device":         0,
        "is_high_risk_country":  1 if merchant["country"] in HIGH_RISK_COUNTRIES else 0,
        "is_cross_border":       1 if merchant["country"] != state["home_country"] else 0,
    }

    # Update state
    state["txn_count"]    += 1
    state["last_txn_time"] = timestamp
    state["avg_amount"]    = round(
        state["avg_amount"] * 0.95 + amount * 0.05, 2   # exponential moving average
    )
    return txn


def apply_fraud_pattern(txn: dict, pattern: str) -> dict:
    txn = txn.copy()
    txn["is_fraud"]      = True
    txn["fraud_pattern"] = pattern

    if pattern == "card_testing":
        txn["amount"]              = round(random.uniform(0.01, 2.00), 2)
        txn["merchant_category"]   = "digital_goods"
        txn["amount_deviation"]    = round(abs(txn["amount"] - 200) / 200, 4)

    elif pattern == "account_takeover":
        txn["amount"]           = round(random.uniform(5000, 25000), 2)
        txn["device_id"]        = f"unknown-{uuid.uuid4().hex[:8]}"
        txn["is_new_device"]    = 1
        txn["amount_deviation"] = round(random.uniform(8, 20), 4)
        txn["payment_method"]   = "bank_transfer"

    elif pattern == "impossible_travel":
        txn["merchant_country"]      = random.choice(HIGH_RISK_COUNTRIES)
        txn["is_high_risk_country"]  = 1
        txn["is_cross_border"]       = 1
        txn["geo_distance_km"]       = round(random.uniform(5000, 15000), 2)
        txn["amount"]                = round(random.uniform(500, 8000), 2)
        txn["hours_since_last_txn"]  = round(random.uniform(0.01, 2.0), 4)

    elif pattern == "high_value_spike":
        txn["amount"]           = round(random.uniform(15000, 100000), 2)
        txn["amount_deviation"] = round(random.uniform(10, 50), 4)
        txn["merchant_category"]= "money_transfer"
        txn["is_high_risk_country"] = 1

    elif pattern == "money_mule":
        txn["amount"]              = round(random.uniform(1000, 9999), 2)
        txn["payment_method"]      = "bank_transfer"
        txn["merchant_category"]   = "money_transfer"
        txn["merchant_country"]    = random.choice(HIGH_RISK_COUNTRIES)
        txn["is_high_risk_country"]= 1
        txn["is_cross_border"]     = 1

    elif pattern == "friendly_fraud":
        txn["amount"]           = round(random.uniform(200, 2000), 2)
        txn["merchant_category"]= "ecommerce"
        txn["amount_deviation"] = round(random.uniform(2, 6), 4)

    return txn


FRAUD_PATTERNS = [
    "card_testing", "account_takeover", "impossible_travel",
    "high_value_spike", "money_mule", "friendly_fraud",
]

COLUMNS = [
    "transaction_id", "user_id", "session_id", "amount", "currency",
    "merchant_id", "merchant_name", "merchant_category", "merchant_country",
    "user_country", "user_city", "latitude", "longitude",
    "payment_method", "channel", "device_id", "ip_address",
    "timestamp", "event_type", "is_fraud", "fraud_pattern",
    "txn_count_user", "hours_since_last_txn", "amount_deviation",
    "geo_distance_km", "is_new_device", "is_high_risk_country", "is_cross_border",
]


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Generate timestamps spread over 90 days
    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=90)
    timestamps = sorted([
        start_time + timedelta(seconds=random.randint(0, int((end_time - start_time).total_seconds())))
        for _ in range(NUM_RECORDS)
    ])

    num_fraud  = int(NUM_RECORDS * FRAUD_RATE)
    fraud_idxs = set(random.sample(range(NUM_RECORDS), num_fraud))

    print(f"Generating {NUM_RECORDS:,} transactions ({num_fraud:,} fraud)...")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()

        for i, ts in enumerate(timestamps):
            user_id = random.choice(USERS)
            txn     = generate_normal_transaction(user_id, ts)

            if i in fraud_idxs:
                pattern = random.choice(FRAUD_PATTERNS)
                txn     = apply_fraud_pattern(txn, pattern)

            writer.writerow({col: txn.get(col, "") for col in COLUMNS})

            if (i + 1) % 10_000 == 0:
                print(f"  {i+1:,} / {NUM_RECORDS:,} records written...")

    print(f"Done. Saved to {OUTPUT_PATH}")
    print(f"Fraud rate: {num_fraud/NUM_RECORDS*100:.1f}%")


if __name__ == "__main__":
    main()