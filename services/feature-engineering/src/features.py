import math
import logging

logger = logging.getLogger("features")

HIGH_RISK_COUNTRIES = {"NG", "RU", "BY", "KP", "IR", "VE", "MM"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a    = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def compute_transaction_features(txn: dict, user_features: dict, velocity: int) -> dict:
    """
    Merge raw transaction fields with stored user features
    into the exact feature vector the ML model expects.
    """
    lat  = txn.get("latitude", 0) or 0
    lon  = txn.get("longitude", 0) or 0
    home_lat = user_features.get("home_lat", lat)
    home_lon = user_features.get("home_lon", lon)

    geo_distance = haversine_km(home_lat, home_lon, lat, lon) if (home_lat and home_lon) else 0

    return {
        # Raw fields
        "transaction_id":    txn["transaction_id"],
        "user_id":           txn["user_id"],
        "amount":            txn["amount"],
        "merchant_category": txn.get("merchant_category", ""),
        "payment_method":    txn.get("payment_method", ""),
        "channel":           txn.get("channel", ""),
        "merchant_country":  txn.get("merchant_country", ""),
        "user_country":      txn.get("user_country", ""),
        "timestamp":         txn.get("timestamp", ""),

        # Engineered features
        "txn_count_user":        user_features.get("txn_count_user", 0),
        "hours_since_last_txn":  user_features.get("hours_since_last_txn", -1),
        "amount_deviation":      user_features.get("amount_deviation", 0),
        "geo_distance_km":       geo_distance,
        "is_new_device":         user_features.get("is_new_device", 0),
        "is_high_risk_country":  1 if txn.get("merchant_country") in HIGH_RISK_COUNTRIES else 0,
        "is_cross_border":       1 if txn.get("merchant_country") != txn.get("user_country") else 0,
        "velocity_10min":        velocity,
    }