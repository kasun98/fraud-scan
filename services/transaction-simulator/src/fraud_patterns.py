import random
import uuid
from datetime import datetime, timezone
from typing import Any

HIGH_RISK_COUNTRIES = ["NG", "RU", "BY", "KP", "IR", "VE", "MM"]
HIGH_RISK_MERCHANTS = [
    {"id": "merch-hr-001", "name": "Global Crypto Exchange", "category": "crypto"},
    {"id": "merch-hr-002", "name": "Fast Cash Transfer", "category": "money_transfer"},
    {"id": "merch-hr-003", "name": "Online Casino Pro",    "category": "gambling"},
    {"id": "merch-hr-004", "name": "Gift Card Depot",      "category": "gift_cards"},
]


def apply_fraud_pattern(txn: dict[str, Any]) -> dict[str, Any]:
    """
    Randomly pick one of 6 real-world fraud patterns and mutate the transaction.
    Each pattern mirrors a known fraud typology used in production systems.
    """
    pattern = random.choice([
        _card_testing,
        _account_takeover,
        _impossible_travel,
        _high_value_spike,
        _money_mule,
        _friendly_fraud,
    ])
    txn = pattern(txn)
    txn["is_fraud"] = True
    return txn


# ── Pattern 1: Card Testing ──────────────────────────────────────────────────
# Fraudster makes many tiny transactions to verify a stolen card works
def _card_testing(txn: dict[str, Any]) -> dict[str, Any]:
    txn["amount"]           = round(random.uniform(0.01, 2.00), 2)
    txn["merchant_category"] = "digital_goods"
    txn["merchant_name"]    = "AppStore Micro Purchase"
    txn["channel"]          = "api"
    txn["fraud_pattern"]    = "card_testing"
    txn["metadata"]["velocity_burst"] = True
    return txn


# ── Pattern 2: Account Takeover ──────────────────────────────────────────────
# Stolen credentials, login from new device/IP, immediate large withdrawal
def _account_takeover(txn: dict[str, Any]) -> dict[str, Any]:
    txn["amount"]           = round(random.uniform(5000, 25000), 2)
    txn["device_id"]        = f"unknown-device-{uuid.uuid4().hex[:8]}"
    txn["ip_address"]       = f"185.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    txn["merchant_category"] = "bank_transfer"
    txn["payment_method"]   = "bank_transfer"
    txn["fraud_pattern"]    = "account_takeover"
    txn["metadata"]["new_device"] = True
    txn["metadata"]["new_ip"]     = True
    return txn


# ── Pattern 3: Impossible Travel ─────────────────────────────────────────────
# Transaction in a country geographically impossible given prior activity
def _impossible_travel(txn: dict[str, Any]) -> dict[str, Any]:
    txn["merchant_country"] = random.choice(HIGH_RISK_COUNTRIES)
    txn["user_country"]     = "US"          # user is normally US-based
    txn["latitude"]         = round(random.uniform(50, 60), 4)
    txn["longitude"]        = round(random.uniform(30, 60), 4)
    txn["amount"]           = round(random.uniform(500, 8000), 2)
    txn["fraud_pattern"]    = "impossible_travel"
    txn["metadata"]["geo_mismatch"] = True
    return txn


# ── Pattern 4: High Value Spike ──────────────────────────────────────────────
# Single transaction far above the user's normal spend baseline
def _high_value_spike(txn: dict[str, Any]) -> dict[str, Any]:
    txn["amount"]           = round(random.uniform(15000, 100000), 2)
    txn["merchant"]         = random.choice(HIGH_RISK_MERCHANTS)
    txn["merchant_name"]    = txn["merchant"]["name"]
    txn["merchant_category"] = txn["merchant"]["category"]
    txn["merchant_id"]      = txn["merchant"]["id"]
    txn["fraud_pattern"]    = "high_value_spike"
    txn["metadata"]["amount_zscore"] = round(random.uniform(4.5, 9.0), 2)
    return txn


# ── Pattern 5: Money Mule ────────────────────────────────────────────────────
# Many incoming transfers immediately forwarded out — layering stage of laundering
def _money_mule(txn: dict[str, Any]) -> dict[str, Any]:
    txn["amount"]            = round(random.uniform(1000, 9999), 2)
    txn["payment_method"]    = "bank_transfer"
    txn["merchant_category"] = "money_transfer"
    txn["merchant_country"]  = random.choice(HIGH_RISK_COUNTRIES)
    txn["fraud_pattern"]     = "money_mule"
    txn["metadata"]["structuring"] = True   # amounts kept just under reporting limits
    return txn


# ── Pattern 6: Friendly Fraud ────────────────────────────────────────────────
# Legitimate user disputes a real transaction (chargeback abuse)
def _friendly_fraud(txn: dict[str, Any]) -> dict[str, Any]:
    txn["amount"]            = round(random.uniform(200, 2000), 2)
    txn["merchant_category"] = "ecommerce"
    txn["event_type"]        = "transaction.completed"
    txn["fraud_pattern"]     = "friendly_fraud"
    txn["metadata"]["chargeback_risk"] = True
    return txn