import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import json
import xgboost as xgb


logger = logging.getLogger("scorer")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/model/model.ubj")

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

FEATURE_ORDER = [
    "amount", "txn_count_user", "hours_since_last_txn",
    "amount_deviation", "geo_distance_km",
    "is_new_device", "is_high_risk_country", "is_cross_border",
    "merchant_category", "payment_method", "channel",
]

FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.5"))


class FraudScorer:
    def __init__(self):
        model_path = Path(MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}. "
                "Did you run ml/training/train.py and build the Docker image?"
            )
        logger.info("Loading model from %s", model_path)
        self.model = xgb.XGBClassifier()
        self.model.load_model(str(model_path))
        logger.info("Model loaded successfully")

    def _prepare_features(self, features: dict) -> pd.DataFrame:
        row = {}
        for feat in FEATURE_ORDER:
            val = features.get(feat, 0)
            if feat in CATEGORY_MAPS:
                val = CATEGORY_MAPS[feat].get(str(val), 0)
            row[feat] = val

        df = pd.DataFrame([row])
        # Fix hours_since_last_txn sentinel value
        df["hours_since_last_txn"] = df["hours_since_last_txn"].replace(-1, 24.0)
        return df

    def score(self, features: dict) -> dict:
        df              = self._prepare_features(features)
        fraud_prob      = float(self.model.predict_proba(df)[0][1])
        is_fraud        = fraud_prob >= FRAUD_THRESHOLD

        return {
            "fraud_probability": round(fraud_prob, 6),
            "is_fraud":          is_fraud,
            "threshold":         FRAUD_THRESHOLD,
            "model_version":     "latest",
        }