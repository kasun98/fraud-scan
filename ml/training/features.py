# Features used by the model — order matters for XGBoost
NUMERIC_FEATURES = [
    "amount",
    "txn_count_user",
    "hours_since_last_txn",
    "amount_deviation",
    "geo_distance_km",
]

BINARY_FEATURES = [
    "is_new_device",
    "is_high_risk_country",
    "is_cross_border",
]

CATEGORICAL_FEATURES = [
    "merchant_category",
    "payment_method",
    "channel",
]

ALL_FEATURES = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES

TARGET = "is_fraud"

CATEGORY_MAPS = {
    "merchant_category": {
        "ecommerce": 0, "streaming": 1, "grocery": 2, "fuel": 3,
        "transport": 4, "electronics": 5, "digital_goods": 6,
        "travel": 7, "dining": 8, "money_transfer": 9, "crypto": 10,
        "gift_cards": 11, "gambling": 12, "bank_transfer": 13,
    },
    "payment_method": {
        "credit_card": 0, "debit_card": 1, "bank_transfer": 2,
        "digital_wallet": 3, "crypto": 4,
    },
    "channel": {
        "web": 0, "mobile": 1, "atm": 2, "pos": 3, "api": 4,
    },
}