from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DecisionRecord(BaseModel):
    transaction_id:   str
    user_id:          str
    amount:           float
    currency:         str = "USD"
    merchant_name:    str | None = None
    merchant_category: str | None = None
    merchant_country: str | None = None
    user_country:     str | None = None
    payment_method:   str | None = None
    channel:          str | None = None
    ml_score:         float
    rules_score:      float
    final_score:      float
    decision:         str
    triggered_rules:  list[str] = []
    is_fraud:         bool
    fraud_pattern:    str | None = None
    created_at:       datetime | None = None


class ReviewRequest(BaseModel):
    analyst_id:       str
    analyst_decision: str   # CONFIRMED_FRAUD / FALSE_POSITIVE / NEEDS_INFO
    notes:            str | None = None


class ReviewResponse(BaseModel):
    transaction_id:   str
    analyst_id:       str
    analyst_decision: str
    notes:            str | None
    reviewed_at:      datetime


class StatsResponse(BaseModel):
    total:       int   = 0
    approved:    int   = 0
    review:      int   = 0
    blocked:     int   = 0
    fraud_total: int   = 0
    avg_score:   float = 0.0
    avg_amount:  float = 0.0
    last_hour:   int   = 0
    tps:         float = 0.0
    payment_method_dist: list[dict] = []
    channel_dist: list[dict] = []
    merchant_category_dist: list[dict] = []
    amount_distribution: list[dict] = []
    review_countries: list[dict] = []
    triggered_rules_dist: list[dict] = []